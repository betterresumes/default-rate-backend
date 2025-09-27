from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, text
from typing import Dict, List, Optional
from datetime import datetime
import uuid
import pandas as pd
import io
import math
import logging
import json

from ...core.database import get_db, User, Company, AnnualPrediction, QuarterlyPrediction, Organization, BulkUploadJob
from ...schemas.schemas import (
    AnnualPredictionRequest, QuarterlyPredictionRequest
)
from ...services.ml_service import ml_model
from ...services.quarterly_ml_service import quarterly_ml_model
from .auth_multi_tenant import get_current_active_user as current_verified_user
from app.workers.celery_app import celery_app

router = APIRouter()

logger = logging.getLogger(__name__)


def get_user_access_level(user: User):
    """Get the access level for data created by this user"""
    if user.role == "super_admin":
        return "system"  # System-wide data
    elif user.role in ["org_admin", "org_member"] and user.organization_id:
        return "organization"  # Organization data
    else:
        return "personal"  # Personal data only

def get_data_access_filter(user: User, prediction_model, include_system: bool = False):
    """Get access filter for predictions - excludes system data by default"""
    conditions = []
    
    if user.role == "super_admin" and include_system:
        return None
    
    conditions.append(
        and_(
            prediction_model.access_level == "personal",
            prediction_model.created_by == str(user.id)
        )
    )
    
    if user.organization_id:
        conditions.append(
            and_(
                prediction_model.access_level == "organization",
                prediction_model.organization_id == user.organization_id
            )
        )
    
    if include_system:
        conditions.append(prediction_model.access_level == "system")
    
    return or_(*conditions)

def get_organization_context(current_user: User):
    """Get organization context based on user role for access control"""
    if current_user.role == "super_admin":
        return None  # System-wide access (organization_id = None)
    elif current_user.role in ["tenant_admin", "org_admin", "org_member"]:
        return current_user.organization_id  # Restricted to their organization
    else:
        return current_user.organization_id  # Could be None for basic users

def create_or_get_company(db: Session, company_symbol: str, company_name: str, 
                         market_cap: float, sector: str, user: User):
    """Create company with simplified access control"""
    
    access_level = get_user_access_level(user)
    organization_id = user.organization_id if access_level == "organization" else None
    
    query = db.query(Company).filter(
        Company.symbol == company_symbol.upper(),
        Company.access_level == access_level
    )
    
    if access_level == "organization" and organization_id:
        query = query.filter(Company.organization_id == organization_id)
    elif access_level == "personal":
        query = query.filter(Company.created_by == str(user.id))
    
    existing_company = query.first()
    
    if existing_company:
        return existing_company
    
    company = Company(
        symbol=company_symbol.upper(),
        name=company_name,
        market_cap=market_cap,
        sector=sector,
        access_level=access_level,
        organization_id=organization_id,
        created_by=str(user.id)
    )
    
    db.add(company)
    db.commit()
    db.refresh(company)
    return company

def check_user_permissions(user: User, required_role: str = "user"):
    """Check if user has required permissions based on 5-role hierarchy"""
    role_hierarchy = {
        "user": 0,
        "org_member": 1, 
        "org_admin": 2,
        "tenant_admin": 3,
        "super_admin": 4
    }
    
    user_level = role_hierarchy.get(user.role, -1)
    required_level = role_hierarchy.get(required_role, 0)
    
    return user_level >= required_level

def safe_float(value):
    """Convert value to float, handling None and NaN values"""
    if value is None:
        return None
    try:
        float_val = float(value)
        if math.isnan(float_val) or math.isinf(float_val):
            return None
        return float_val
    except (ValueError, TypeError):
        return None

def is_prediction_owner(prediction, current_user):
    """Check if current user is the owner of the prediction"""
    if not prediction or not current_user:
        return False
    
    # Convert both to string for comparison to handle UUID vs string issues
    prediction_creator = str(prediction.created_by) if prediction.created_by else None
    current_user_id = str(current_user.id) if current_user.id else None
    
    return prediction_creator and current_user_id and prediction_creator == current_user_id


@router.post("/annual", response_model=Dict)
async def create_annual_prediction(
    request: AnnualPredictionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
    """Create annual prediction with simplified 3-level access control"""
    try:
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to create predictions"
            )

        access_level = get_user_access_level(current_user)
        organization_id = current_user.organization_id if access_level == "organization" else None
        
        company = create_or_get_company(
            db=db,
            company_symbol=request.company_symbol,
            company_name=request.company_name,
            market_cap=request.market_cap,
            sector=request.sector,
            user=current_user
        )
        
        existing_query = db.query(AnnualPrediction).filter(
            AnnualPrediction.company_id == company.id,
            AnnualPrediction.reporting_year == request.reporting_year,
            AnnualPrediction.access_level == access_level
        )
        
        if access_level == "organization":
            existing_query = existing_query.filter(AnnualPrediction.organization_id == organization_id)
        elif access_level == "personal":
            existing_query = existing_query.filter(AnnualPrediction.created_by == str(current_user.id))
        
        if request.reporting_quarter:
            existing_query = existing_query.filter(AnnualPrediction.reporting_quarter == request.reporting_quarter)
        else:
            existing_query = existing_query.filter(AnnualPrediction.reporting_quarter.is_(None))
        
        existing_prediction = existing_query.first()
        
        if existing_prediction:
            quarter_text = f" {request.reporting_quarter}" if request.reporting_quarter else ""
            raise HTTPException(
                status_code=400,
                detail=f"Annual prediction for {request.company_symbol} in {request.reporting_year}{quarter_text} already exists in your {access_level} scope"
            )
        
        financial_data = {
            'long_term_debt_to_total_capital': request.long_term_debt_to_total_capital,
            'total_debt_to_ebitda': request.total_debt_to_ebitda,
            'net_income_margin': request.net_income_margin,
            'ebit_to_interest_expense': request.ebit_to_interest_expense,
            'return_on_assets': request.return_on_assets
        }
        
        ml_result = await ml_model.predict_annual(financial_data)
        
        prediction = AnnualPrediction(
            id=uuid.uuid4(),
            company_id=company.id,
            organization_id=organization_id,
            access_level=access_level,
            reporting_year=request.reporting_year,
            reporting_quarter=request.reporting_quarter,
            
            long_term_debt_to_total_capital=request.long_term_debt_to_total_capital,
            total_debt_to_ebitda=request.total_debt_to_ebitda,
            net_income_margin=request.net_income_margin,
            ebit_to_interest_expense=request.ebit_to_interest_expense,
            return_on_assets=request.return_on_assets,
            
            probability=ml_result['probability'],
            risk_level=ml_result['risk_level'],
            confidence=ml_result['confidence'],
            predicted_at=datetime.utcnow(),
            
            created_by=str(current_user.id)
        )
        
        db.add(prediction)
        db.commit()
        db.refresh(prediction)
        
        organization_name = None
        if organization_id:
            org = db.query(Organization).filter(Organization.id == organization_id).first()
            organization_name = org.name if org else None
        
        return {
            "success": True,
            "message": f"Annual prediction created for {request.company_symbol}",
            "prediction": {
                "id": str(prediction.id),
                "company_id": str(company.id),
                "company_symbol": request.company_symbol,
                "company_name": request.company_name,
                "sector": request.sector,
                "market_cap": float(request.market_cap),
                "reporting_year": request.reporting_year,
                "reporting_quarter": request.reporting_quarter,
                
                "long_term_debt_to_total_capital": float(request.long_term_debt_to_total_capital),
                "total_debt_to_ebitda": float(request.total_debt_to_ebitda),
                "net_income_margin": float(request.net_income_margin),
                "ebit_to_interest_expense": float(request.ebit_to_interest_expense),
                "return_on_assets": float(request.return_on_assets),
                
                "probability": float(ml_result['probability']),
                "risk_level": ml_result['risk_level'],
                "confidence": float(ml_result['confidence']),
                
                "access_level": access_level,
                "organization_id": str(organization_id) if organization_id else None,
                "organization_name": organization_name,
                "created_by": str(current_user.id),
                "created_by_email": current_user.email,
                "created_at": prediction.created_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating annual prediction: {str(e)}")

@router.post("/quarterly", response_model=Dict)
async def create_quarterly_prediction(
    request: QuarterlyPredictionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
    """Create quarterly prediction with simplified 3-level access control"""
    try:
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to create predictions"
            )

        access_level = get_user_access_level(current_user)
        organization_id = current_user.organization_id if access_level == "organization" else None
        
        company = create_or_get_company(
            db=db,
            company_symbol=request.company_symbol,
            company_name=request.company_name,
            market_cap=request.market_cap,
            sector=request.sector,
            user=current_user
        )
        
        existing_query = db.query(QuarterlyPrediction).filter(
            QuarterlyPrediction.company_id == company.id,
            QuarterlyPrediction.reporting_year == request.reporting_year,
            QuarterlyPrediction.reporting_quarter == request.reporting_quarter,
            QuarterlyPrediction.access_level == access_level
        )
        
        if access_level == "organization":
            existing_query = existing_query.filter(QuarterlyPrediction.organization_id == organization_id)
        elif access_level == "personal":
            existing_query = existing_query.filter(QuarterlyPrediction.created_by == str(current_user.id))
        
        existing_prediction = existing_query.first()
        
        if existing_prediction:
            raise HTTPException(
                status_code=400,
                detail=f"Quarterly prediction for {request.company_symbol} in {request.reporting_year} {request.reporting_quarter} already exists in your {access_level} scope"
            )
        
        financial_data = {
            'total_debt_to_ebitda': request.total_debt_to_ebitda,
            'sga_margin': request.sga_margin,
            'long_term_debt_to_total_capital': request.long_term_debt_to_total_capital,
            'return_on_capital': request.return_on_capital
        }
        
        ml_result = await quarterly_ml_model.predict_quarterly(financial_data)
        
        prediction = QuarterlyPrediction(
            id=uuid.uuid4(),
            company_id=company.id,
            organization_id=organization_id,
            access_level=access_level,
            reporting_year=request.reporting_year,
            reporting_quarter=request.reporting_quarter,
            
            total_debt_to_ebitda=request.total_debt_to_ebitda,
            sga_margin=request.sga_margin,
            long_term_debt_to_total_capital=request.long_term_debt_to_total_capital,
            return_on_capital=request.return_on_capital,
            
            logistic_probability=ml_result.get('logistic_probability'),
            gbm_probability=ml_result.get('gbm_probability'),
            ensemble_probability=ml_result.get('ensemble_probability'),
            risk_level=ml_result['risk_level'],
            confidence=ml_result['confidence'],
            predicted_at=datetime.utcnow(),
            
            created_by=str(current_user.id)
        )
        
        db.add(prediction)
        db.commit()
        db.refresh(prediction)
        
        organization_name = None
        if organization_id:
            org = db.query(Organization).filter(Organization.id == organization_id).first()
            organization_name = org.name if org else None
        
        return {
            "success": True,
            "message": f"Quarterly prediction created for {request.company_symbol}",
            "prediction": {
                "id": str(prediction.id),
                "company_id": str(company.id),
                "company_symbol": request.company_symbol,
                "company_name": request.company_name,
                "sector": request.sector,
                "market_cap": float(request.market_cap),
                "reporting_year": request.reporting_year,
                "reporting_quarter": request.reporting_quarter,
                
                "total_debt_to_ebitda": float(request.total_debt_to_ebitda),
                "sga_margin": float(request.sga_margin),
                "long_term_debt_to_total_capital": float(request.long_term_debt_to_total_capital),
                "return_on_capital": float(request.return_on_capital),
                
                "logistic_probability": float(ml_result.get('logistic_probability', 0)),
                "gbm_probability": float(ml_result.get('gbm_probability', 0)),
                "ensemble_probability": float(ml_result.get('ensemble_probability', 0)),
                "risk_level": ml_result['risk_level'],
                "confidence": float(ml_result['confidence']),
                
                "access_level": access_level,
                "organization_id": str(organization_id) if organization_id else None,
                "organization_name": organization_name,
                "created_by": str(current_user.id),
                "created_by_email": current_user.email,
                "created_at": prediction.created_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating quarterly prediction: {str(e)}")


@router.get("/annual", response_model=Dict)
async def get_annual_predictions(
    page: int = 1,
    size: int = 10,
    company_symbol: Optional[str] = None,
    reporting_year: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
    """Get paginated annual predictions (personal + organization data only - excludes system data)"""
    try:
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to view predictions"
            )

        query = db.query(
            AnnualPrediction,
            Company,
            Organization,
            User
        ).select_from(AnnualPrediction).join(
            Company, AnnualPrediction.company_id == Company.id
        ).outerjoin(
            Organization, AnnualPrediction.organization_id == Organization.id
        ).outerjoin(
            User, AnnualPrediction.created_by == User.id
        )
        
        access_filter = get_data_access_filter(current_user, AnnualPrediction, include_system=False)
        if access_filter is not None:
            query = query.filter(access_filter)
        
        if company_symbol:
            query = query.filter(Company.symbol.ilike(f"%{company_symbol}%"))
        if reporting_year:
            query = query.filter(AnnualPrediction.reporting_year == reporting_year)
        
        total = query.count()
        skip = (page - 1) * size
        results = query.offset(skip).limit(size).all()
        
        prediction_data = []
        for pred, company, organization, creator in results:            
            prediction_data.append({
                "id": str(pred.id),
                "company_id": str(company.id),
                "company_symbol": company.symbol,
                "company_name": company.name,
                "sector": company.sector,
                "market_cap": safe_float(company.market_cap),
                "reporting_year": pred.reporting_year,
                "reporting_quarter": pred.reporting_quarter,
                
                "long_term_debt_to_total_capital": safe_float(pred.long_term_debt_to_total_capital),
                "total_debt_to_ebitda": safe_float(pred.total_debt_to_ebitda),
                "net_income_margin": safe_float(pred.net_income_margin),
                "ebit_to_interest_expense": safe_float(pred.ebit_to_interest_expense),
                "return_on_assets": safe_float(pred.return_on_assets),
                
                "probability": safe_float(pred.probability),
                "risk_level": pred.risk_level,
                "confidence": safe_float(pred.confidence),
                
                "access_level": pred.access_level,
                "organization_id": str(pred.organization_id) if pred.organization_id else None,
                "organization_name": organization.name if organization else None,
                "created_by": str(pred.created_by),
                "created_by_email": creator.email if creator else None,
                "created_at": pred.created_at.isoformat(),
                "updated_at": pred.updated_at.isoformat() if pred.updated_at else None
            })
        
        return {
            "success": True,
            "predictions": prediction_data,
            "pagination": {
                "total": total,
                "page": page,
                "size": size,
                "pages": (total + size - 1) // size
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching annual predictions: {str(e)}")

@router.get("/quarterly", response_model=Dict)
async def get_quarterly_predictions(
    page: int = 1,
    size: int = 10,
    company_symbol: Optional[str] = None,
    reporting_year: Optional[str] = None,
    reporting_quarter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
    """Get paginated quarterly predictions (personal + organization data only - excludes system data)"""
    try:
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to view predictions"
            )

        query = db.query(
            QuarterlyPrediction,
            Company,
            Organization,
            User
        ).select_from(QuarterlyPrediction).join(
            Company, QuarterlyPrediction.company_id == Company.id
        ).outerjoin(
            Organization, QuarterlyPrediction.organization_id == Organization.id
        ).outerjoin(
            User, QuarterlyPrediction.created_by == User.id
        )
        
        access_filter = get_data_access_filter(current_user, QuarterlyPrediction, include_system=False)
        if access_filter is not None:
            query = query.filter(access_filter)
        if company_symbol:
            query = query.filter(Company.symbol.ilike(f"%{company_symbol}%"))
        if reporting_year:
            query = query.filter(QuarterlyPrediction.reporting_year == reporting_year)
        if reporting_quarter:
            query = query.filter(QuarterlyPrediction.reporting_quarter == reporting_quarter)
        
        total = query.count()
        skip = (page - 1) * size
        results = query.offset(skip).limit(size).all()
        
        prediction_data = []
        for pred, company, organization, creator in results:
            prediction_data.append({
                "id": str(pred.id),
                "company_id": str(company.id),
                "company_symbol": company.symbol,
                "company_name": company.name,
                "sector": company.sector,
                "market_cap": safe_float(company.market_cap),
                "reporting_year": pred.reporting_year,
                "reporting_quarter": pred.reporting_quarter,
                
                "total_debt_to_ebitda": safe_float(pred.total_debt_to_ebitda),
                "sga_margin": safe_float(pred.sga_margin),
                "long_term_debt_to_total_capital": safe_float(pred.long_term_debt_to_total_capital),
                "return_on_capital": safe_float(pred.return_on_capital),
                
                "logistic_probability": safe_float(pred.logistic_probability),
                "gbm_probability": safe_float(pred.gbm_probability),
                "ensemble_probability": safe_float(pred.ensemble_probability),
                "risk_level": pred.risk_level,
                "confidence": safe_float(pred.confidence),
                
                "access_level": pred.access_level,
                "organization_id": str(pred.organization_id) if pred.organization_id else None,
                "organization_name": organization.name if organization else None,
                "created_by": str(pred.created_by),
                "created_by_email": creator.email if creator else None,
                "created_at": pred.created_at.isoformat(),
                "updated_at": pred.updated_at.isoformat() if pred.updated_at else None
            })
        
        return {
            "success": True,
            "predictions": prediction_data,
            "pagination": {
                "total": total,
                "page": page,
                "size": size,
                "pages": (total + size - 1) // size
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching quarterly predictions: {str(e)}")


@router.get("/annual/system", response_model=Dict)
async def get_system_annual_predictions(
    page: int = 1,
    size: int = 10,
    company_symbol: Optional[str] = None,
    reporting_year: Optional[str] = None,
    sector: Optional[str] = None,
    risk_level: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
    """Get paginated system-level annual predictions (accessible to all user roles)"""
    try:
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to view system predictions"
            )

        query = db.query(
            AnnualPrediction,
            Company,
            User
        ).select_from(AnnualPrediction).join(
            Company, AnnualPrediction.company_id == Company.id
        ).outerjoin(
            User, AnnualPrediction.created_by == User.id
        ).filter(
            AnnualPrediction.access_level == "system"  # Only system-level predictions
        )
        
        if company_symbol:
            query = query.filter(Company.symbol.ilike(f"%{company_symbol}%"))
        if reporting_year:
            query = query.filter(AnnualPrediction.reporting_year == reporting_year)
        if sector:
            query = query.filter(Company.sector.ilike(f"%{sector}%"))
        if risk_level:
            query = query.filter(AnnualPrediction.risk_level == risk_level)
        
        query = query.order_by(AnnualPrediction.created_at.desc())
        
        total = query.count()
        skip = (page - 1) * size
        results = query.offset(skip).limit(size).all()
        
        prediction_data = []
        for pred, company, creator in results:            
            prediction_data.append({
                "id": str(pred.id),
                "company_id": str(company.id),
                "company_symbol": company.symbol,
                "company_name": company.name,
                "sector": company.sector,
                "market_cap": safe_float(company.market_cap),
                "reporting_year": pred.reporting_year,
                "reporting_quarter": pred.reporting_quarter,
                
                "long_term_debt_to_total_capital": safe_float(pred.long_term_debt_to_total_capital),
                "total_debt_to_ebitda": safe_float(pred.total_debt_to_ebitda),
                "net_income_margin": safe_float(pred.net_income_margin),
                "ebit_to_interest_expense": safe_float(pred.ebit_to_interest_expense),
                "return_on_assets": safe_float(pred.return_on_assets),
                
                "probability": safe_float(pred.probability),
                "risk_level": pred.risk_level,
                "confidence": safe_float(pred.confidence),
                
                "access_level": pred.access_level,
                "created_by": str(pred.created_by),
                "created_by_email": creator.email if creator else None,
                "created_at": pred.created_at.isoformat(),
                "predicted_at": pred.predicted_at.isoformat() if pred.predicted_at else None
            })
        
        return {
            "success": True,
            "message": "System-level annual predictions retrieved successfully",
            "predictions": prediction_data,
            "pagination": {
                "total": total,
                "page": page,
                "size": size,
                "pages": (total + size - 1) // size
            },
            "filters": {
                "access_level": "system",
                "company_symbol": company_symbol,
                "reporting_year": reporting_year,
                "sector": sector,
                "risk_level": risk_level
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching system annual predictions: {str(e)}")

@router.get("/quarterly/system", response_model=Dict)
async def get_system_quarterly_predictions(
    page: int = 1,
    size: int = 10,
    company_symbol: Optional[str] = None,
    reporting_year: Optional[str] = None,
    reporting_quarter: Optional[str] = None,
    sector: Optional[str] = None,
    risk_level: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
    """Get paginated system-level quarterly predictions (accessible to all user roles)"""
    try:
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to view system predictions"
            )

        query = db.query(
            QuarterlyPrediction,
            Company,
            User
        ).select_from(QuarterlyPrediction).join(
            Company, QuarterlyPrediction.company_id == Company.id
        ).outerjoin(
            User, QuarterlyPrediction.created_by == User.id
        ).filter(
            QuarterlyPrediction.access_level == "system"  # Only system-level predictions
        )
        
        if company_symbol:
            query = query.filter(Company.symbol.ilike(f"%{company_symbol}%"))
        if reporting_year:
            query = query.filter(QuarterlyPrediction.reporting_year == reporting_year)
        if reporting_quarter:
            query = query.filter(QuarterlyPrediction.reporting_quarter == reporting_quarter)
        if sector:
            query = query.filter(Company.sector.ilike(f"%{sector}%"))
        if risk_level:
            query = query.filter(QuarterlyPrediction.risk_level == risk_level)
        
        query = query.order_by(QuarterlyPrediction.created_at.desc())
        
        total = query.count()
        skip = (page - 1) * size
        results = query.offset(skip).limit(size).all()
        
        prediction_data = []
        for pred, company, creator in results:            
            prediction_data.append({
                "id": str(pred.id),
                "company_id": str(company.id),
                "company_symbol": company.symbol,
                "company_name": company.name,
                "sector": company.sector,
                "market_cap": safe_float(company.market_cap),
                "reporting_year": pred.reporting_year,
                "reporting_quarter": pred.reporting_quarter,
                
                "total_debt_to_ebitda": safe_float(pred.total_debt_to_ebitda),
                "sga_margin": safe_float(pred.sga_margin),
                "long_term_debt_to_total_capital": safe_float(pred.long_term_debt_to_total_capital),
                "return_on_capital": safe_float(pred.return_on_capital),
                
                "logistic_probability": safe_float(pred.logistic_probability),
                "gbm_probability": safe_float(pred.gbm_probability),
                "ensemble_probability": safe_float(pred.ensemble_probability),
                "risk_level": pred.risk_level,
                "confidence": safe_float(pred.confidence),
                
                "access_level": pred.access_level,
                "created_by": str(pred.created_by),
                "created_by_email": creator.email if creator else None,
                "created_at": pred.created_at.isoformat(),
                "predicted_at": pred.predicted_at.isoformat() if pred.predicted_at else None
            })
        
        return {
            "success": True,
            "message": "System-level quarterly predictions retrieved successfully",
            "predictions": prediction_data,
            "pagination": {
                "total": total,
                "page": page,
                "size": size,
                "pages": (total + size - 1) // size
            },
            "filters": {
                "access_level": "system",
                "company_symbol": company_symbol,
                "reporting_year": reporting_year,
                "reporting_quarter": reporting_quarter,
                "sector": sector,
                "risk_level": risk_level
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching system quarterly predictions: {str(e)}")


@router.post("/bulk-upload", response_model=Dict)
async def bulk_upload_predictions(
    file: UploadFile = File(...),
    prediction_type: str = "annual",  # annual or quarterly
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
    """Bulk upload predictions from CSV file"""
    try:
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to upload predictions"
            )

        if not file.filename.endswith('.csv'):
            raise HTTPException(
                status_code=400,
                detail="Only CSV files are supported for bulk upload"
            )

        import pandas as pd
        import io
        
        content = await file.read()
        df = pd.read_csv(io.StringIO(content.decode('utf-8')))
        
        organization_context = get_organization_context(current_user)
        access_level = get_user_access_level(current_user)
        
        if current_user.role == "super_admin":
            final_org_id = None  # System-level predictions
        elif current_user.organization_id:
            final_org_id = current_user.organization_id  # Organization predictions
        else:
            final_org_id = None  # Personal predictions (no org)
        
        results = {
            "success": True,
            "total_rows": len(df),
            "successful": 0,
            "failed": 0,
            "errors": []
        }
        
        for index, row in df.iterrows():
            try:
                company = create_or_get_company(
                    db=db,
                    company_symbol=row['company_symbol'],
                    company_name=row['company_name'],
                    market_cap=float(row['market_cap']),
                    sector=row['sector'],
                    user=current_user
                )
                
                if prediction_type == "annual":
                    existing_query = db.query(AnnualPrediction).filter(
                        AnnualPrediction.company_id == company.id,
                        AnnualPrediction.reporting_year == row['reporting_year'],
                        AnnualPrediction.organization_id == final_org_id
                    )
                    
                    if final_org_id is None and current_user.role != "super_admin":
                        existing_query = existing_query.filter(AnnualPrediction.created_by == str(current_user.id))
                    
                    existing = existing_query.first()
                    
                    if existing:
                        scope_text = "global" if current_user.role == "super_admin" else ("organization" if final_org_id else "personal")
                        results["errors"].append(f"Row {index + 1}: Annual prediction already exists for {row['company_symbol']} {row['reporting_year']} in your {scope_text} scope")
                        results["failed"] += 1
                        continue
                    
                    financial_data = {
                        'long_term_debt_to_total_capital': float(row['long_term_debt_to_total_capital']),
                        'total_debt_to_ebitda': float(row['total_debt_to_ebitda']),
                        'net_income_margin': float(row['net_income_margin']),
                        'ebit_to_interest_expense': float(row['ebit_to_interest_expense']),
                        'return_on_assets': float(row['return_on_assets'])
                    }
                    
                    ml_result = await ml_model.predict_annual(financial_data)
                    
                    prediction = AnnualPrediction(
                        id=uuid.uuid4(),
                        company_id=company.id,
                        organization_id=final_org_id,
                        reporting_year=row['reporting_year'],
                        long_term_debt_to_total_capital=financial_data['long_term_debt_to_total_capital'],
                        total_debt_to_ebitda=financial_data['total_debt_to_ebitda'],
                        net_income_margin=financial_data['net_income_margin'],
                        ebit_to_interest_expense=financial_data['ebit_to_interest_expense'],
                        return_on_assets=financial_data['return_on_assets'],
                        probability=ml_result['probability'],
                        risk_level=ml_result['risk_level'],
                        confidence=ml_result['confidence'],
                        predicted_at=datetime.utcnow(),
                        created_by=current_user.id
                    )
                    
                elif prediction_type == "quarterly":
                    existing_query = db.query(QuarterlyPrediction).filter(
                        QuarterlyPrediction.company_id == company.id,
                        QuarterlyPrediction.reporting_year == row['reporting_year'],
                        QuarterlyPrediction.reporting_quarter == row['reporting_quarter'],
                        QuarterlyPrediction.organization_id == final_org_id
                    )
                    
                    if final_org_id is None and current_user.role != "super_admin":
                        existing_query = existing_query.filter(QuarterlyPrediction.created_by == str(current_user.id))
                    
                    existing = existing_query.first()
                    
                    if existing:
                        scope_text = "global" if current_user.role == "super_admin" else ("organization" if final_org_id else "personal")
                        results["errors"].append(f"Row {index + 1}: Quarterly prediction already exists for {row['company_symbol']} {row['reporting_year']} {row['reporting_quarter']} in your {scope_text} scope")
                        results["failed"] += 1
                        continue
                    
                    financial_data = {
                        'total_debt_to_ebitda': float(row['total_debt_to_ebitda']),
                        'sga_margin': float(row['sga_margin']),
                        'long_term_debt_to_total_capital': float(row['long_term_debt_to_total_capital']),
                        'return_on_capital': float(row['return_on_capital'])
                    }
                    
                    ml_result = await quarterly_ml_model.predict_quarterly(financial_data)
                    
                    prediction = QuarterlyPrediction(
                        id=uuid.uuid4(),
                        company_id=company.id,
                        organization_id=final_org_id,
                        reporting_year=row['reporting_year'],
                        reporting_quarter=row['reporting_quarter'],
                        total_debt_to_ebitda=financial_data['total_debt_to_ebitda'],
                        sga_margin=financial_data['sga_margin'],
                        long_term_debt_to_total_capital=financial_data['long_term_debt_to_total_capital'],
                        return_on_capital=financial_data['return_on_capital'],
                        logistic_probability=ml_result.get('logistic_probability'),
                        gbm_probability=ml_result.get('gbm_probability'),
                        ensemble_probability=ml_result.get('ensemble_probability'),
                        risk_level=ml_result['risk_level'],
                        confidence=ml_result['confidence'],
                        predicted_at=datetime.utcnow(),
                        created_by=current_user.id
                    )
                
                db.add(prediction)
                results["successful"] += 1
                
            except Exception as e:
                results["errors"].append(f"Row {index + 1}: {str(e)}")
                results["failed"] += 1
                continue
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Bulk upload completed. {results['successful']} successful, {results['failed']} failed.",
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Bulk upload failed: {str(e)}")


@router.post("/annual/bulk-upload-async")
async def bulk_upload_annual_async(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
    """Async bulk upload annual predictions with job tracking"""
    try:
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to create predictions"
            )

        if not file.filename.endswith(('.csv', '.xlsx')):
            raise HTTPException(
                status_code=400,
                detail="Only CSV and Excel files are supported"
            )

        organization_context = get_organization_context(current_user)
        is_global = current_user.role == "super_admin"
        
        if current_user.role == "super_admin":
            final_org_id = None  # Global predictions
        elif current_user.organization_id:
            final_org_id = current_user.organization_id  # Organization predictions
        else:
            final_org_id = None  # User-specific predictions (no org)
        
        contents = await file.read()
        file_size = len(contents)
        
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(contents))
        
        required_columns = [
            'company_symbol', 'company_name', 'market_cap', 'sector',
            'reporting_year',
            'long_term_debt_to_total_capital', 'total_debt_to_ebitda',
            'net_income_margin', 'ebit_to_interest_expense', 'return_on_assets'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        data = df.to_dict('records')
        total_rows = len(data)
        
        if total_rows == 0:
            raise HTTPException(status_code=400, detail="No data found in file")
        
        if total_rows > 10000:  # Limit for safety
            raise HTTPException(status_code=400, detail="File contains too many rows (max 10,000)")
        
        from app.services.celery_bulk_upload_service import celery_bulk_upload_service
        
        job_id = await celery_bulk_upload_service.create_bulk_upload_job(
            user_id=str(current_user.id),
            organization_id=final_org_id,
            job_type='annual',
            filename=file.filename,
            file_size=file_size,
            total_rows=total_rows
        )
        
        task_info = await celery_bulk_upload_service.process_annual_bulk_upload(
            job_id=job_id,
            data=data,
            user_id=str(current_user.id),
            organization_id=final_org_id
        )
        
        return {
            "success": True,
            "message": "Bulk upload job started successfully using Celery workers",
            "job_id": job_id,
            "task_id": task_info['task_id'],
            "total_rows": total_rows,
            "estimated_time_minutes": task_info['estimated_time_minutes'],
            
            # NEW AUTO-SCALING FIELDS:
            "queue_priority": task_info['queue_priority'],
            "queue_position": task_info['queue_position'],
            "current_system_load": task_info['system_load'],
            "processing_message": task_info['processing_message'],
            "worker_capacity": task_info['current_worker_capacity']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting bulk upload: {str(e)}")

@router.post("/quarterly/bulk-upload-async")
async def bulk_upload_quarterly_async(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
    """Async bulk upload quarterly predictions with job tracking"""
    try:
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to create predictions"
            )

        if not file.filename.endswith(('.csv', '.xlsx')):
            raise HTTPException(
                status_code=400,
                detail="Only CSV and Excel files are supported"
            )

        organization_context = get_organization_context(current_user)
        access_level = get_user_access_level(current_user)
        
        if current_user.role == "super_admin":
            final_org_id = None  # System-level predictions
        elif current_user.organization_id:
            final_org_id = current_user.organization_id  # Organization predictions
        else:
            final_org_id = None  # Personal predictions (no org)
        
        contents = await file.read()
        file_size = len(contents)
        
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(contents))
        
        required_columns = [
            'company_symbol', 'company_name', 'market_cap', 'sector',
            'reporting_year', 'reporting_quarter',
            'total_debt_to_ebitda', 'sga_margin',
            'long_term_debt_to_total_capital', 'return_on_capital'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        data = df.to_dict('records')
        total_rows = len(data)
        
        if total_rows == 0:
            raise HTTPException(status_code=400, detail="No data found in file")
        
        if total_rows > 10000:
            raise HTTPException(status_code=400, detail="File contains too many rows (max 10,000)")
        
        # ADDITIONAL DATA VALIDATION - Fail early if data is invalid
        try:
            # Test the first row to ensure all required fields are accessible
            if len(data) > 0:
                test_row = data[0]
                
                # Validate required fields exist and are not None/empty
                required_test_fields = {
                    'company_symbol': test_row.get('company_symbol'),
                    'company_name': test_row.get('company_name'),
                    'reporting_year': test_row.get('reporting_year'),
                    'reporting_quarter': test_row.get('reporting_quarter'),
                    'total_debt_to_ebitda': test_row.get('total_debt_to_ebitda'),
                    'sga_margin': test_row.get('sga_margin'),
                    'long_term_debt_to_total_capital': test_row.get('long_term_debt_to_total_capital'),
                    'return_on_capital': test_row.get('return_on_capital')
                }
                
                # Check for missing or invalid field values
                invalid_fields = []
                for field_name, field_value in required_test_fields.items():
                    if field_value is None or str(field_value).strip() == '' or str(field_value).lower() in ['nan', 'null']:
                        invalid_fields.append(field_name)
                
                if invalid_fields:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"First row has invalid/missing values for required fields: {', '.join(invalid_fields)}. Please check your data format."
                    )
                
                # Test data iteration (same as worker task does)
                test_iteration_count = 0
                for i, row in enumerate(data[:3]):  # Test first 3 rows
                    if not row or not isinstance(row, dict):
                        raise HTTPException(
                            status_code=400,
                            detail=f"Row {i+1} is invalid or not a dictionary. Data format error."
                        )
                    test_iteration_count += 1
                
                if test_iteration_count == 0:
                    raise HTTPException(
                        status_code=400,
                        detail="Data iteration test failed - unable to access rows. File format may be corrupted."
                    )
                    
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Data validation failed: {str(e)}. Please check your file format and ensure all required columns have valid data."
            )
        
        from app.services.celery_bulk_upload_service import celery_bulk_upload_service
        
        job_id = await celery_bulk_upload_service.create_bulk_upload_job(
            user_id=str(current_user.id),
            organization_id=final_org_id,
            job_type='quarterly',
            filename=file.filename,
            file_size=file_size,
            total_rows=total_rows
        )
        
        task_info = await celery_bulk_upload_service.process_quarterly_bulk_upload(
            job_id=job_id,
            data=data,
            user_id=str(current_user.id),
            organization_id=final_org_id
        )
        
        return {
            "success": True,
            "message": "Bulk upload job started successfully using Celery workers",
            "job_id": job_id,
            "task_id": task_info['task_id'],
            "total_rows": total_rows,
            "estimated_time_minutes": task_info['estimated_time_minutes'],
            
            # NEW AUTO-SCALING FIELDS:
            "queue_priority": task_info['queue_priority'],
            "queue_position": task_info['queue_position'],
            "current_system_load": task_info['system_load'],
            "processing_message": task_info['processing_message'],
            "worker_capacity": task_info['current_worker_capacity']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting bulk upload: {str(e)}")

@router.get("/jobs/{job_id}/status")
async def get_bulk_upload_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
    """Get the status of a bulk upload job"""
    try:
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to view job status"
            )

        from app.services.celery_bulk_upload_service import celery_bulk_upload_service
        
        job_status = await celery_bulk_upload_service.get_job_status(job_id)
        
        if not job_status:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {
            "success": True,
            "job": job_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting job status: {str(e)}")


@router.get("/jobs/{job_id}/results")
async def get_bulk_upload_job_results(
    job_id: str,
    page: int = 1,
    page_size: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
    """Get the complete results of a bulk upload job including all processed companies and predictions"""
    try:
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to view job results"
            )

        # Validate pagination
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 1000:
            page_size = 100

        # First get the job info
        job = db.query(BulkUploadJob).filter(BulkUploadJob.id == job_id).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check if job is accessible by user (same organization or super admin)
        if not check_user_permissions(current_user, "super_admin"):
            if job.organization_id != current_user.organization_id:
                raise HTTPException(
                    status_code=403, 
                    detail="Access denied to this job"
                )
        
        # Build job summary
        job_summary = {
            "job_id": str(job.id),
            "status": job.status,
            "job_type": job.job_type,
            "original_filename": job.original_filename,
            "total_rows": job.total_rows or 0,
            "processed_rows": job.processed_rows or 0,
            "successful_rows": job.successful_rows or 0,
            "failed_rows": job.failed_rows or 0,
            "processing_time_seconds": None,
            "rows_per_second": None,
            "success_rate_percent": 0.0,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error_message": job.error_message,
            "error_details": json.loads(job.error_details) if job.error_details else []
        }
        
        # Calculate processing metrics if available
        if job.started_at and job.completed_at:
            processing_time = (job.completed_at - job.started_at).total_seconds()
            job_summary["processing_time_seconds"] = round(processing_time, 2)
            
            if processing_time > 0 and job.successful_rows:
                job_summary["rows_per_second"] = round(job.successful_rows / processing_time, 2)
        
        if job.total_rows and job.total_rows > 0:
            job_summary["success_rate_percent"] = round((job.successful_rows or 0) / job.total_rows * 100, 2)
        
        # Now get the actual prediction results based on job type
        prediction_results = []
        
        if job.job_type == "annual_prediction":
            # Get annual predictions created during this job timeframe
            query = db.query(AnnualPrediction, Company).join(
                Company, AnnualPrediction.company_id == Company.id
            )
            
            # Filter by organization if not super admin
            if not check_user_permissions(current_user, "super_admin"):
                if current_user.organization_id:
                    query = query.filter(Company.organization_id == current_user.organization_id)
                else:
                    query = query.filter(Company.organization_id.is_(None))
            
            # Filter by time range around job processing with tighter window
            if job.started_at:
                # Use a tighter time window - predictions should be created during job execution
                from datetime import timedelta
                # Use minimal buffer - job execution should be tightly controlled
                start_time = job.started_at - timedelta(seconds=30)  # 30 second buffer before
                end_time = job.completed_at if job.completed_at else (job.started_at + timedelta(hours=2))
                end_time = end_time + timedelta(seconds=30)  # 30 second buffer after
                
                query = query.filter(
                    AnnualPrediction.created_at >= start_time,
                    AnnualPrediction.created_at <= end_time
                )
                
                # Additional filtering by created_by user if available
                if job.user_id:
                    query = query.filter(AnnualPrediction.created_by == str(job.user_id))
            
            predictions = query.order_by(AnnualPrediction.created_at.desc()).limit(
                min(job.total_rows or 1000, 2000)  # Limit to job size or 2000 max
            ).all()
            
            # Apply pagination  
            total_predictions = len(predictions)
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_predictions = predictions[start_idx:end_idx]
            
            for prediction, company in paginated_predictions:
                prediction_results.append({
                    "company_symbol": company.symbol,
                    "company_name": company.company_name,
                    "company_sector": company.sector,
                    "prediction_id": str(prediction.id),
                    "default_probability": round(prediction.default_probability, 4),
                    "risk_category": prediction.risk_category,
                    "financial_metrics": {
                        "total_debt_to_ebitda": prediction.total_debt_to_ebitda,
                        "sga_margin": prediction.sga_margin,
                        "long_term_debt_to_total_capital": prediction.long_term_debt_to_total_capital,
                        "return_on_capital": prediction.return_on_capital,
                        "current_ratio": prediction.current_ratio,
                        "debt_to_equity": prediction.debt_to_equity,
                        "net_income_margin": prediction.net_income_margin,
                        "asset_turnover": prediction.asset_turnover,
                        "ebitda_margin": prediction.ebitda_margin,
                        "revenue_growth": prediction.revenue_growth,
                        "total_debt_to_total_assets": prediction.total_debt_to_total_assets,
                        "operating_margin": prediction.operating_margin,
                        "roa": prediction.roa,
                        "roe": prediction.roe
                    },
                    "created_at": prediction.created_at.isoformat() if prediction.created_at else None
                })
            
        elif job.job_type == "quarterly_prediction":
            # Get quarterly predictions created during this job timeframe
            query = db.query(QuarterlyPrediction, Company).join(
                Company, QuarterlyPrediction.company_id == Company.id
            )
            
            # Filter by organization if not super admin
            if not check_user_permissions(current_user, "super_admin"):
                if current_user.organization_id:
                    query = query.filter(Company.organization_id == current_user.organization_id)
                else:
                    query = query.filter(Company.organization_id.is_(None))
            
            # Filter by time range around job processing with tighter window
            if job.started_at:
                # Use a tighter time window - predictions should be created during job execution
                from datetime import timedelta
                # Use minimal buffer - job execution should be tightly controlled
                start_time = job.started_at - timedelta(seconds=30)  # 30 second buffer before
                end_time = job.completed_at if job.completed_at else (job.started_at + timedelta(hours=2))
                end_time = end_time + timedelta(seconds=30)  # 30 second buffer after
                
                query = query.filter(
                    QuarterlyPrediction.created_at >= start_time,
                    QuarterlyPrediction.created_at <= end_time
                )
                
                # Additional filtering by created_by user if available  
                if job.user_id:
                    query = query.filter(QuarterlyPrediction.created_by == str(job.user_id))
            
            predictions = query.order_by(QuarterlyPrediction.created_at.desc()).limit(
                min(job.total_rows or 1000, 2000)  # Limit to job size or 2000 max
            ).all()
            
            # Apply pagination
            total_predictions = len(predictions) 
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_predictions = predictions[start_idx:end_idx]
            
            for prediction, company in paginated_predictions:
                prediction_results.append({
                    "company_symbol": company.symbol,
                    "company_name": company.company_name,
                    "company_sector": company.sector,
                    "prediction_id": str(prediction.id),
                    "default_probability": round(prediction.default_probability, 4),
                    "risk_category": prediction.risk_category,
                    "financial_metrics": {
                        "total_debt_to_ebitda": prediction.total_debt_to_ebitda,
                        "sga_margin": prediction.sga_margin,
                        "long_term_debt_to_total_capital": prediction.long_term_debt_to_total_capital,
                        "return_on_capital": prediction.return_on_capital
                    },
                    "quarter": prediction.quarter,
                    "year": prediction.year,
                    "created_at": prediction.created_at.isoformat() if prediction.created_at else None
                })
        
        return {
            "success": True,
            "job_summary": job_summary,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_results": total_predictions if 'total_predictions' in locals() else 0,
                "total_pages": math.ceil((total_predictions if 'total_predictions' in locals() else 0) / page_size),
                "has_next": page * page_size < (total_predictions if 'total_predictions' in locals() else 0),
                "has_previous": page > 1
            },
            "results": prediction_results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job results: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting job results: {str(e)}")


@router.get("/jobs/{job_id}/download")
async def download_bulk_upload_job_results(
    job_id: str,
    format: str = "csv",  # csv or excel
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
    """Download the complete results of a bulk upload job as CSV or Excel file"""
    from fastapi.responses import StreamingResponse
    
    try:
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to download job results"
            )

        if format not in ["csv", "excel"]:
            raise HTTPException(status_code=400, detail="Format must be 'csv' or 'excel'")

        # Get job results using the existing endpoint logic (without pagination)
        job = db.query(BulkUploadJob).filter(BulkUploadJob.id == job_id).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check access permissions
        if not check_user_permissions(current_user, "super_admin"):
            if job.organization_id != current_user.organization_id:
                raise HTTPException(
                    status_code=403, 
                    detail="Access denied to this job"
                )

        # Get all predictions (no pagination for download)
        prediction_data = []
        
        if job.job_type == "annual_prediction":
            query = db.query(AnnualPrediction, Company).join(
                Company, AnnualPrediction.company_id == Company.id
            )
            
            # Apply same filters as results endpoint
            if not check_user_permissions(current_user, "super_admin"):
                if current_user.organization_id:
                    query = query.filter(Company.organization_id == current_user.organization_id)
                else:
                    query = query.filter(Company.organization_id.is_(None))
            
            if job.started_at:
                from datetime import timedelta
                start_time = job.started_at - timedelta(seconds=30)
                end_time = job.completed_at if job.completed_at else (job.started_at + timedelta(hours=2))
                end_time = end_time + timedelta(seconds=30)
                
                query = query.filter(
                    AnnualPrediction.created_at >= start_time,
                    AnnualPrediction.created_at <= end_time
                )
                
                if job.user_id:
                    query = query.filter(AnnualPrediction.created_by == str(job.user_id))
            
            predictions = query.order_by(AnnualPrediction.created_at.desc()).limit(
                min(job.total_rows or 1000, 5000)  # Higher limit for download
            ).all()
            
            for prediction, company in predictions:
                prediction_data.append({
                    "Company Symbol": company.symbol,
                    "Company Name": company.company_name,
                    "Sector": company.sector,
                    "Default Probability": round(prediction.default_probability, 4),
                    "Risk Category": prediction.risk_category,
                    "Reporting Year": prediction.reporting_year,
                    "Total Debt to EBITDA": prediction.total_debt_to_ebitda,
                    "SGA Margin": prediction.sga_margin,
                    "Long Term Debt to Total Capital": prediction.long_term_debt_to_total_capital,
                    "Return on Capital": prediction.return_on_capital,
                    "Current Ratio": prediction.current_ratio,
                    "Debt to Equity": prediction.debt_to_equity,
                    "Net Income Margin": prediction.net_income_margin,
                    "Asset Turnover": prediction.asset_turnover,
                    "EBITDA Margin": prediction.ebitda_margin,
                    "Revenue Growth": prediction.revenue_growth,
                    "Total Debt to Total Assets": prediction.total_debt_to_total_assets,
                    "Operating Margin": prediction.operating_margin,
                    "ROA": prediction.roa,
                    "ROE": prediction.roe,
                    "Created At": prediction.created_at.isoformat() if prediction.created_at else None
                })
                
        elif job.job_type == "quarterly_prediction":
            query = db.query(QuarterlyPrediction, Company).join(
                Company, QuarterlyPrediction.company_id == Company.id
            )
            
            # Apply same filters as results endpoint
            if not check_user_permissions(current_user, "super_admin"):
                if current_user.organization_id:
                    query = query.filter(Company.organization_id == current_user.organization_id)
                else:
                    query = query.filter(Company.organization_id.is_(None))
            
            if job.started_at:
                from datetime import timedelta
                start_time = job.started_at - timedelta(seconds=30)
                end_time = job.completed_at if job.completed_at else (job.started_at + timedelta(hours=2))
                end_time = end_time + timedelta(seconds=30)
                
                query = query.filter(
                    QuarterlyPrediction.created_at >= start_time,
                    QuarterlyPrediction.created_at <= end_time
                )
                
                if job.user_id:
                    query = query.filter(QuarterlyPrediction.created_by == str(job.user_id))
            
            predictions = query.order_by(QuarterlyPrediction.created_at.desc()).limit(
                min(job.total_rows or 1000, 5000)  # Higher limit for download
            ).all()
            
            for prediction, company in predictions:
                prediction_data.append({
                    "Company Symbol": company.symbol,
                    "Company Name": company.company_name,
                    "Sector": company.sector,
                    "Quarter": prediction.quarter,
                    "Year": prediction.year,
                    "Default Probability": round(prediction.default_probability, 4),
                    "Risk Category": prediction.risk_category,
                    "Total Debt to EBITDA": prediction.total_debt_to_ebitda,
                    "SGA Margin": prediction.sga_margin,
                    "Long Term Debt to Total Capital": prediction.long_term_debt_to_total_capital,
                    "Return on Capital": prediction.return_on_capital,
                    "Created At": prediction.created_at.isoformat() if prediction.created_at else None
                })

        if not prediction_data:
            raise HTTPException(status_code=404, detail="No prediction results found for this job")

        # Create DataFrame and export
        import pandas as pd
        df = pd.DataFrame(prediction_data)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"predictions_{job.job_type}_{job.original_filename}_{timestamp}"
        
        if format == "csv":
            # Create CSV
            output = io.StringIO()
            df.to_csv(output, index=False)
            output.seek(0)
            
            def iter_csv():
                yield output.getvalue().encode('utf-8')
            
            return StreamingResponse(
                iter_csv(),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={filename}.csv"}
            )
            
        elif format == "excel":
            # Create Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Predictions')
            output.seek(0)
            
            def iter_excel():
                yield output.getvalue()
            
            return StreamingResponse(
                iter_excel(),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={filename}.xlsx"}
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading job results: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error downloading job results: {str(e)}")


@router.get("/jobs")
async def list_bulk_upload_jobs(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
    """List bulk upload jobs for the current user/organization"""
    try:
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to view jobs"
            )

        organization_id = get_organization_context(current_user)
        
        query = db.query(BulkUploadJob)
        
        if organization_id:
            query = query.filter(BulkUploadJob.organization_id == organization_id)
        else:
            query = query.filter(BulkUploadJob.user_id == current_user.id)
        
        if status:
            query = query.filter(BulkUploadJob.status == status)
        
        query = query.order_by(BulkUploadJob.created_at.desc())
        
        total = query.count()
        jobs = query.offset(offset).limit(limit).all()
        
        job_list = []
        for job in jobs:
            progress_percentage = 0
            if job.total_rows and job.total_rows > 0 and job.processed_rows is not None:
                try:
                    progress = (job.processed_rows / job.total_rows) * 100
                    progress_percentage = round(progress, 2) if not (math.isnan(progress) or math.isinf(progress)) else 0
                except (ZeroDivisionError, TypeError):
                    progress_percentage = 0
            
            job_data = {
                'id': str(job.id),
                'status': job.status,
                'job_type': job.job_type,
                'original_filename': job.original_filename,
                'total_rows': job.total_rows or 0,
                'processed_rows': job.processed_rows or 0,
                'successful_rows': job.successful_rows or 0,
                'failed_rows': job.failed_rows or 0,
                'created_at': job.created_at.isoformat() if job.created_at else None,
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'progress_percentage': progress_percentage
            }
            job_list.append(job_data)
        
        return {
            "success": True,
            "jobs": job_list,
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing jobs: {str(e)}")

@router.get("/jobs/{job_id}")
async def get_job_details(
    job_id: str,
    include_errors: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
    """Get comprehensive job details including results and error information"""
    try:
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to view job details"
            )

        organization_id = get_organization_context(current_user)
        
        query = db.query(BulkUploadJob).filter(BulkUploadJob.id == job_id)
        
        if organization_id:
            query = query.filter(BulkUploadJob.organization_id == organization_id)
        else:
            query = query.filter(BulkUploadJob.user_id == current_user.id)
        
        job = query.first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found or access denied")

        progress_percentage = 0
        if job.total_rows and job.total_rows > 0 and job.processed_rows is not None:
            try:
                progress = (job.processed_rows / job.total_rows) * 100
                import math
                progress_percentage = round(progress, 2) if not (math.isnan(progress) or math.isinf(progress)) else 0
            except (ZeroDivisionError, TypeError):
                progress_percentage = 0

        celery_status = None
        celery_meta = None
        task_result = None
        
        try:
            from app.workers.celery_app import celery_app
            # Note: We would need to store celery_task_id in database for this to work
        except Exception:
            pass

        error_details_parsed = None
        if job.error_details and include_errors:
            try:
                import json
                error_details_parsed = json.loads(job.error_details)
            except (json.JSONDecodeError, TypeError):
                error_details_parsed = {"raw_error": job.error_details}

        processing_time_seconds = None
        if job.started_at and job.completed_at:
            processing_time_seconds = (job.completed_at - job.started_at).total_seconds()
        elif job.started_at:
            from datetime import datetime
            processing_time_seconds = (datetime.utcnow() - job.started_at).total_seconds()

        job_details = {
            "id": str(job.id),
            "status": job.status,
            "job_type": job.job_type,
            
            "file_info": {
                "original_filename": job.original_filename,
                "file_size": job.file_size,
                "file_size_mb": round(job.file_size / (1024 * 1024), 2) if job.file_size else None
            },
            
            "progress": {
                "total_rows": job.total_rows or 0,
                "processed_rows": job.processed_rows or 0,
                "successful_rows": job.successful_rows or 0,
                "failed_rows": job.failed_rows or 0,
                "progress_percentage": progress_percentage,
                "remaining_rows": (job.total_rows or 0) - (job.processed_rows or 0)
            },
            
            "performance": {
                "processing_time_seconds": processing_time_seconds,
                "rows_per_second": round((job.processed_rows or 0) / processing_time_seconds, 2) if processing_time_seconds and processing_time_seconds > 0 else None,
                "estimated_completion_time": None  # Could calculate based on current rate
            },
            
            "timestamps": {
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "updated_at": job.updated_at.isoformat() if job.updated_at else None
            },
            
            "context": {
                "user_id": str(job.user_id),
                "organization_id": str(job.organization_id) if job.organization_id else None,
                "created_by": job.user.username if job.user else None
            },
            
            "errors": {
                "has_errors": bool(job.error_message or job.error_details),
                "error_message": job.error_message if include_errors else None,
                "error_details": error_details_parsed if include_errors else None,
                "error_count": len(error_details_parsed.get('errors', [])) if error_details_parsed and isinstance(error_details_parsed, dict) else None
            } if include_errors else {
                "has_errors": bool(job.error_message or job.error_details),
                "error_count": len(json.loads(job.error_details).get('errors', [])) if job.error_details else 0
            },
            
            "celery_info": {
                "task_id": getattr(job, 'celery_task_id', None),
                "celery_status": celery_status,
                "celery_meta": celery_meta
            }
        }

        if job.status == "processing" and processing_time_seconds and job.processed_rows and job.total_rows:
            remaining_rows = job.total_rows - job.processed_rows
            if remaining_rows > 0 and processing_time_seconds > 0:
                rows_per_second = job.processed_rows / processing_time_seconds
                if rows_per_second > 0:
                    estimated_seconds = remaining_rows / rows_per_second
                    job_details["performance"]["estimated_completion_seconds"] = round(estimated_seconds, 0)
                    job_details["performance"]["estimated_completion_time"] = f"{int(estimated_seconds // 60)}m {int(estimated_seconds % 60)}s"

        return {
            "success": True,
            "job": job_details
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting job details: {str(e)}")

@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
    """Delete a bulk upload job (cannot delete jobs that are currently processing)"""
    try:
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to delete jobs"
            )

        organization_id = get_organization_context(current_user)
        
        query = db.query(BulkUploadJob).filter(BulkUploadJob.id == job_id)
        
        if organization_id:
            query = query.filter(BulkUploadJob.organization_id == organization_id)
        else:
            query = query.filter(BulkUploadJob.user_id == current_user.id)
        
        job = query.first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found or access denied")

        if job.status == "processing":
            processing_duration = None
            if job.started_at:
                processing_duration = (datetime.utcnow() - job.started_at).total_seconds()
            
            if processing_duration and processing_duration > 30:
                raise HTTPException(
                    status_code=400, 
                    detail="Cannot delete job that has been processing for more than 30 seconds. Please cancel the job first or wait for it to complete."
                )
            else:
                if hasattr(job, 'celery_task_id') and job.celery_task_id:
                    try:
                        from app.workers.celery_app import celery_app
                        celery_app.control.revoke(job.celery_task_id, terminate=True)
                        logger.info(f"Cancelled Celery task {job.celery_task_id} for job {job_id}")
                    except Exception as e:
                        logger.warning(f"Failed to cancel Celery task {job.celery_task_id}: {str(e)}")
        
        elif job.status in ["pending", "queued"] and hasattr(job, 'celery_task_id') and job.celery_task_id:
            try:
                from app.workers.celery_app import celery_app
                celery_app.control.revoke(job.celery_task_id, terminate=True)
                logger.info(f"Cancelled Celery task {job.celery_task_id} for {job.status} job {job_id}")
            except Exception as e:
                logger.warning(f"Failed to cancel Celery task {job.celery_task_id}: {str(e)}")

        db.delete(job)
        db.commit()

        return {
            "success": True,
            "message": f"Job {job_id} deleted successfully",
            "deleted_job": {
                "id": str(job.id),
                "status": job.status,
                "job_type": job.job_type,
                "original_filename": job.original_filename
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting job: {str(e)}")

@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
    """Cancel a running bulk upload job"""
    try:
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to cancel jobs"
            )

        organization_id = get_organization_context(current_user)
        
        query = db.query(BulkUploadJob).filter(BulkUploadJob.id == job_id)
        
        if organization_id:
            query = query.filter(BulkUploadJob.organization_id == organization_id)
        else:
            query = query.filter(BulkUploadJob.user_id == current_user.id)
        
        job = query.first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found or access denied")

        if job.status not in ["pending", "processing"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot cancel job with status '{job.status}'. Only pending or processing jobs can be cancelled."
            )

        celery_cancelled = False
        if hasattr(job, 'celery_task_id') and job.celery_task_id:
            try:
                from app.workers.celery_app import celery_app
                celery_app.control.revoke(job.celery_task_id, terminate=True)
                celery_cancelled = True
            except Exception as e:
                logger.warning(f"Failed to cancel Celery task {job.celery_task_id}: {str(e)}")

        job.status = "failed"
        job.error_message = "Job cancelled by user"
        job.completed_at = func.now()
        db.commit()

        return {
            "success": True,
            "message": f"Job {job_id} cancelled successfully",
            "cancelled_job": {
                "id": str(job.id),
                "status": job.status,
                "job_type": job.job_type,
                "original_filename": job.original_filename,
                "celery_cancelled": celery_cancelled
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error cancelling job: {str(e)}")


@router.put("/annual/{prediction_id}")
async def update_annual_prediction(
    prediction_id: str,
    request: AnnualPredictionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
    """Update an existing annual prediction with proper access control"""
    try:
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to update predictions"
            )

        prediction = db.query(AnnualPrediction).filter(AnnualPrediction.id == prediction_id).first()
        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")
        
        if prediction.access_level == "system":
            if current_user.role != "super_admin":
                raise HTTPException(
                    status_code=403,
                    detail="Only super admin can update system-level predictions"
                )
        else:
            can_update = False
            
            if current_user.role == "super_admin":
                can_update = True
                
            elif is_prediction_owner(prediction, current_user):
                can_update = True
                
            elif (prediction.access_level == "organization" and 
                  current_user.organization_id and 
                  prediction.organization_id == current_user.organization_id and
                  current_user.role in ["org_admin", "org_member"]):
                can_update = True
            
            if not can_update:
                if prediction.access_level == "organization":
                    if not current_user.organization_id:
                        detail = "You must be part of an organization to edit organization predictions"
                    elif prediction.organization_id != current_user.organization_id:
                        detail = "You can only edit predictions within your organization"
                    elif current_user.role not in ["org_admin", "org_member"]:
                        detail = "You need organization member role to edit organization predictions"
                    else:
                        detail = "You can only edit predictions that you created or organization predictions within your org"
                else:
                    detail = "You can only edit predictions that you created"
                    
                raise HTTPException(status_code=403, detail=detail)
        
        company = prediction.company
        company.name = request.company_name
        company.market_cap = request.market_cap  # Market cap should be stored as-is (already in millions)
        company.sector = request.sector
        
        financial_data = {
            'long_term_debt_to_total_capital': request.long_term_debt_to_total_capital,
            'total_debt_to_ebitda': request.total_debt_to_ebitda,
            'net_income_margin': request.net_income_margin,
            'ebit_to_interest_expense': request.ebit_to_interest_expense,
            'return_on_assets': request.return_on_assets
        }
        
        ml_result = await ml_model.predict_annual(financial_data)
        
        prediction.reporting_year = request.reporting_year
        prediction.reporting_quarter = request.reporting_quarter
        prediction.long_term_debt_to_total_capital = request.long_term_debt_to_total_capital
        prediction.total_debt_to_ebitda = request.total_debt_to_ebitda
        prediction.net_income_margin = request.net_income_margin
        prediction.ebit_to_interest_expense = request.ebit_to_interest_expense
        prediction.return_on_assets = request.return_on_assets
        prediction.probability = ml_result['probability']
        prediction.risk_level = ml_result['risk_level']
        prediction.confidence = ml_result['confidence']
        prediction.predicted_at = datetime.utcnow()
        
        db.commit()
        db.refresh(prediction)
        
        organization_name = None
        if prediction.organization_id:
            org = db.query(Organization).filter(Organization.id == prediction.organization_id).first()
            organization_name = org.name if org else None
        
        access_level = prediction.access_level
        
        return {
            "success": True,
            "message": f"Annual prediction updated for {request.company_symbol}",
            "prediction": {
                "id": str(prediction.id),
                "company_id": str(prediction.company_id),
                "company_symbol": request.company_symbol,
                "company_name": request.company_name,
                "sector": request.sector,
                "market_cap": float(request.market_cap),
                "reporting_year": request.reporting_year,
                "reporting_quarter": request.reporting_quarter,
                
                "long_term_debt_to_total_capital": float(request.long_term_debt_to_total_capital),
                "total_debt_to_ebitda": float(request.total_debt_to_ebitda),
                "net_income_margin": float(request.net_income_margin),
                "ebit_to_interest_expense": float(request.ebit_to_interest_expense),
                "return_on_assets": float(request.return_on_assets),
                
                "probability": float(ml_result['probability']),
                "risk_level": ml_result['risk_level'],
                "confidence": float(ml_result['confidence']),
                "predicted_at": prediction.predicted_at.isoformat(),
                
                "organization_id": str(prediction.organization_id) if prediction.organization_id else None,
                "organization_name": organization_name,
                "access_level": access_level,
                "created_by": str(prediction.created_by),
                "created_by_email": current_user.email,
                "created_at": prediction.created_at.isoformat(),
                "updated_at": prediction.updated_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating annual prediction: {str(e)}")

@router.delete("/annual/{prediction_id}")
async def delete_annual_prediction(
    prediction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
    """Delete an annual prediction with proper access control"""
    try:
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to delete predictions"
            )

        prediction = db.query(AnnualPrediction).filter(AnnualPrediction.id == prediction_id).first()
        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")
        
        if prediction.access_level == "system":
            if current_user.role != "super_admin":
                raise HTTPException(
                    status_code=403,
                    detail="Only super admin can delete system-level predictions"
                )
        else:
            can_delete = False
            
            if current_user.role == "super_admin":
                can_delete = True
                
            elif is_prediction_owner(prediction, current_user):
                can_delete = True
                
            elif (prediction.access_level == "organization" and 
                  current_user.organization_id and 
                  prediction.organization_id == current_user.organization_id and
                  current_user.role in ["org_admin", "org_member"]):
                can_delete = True
            
            if not can_delete:
                if prediction.access_level == "organization":
                    if not current_user.organization_id:
                        detail = "You must be part of an organization to delete organization predictions"
                    elif prediction.organization_id != current_user.organization_id:
                        detail = "You can only delete predictions within your organization"
                    elif current_user.role not in ["org_admin", "org_member"]:
                        detail = "You need organization member role to delete organization predictions"
                    else:
                        detail = "You can only delete predictions that you created or organization predictions within your org"
                else:
                    detail = "You can only delete predictions that you created"
                    
                raise HTTPException(status_code=403, detail=detail)
        
        db.delete(prediction)
        db.commit()
        
        return {
            "success": True,
            "message": f"Annual prediction deleted successfully",
            "deleted_id": prediction_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting annual prediction: {str(e)}")

@router.put("/quarterly/{prediction_id}")
async def update_quarterly_prediction(
    prediction_id: str,
    request: QuarterlyPredictionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
    """Update an existing quarterly prediction with proper access control"""
    try:
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to update predictions"
            )

        prediction = db.query(QuarterlyPrediction).filter(QuarterlyPrediction.id == prediction_id).first()
        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")
        
        if prediction.access_level == "system":
            if current_user.role != "super_admin":
                raise HTTPException(
                    status_code=403,
                    detail="Only super admin can update system-level predictions"
                )
        else:
            can_update = False
            
            if current_user.role == "super_admin":
                can_update = True
                
            elif is_prediction_owner(prediction, current_user):
                can_update = True
                
            elif (prediction.access_level == "organization" and 
                  current_user.organization_id and 
                  prediction.organization_id == current_user.organization_id and
                  current_user.role in ["org_admin", "org_member"]):
                can_update = True
            
            if not can_update:
                if prediction.access_level == "organization":
                    if not current_user.organization_id:
                        detail = "You must be part of an organization to update organization predictions"
                    elif prediction.organization_id != current_user.organization_id:
                        detail = "You can only update predictions within your organization"
                    elif current_user.role not in ["org_admin", "org_member"]:
                        detail = "You need organization member role to update organization predictions"
                    else:
                        detail = "You can only update predictions that you created or organization predictions within your org"
                else:
                    detail = "You can only update predictions that you created"
                    
                raise HTTPException(status_code=403, detail=detail)
        
        company = prediction.company
        company.name = request.company_name
        company.market_cap = request.market_cap   # Market cap should be stored as-is (already in millions)
        company.sector = request.sector
        
        financial_data = {
            'total_debt_to_ebitda': request.total_debt_to_ebitda,
            'sga_margin': request.sga_margin,
            'long_term_debt_to_total_capital': request.long_term_debt_to_total_capital,
            'return_on_capital': request.return_on_capital
        }
        
        ml_result = await quarterly_ml_model.predict_quarterly(financial_data)
        
        prediction.reporting_year = request.reporting_year
        prediction.reporting_quarter = request.reporting_quarter
        prediction.total_debt_to_ebitda = request.total_debt_to_ebitda
        prediction.sga_margin = request.sga_margin
        prediction.long_term_debt_to_total_capital = request.long_term_debt_to_total_capital
        prediction.return_on_capital = request.return_on_capital
        prediction.logistic_probability = ml_result.get('logistic_probability')
        prediction.gbm_probability = ml_result.get('gbm_probability')
        prediction.ensemble_probability = ml_result.get('ensemble_probability')
        prediction.risk_level = ml_result['risk_level']
        prediction.confidence = ml_result['confidence']
        prediction.predicted_at = datetime.utcnow()
        
        db.commit()
        db.refresh(prediction)
        
        organization_name = None
        if prediction.organization_id:
            org = db.query(Organization).filter(Organization.id == prediction.organization_id).first()
            organization_name = org.name if org else None
        
        access_level = prediction.access_level
        
        return {
            "success": True,
            "message": f"Quarterly prediction updated for {request.company_symbol}",
            "prediction": {
                "id": str(prediction.id),
                "company_id": str(prediction.company_id),
                "company_symbol": request.company_symbol,
                "company_name": request.company_name,
                "sector": request.sector,
                "market_cap": float(request.market_cap),
                "reporting_year": request.reporting_year,
                "reporting_quarter": request.reporting_quarter,
                
                "total_debt_to_ebitda": float(request.total_debt_to_ebitda),
                "sga_margin": float(request.sga_margin),
                "long_term_debt_to_total_capital": float(request.long_term_debt_to_total_capital),
                "return_on_capital": float(request.return_on_capital),
                
                "logistic_probability": float(ml_result.get('logistic_probability', 0)),
                "gbm_probability": float(ml_result.get('gbm_probability', 0)),
                "ensemble_probability": float(ml_result.get('ensemble_probability', 0)),
                "risk_level": ml_result['risk_level'],
                "confidence": float(ml_result['confidence']),
                "predicted_at": prediction.predicted_at.isoformat(),
                
                "organization_id": str(prediction.organization_id) if prediction.organization_id else None,
                "organization_name": organization_name,
                "access_level": access_level,
                "created_by": str(prediction.created_by),
                "created_by_email": current_user.email,
                "created_at": prediction.created_at.isoformat(),
                "updated_at": prediction.updated_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating quarterly prediction: {str(e)}")

@router.delete("/quarterly/{prediction_id}")
async def delete_quarterly_prediction(
    prediction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
    """Delete a quarterly prediction with proper access control"""
    try:
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to delete predictions"
            )

        prediction = db.query(QuarterlyPrediction).filter(QuarterlyPrediction.id == prediction_id).first()
        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")
        
        if prediction.access_level == "system":
            if current_user.role != "super_admin":
                raise HTTPException(
                    status_code=403,
                    detail="Only super admin can delete system-level predictions"
                )
        else:
            can_delete = False
            
            if current_user.role == "super_admin":
                can_delete = True
                
            elif is_prediction_owner(prediction, current_user):
                can_delete = True
                
            elif (prediction.access_level == "organization" and 
                  current_user.organization_id and 
                  prediction.organization_id == current_user.organization_id and
                  current_user.role in ["org_admin", "org_member"]):
                can_delete = True
            
            if not can_delete:
                if prediction.access_level == "organization":
                    if not current_user.organization_id:
                        detail = "You must be part of an organization to delete organization predictions"
                    elif prediction.organization_id != current_user.organization_id:
                        detail = "You can only delete predictions within your organization"
                    elif current_user.role not in ["org_admin", "org_member"]:
                        detail = "You need organization member role to delete organization predictions"
                    else:
                        detail = "You can only delete predictions that you created or organization predictions within your org"
                else:
                    detail = "You can only delete predictions that you created"
                    
                raise HTTPException(status_code=403, detail=detail)
        
        db.delete(prediction)
        db.commit()
        
        return {
            "success": True,
            "message": f"Quarterly prediction deleted successfully",
            "deleted_id": prediction_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting quarterly prediction: {str(e)}")


@router.get("/stats")
async def get_prediction_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
    """Get comprehensive prediction statistics - Available to all authenticated users"""
    try:
        pass  # Removed super admin restriction

        total_annual = db.query(AnnualPrediction).count()
        total_quarterly = db.query(QuarterlyPrediction).count()
        total_companies = db.query(Company).count()
        total_users = db.query(User).count()
        total_organizations = db.query(Organization).count()

        annual_by_access = {
            "personal": db.query(AnnualPrediction).filter(AnnualPrediction.access_level == "personal").count(),
            "organization": db.query(AnnualPrediction).filter(AnnualPrediction.access_level == "organization").count(),
            "system": db.query(AnnualPrediction).filter(AnnualPrediction.access_level == "system").count()
        }

        quarterly_by_access = {
            "personal": db.query(QuarterlyPrediction).filter(QuarterlyPrediction.access_level == "personal").count(),
            "organization": db.query(QuarterlyPrediction).filter(QuarterlyPrediction.access_level == "organization").count(),
            "system": db.query(QuarterlyPrediction).filter(QuarterlyPrediction.access_level == "system").count()
        }

        org_stats = []
        organizations = db.query(Organization).all()
        
        for org in organizations:
            org_annual_count = db.query(AnnualPrediction).filter(
                AnnualPrediction.organization_id == org.id
            ).count()
            
            org_quarterly_count = db.query(QuarterlyPrediction).filter(
                QuarterlyPrediction.organization_id == org.id
            ).count()
            
            org_user_count = db.query(User).filter(User.organization_id == org.id).count()
            
            org_stats.append({
                "organization_id": str(org.id),
                "organization_name": org.name,
                "organization_domain": org.domain,
                "user_count": org_user_count,
                "annual_predictions": org_annual_count,
                "quarterly_predictions": org_quarterly_count,
                "total_predictions": org_annual_count + org_quarterly_count
            })

        user_role_stats = {}
        for role in ["super_admin", "tenant_admin", "org_admin", "org_member", "user"]:
            role_users = db.query(User).filter(User.role == role).all()
            role_count = len(role_users)
            
            role_annual_count = 0
            role_quarterly_count = 0
            
            for user in role_users:
                role_annual_count += db.query(AnnualPrediction).filter(
                    AnnualPrediction.created_by == str(user.id)
                ).count()
                
                role_quarterly_count += db.query(QuarterlyPrediction).filter(
                    QuarterlyPrediction.created_by == str(user.id)
                ).count()
            
            user_role_stats[role] = {
                "user_count": role_count,
                "annual_predictions": role_annual_count,
                "quarterly_predictions": role_quarterly_count,
                "total_predictions": role_annual_count + role_quarterly_count
            }

        user_contributions = {}
        all_users = db.query(User).all()
        
        for user in all_users:
            annual_count = db.query(AnnualPrediction).filter(
                AnnualPrediction.created_by == str(user.id)
            ).count()
            
            quarterly_count = db.query(QuarterlyPrediction).filter(
                QuarterlyPrediction.created_by == str(user.id)
            ).count()
            
            total_count = annual_count + quarterly_count
            
            if total_count > 0:  # Only include users who have made predictions
                org_name = None
                if user.organization_id:
                    org = db.query(Organization).filter(Organization.id == user.organization_id).first()
                    org_name = org.name if org else None
                
                user_contributions[user.id] = {
                    "user_id": str(user.id),
                    "full_name": user.full_name,
                    "email": user.email,
                    "role": user.role,
                    "organization_name": org_name or "No Organization",
                    "annual_predictions": annual_count,
                    "quarterly_predictions": quarterly_count,
                    "total_predictions": total_count
                }
        
        top_contributors = sorted(
            user_contributions.values(), 
            key=lambda x: x["total_predictions"], 
            reverse=True
        )[:10]

        company_prediction_query = text("""
            SELECT 
                c.id,
                c.symbol,
                c.name,
                c.sector,
                c.access_level,
                COALESCE(annual_count, 0) as annual_count,
                COALESCE(quarterly_count, 0) as quarterly_count,
                COALESCE(annual_count, 0) + COALESCE(quarterly_count, 0) as total_count
            FROM companies c
            LEFT JOIN (
                SELECT company_id, COUNT(*) as annual_count 
                FROM annual_predictions 
                GROUP BY company_id
            ) ap ON c.id = ap.company_id
            LEFT JOIN (
                SELECT company_id, COUNT(*) as quarterly_count 
                FROM quarterly_predictions 
                GROUP BY company_id
            ) qp ON c.id = qp.company_id
            ORDER BY total_count DESC
            LIMIT 10
        """)
        
        company_result = db.execute(company_prediction_query).fetchall()
        top_companies = []
        
        for row in company_result:
            top_companies.append({
                "company_id": str(row.id),
                "symbol": row.symbol,
                "name": row.name,
                "sector": row.sector,
                "access_level": row.access_level,
                "annual_predictions": row.annual_count or 0,
                "quarterly_predictions": row.quarterly_count or 0,
                "total_predictions": row.total_count or 0
            })

        from datetime import datetime, timedelta
        
        seven_days_ago = datetime.now() - timedelta(days=7)
        
        recent_annual = db.query(AnnualPrediction).filter(
            AnnualPrediction.created_at >= seven_days_ago
        ).count()
        
        recent_quarterly = db.query(QuarterlyPrediction).filter(
            QuarterlyPrediction.created_at >= seven_days_ago
        ).count()

        return {
            "success": True,
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_predictions": total_annual + total_quarterly,
                "annual_predictions": total_annual,
                "quarterly_predictions": total_quarterly,
                "total_companies": total_companies,
                "total_users": total_users,
                "total_organizations": total_organizations,
                "recent_activity": {
                    "last_7_days": {
                        "annual": recent_annual,
                        "quarterly": recent_quarterly,
                        "total": recent_annual + recent_quarterly
                    }
                }
            },
            "breakdown": {
                "by_access_level": {
                    "annual": annual_by_access,
                    "quarterly": quarterly_by_access,
                    "combined": {
                        "personal": annual_by_access["personal"] + quarterly_by_access["personal"],
                        "organization": annual_by_access["organization"] + quarterly_by_access["organization"],
                        "system": annual_by_access["system"] + quarterly_by_access["system"]
                    }
                },
                "by_organization": org_stats,
                "by_user_role": user_role_stats
            },
            "insights": {
                "top_contributors": top_contributors,
                "most_predicted_companies": top_companies
            },
            "metadata": {
                "access_level_explanation": {
                    "personal": "Only creator can see - private data",
                    "organization": "All org members can see - shared data",
                    "system": "Everyone can see - public data"
                },
                "note": "Statistics generated for super admin dashboard"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating statistics: {str(e)}")



from pydantic import BaseModel
from typing import Optional

class DashboardRequest(BaseModel):
    include_platform_stats: bool = False
    organization_filter: Optional[str] = None
    custom_scope: Optional[str] = None

@router.post("/dashboard")
async def get_dashboard_post(
    request: DashboardRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
    """Enhanced dashboard API with SEPARATE user data and platform statistics"""
    try:
        if current_user.role == "super_admin":
            scope = "system"
        elif current_user.role in ["tenant_admin", "org_admin", "org_member"] and current_user.organization_id:
            scope = "organization"
        else:
            scope = "personal"

        if scope == "system":
            user_dashboard = await get_system_dashboard(db, current_user)
        elif scope == "organization":
            user_dashboard = await get_organization_dashboard(db, current_user)
        else:
            user_dashboard = await get_personal_dashboard(db, current_user)

        response = {
            "user_dashboard": user_dashboard,
            "scope": scope
        }

        if request.include_platform_stats:
            platform_stats = await get_platform_statistics(db)
            response["platform_statistics"] = platform_stats

        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")

async def get_system_dashboard(db: Session, current_user: User):
    """Get system-wide dashboard data"""
    total_companies = db.query(Company).count()
    
    annual_predictions = db.query(AnnualPrediction).count()
    quarterly_predictions = db.query(QuarterlyPrediction).count()
    total_predictions = annual_predictions + quarterly_predictions
    
    annual_avg = db.query(func.avg(AnnualPrediction.probability)).scalar() or 0
    quarterly_avg = db.query(func.avg(QuarterlyPrediction.logistic_probability)).scalar() or 0
    average_default_rate = (annual_avg + quarterly_avg) / 2 if (annual_avg or quarterly_avg) else 0
    
    high_risk_annual = db.query(AnnualPrediction).filter(AnnualPrediction.probability > 0.7).count()
    high_risk_quarterly = db.query(QuarterlyPrediction).filter(QuarterlyPrediction.logistic_probability > 0.7).count()
    high_risk_companies = high_risk_annual + high_risk_quarterly
    
    sectors_covered = db.query(Company.sector).distinct().count()
    
    return {
        "scope": "system",
        "user_name": current_user.full_name,
        "organization_name": "System Administrator",
        "total_companies": total_companies,
        "total_predictions": total_predictions,
        "annual_predictions": annual_predictions,
        "quarterly_predictions": quarterly_predictions,
        "average_default_rate": round(average_default_rate, 4),
        "high_risk_companies": high_risk_companies,
        "sectors_covered": sectors_covered,
        "data_scope": "All system data"
    }

async def get_organization_dashboard(db: Session, current_user: User):
    """Get organization-level dashboard data - ONLY ORG-SPECIFIC DATA"""
    if not current_user.organization_id:
        raise HTTPException(status_code=400, detail="User not associated with any organization")
    
    organization = db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    if current_user.role == "tenant_admin":
        companies = db.query(Company).all()
        annual_predictions = db.query(AnnualPrediction).all()
        quarterly_predictions = db.query(QuarterlyPrediction).all()
        data_scope_note = " (Cross-organization access - all orgs)"
    else:
        companies = db.query(Company).filter(
            Company.organization_id == current_user.organization_id
        ).all()
        
        annual_predictions = db.query(AnnualPrediction).filter(
            AnnualPrediction.organization_id == current_user.organization_id
        ).all()
        
        quarterly_predictions = db.query(QuarterlyPrediction).filter(
            QuarterlyPrediction.organization_id == current_user.organization_id
        ).all()
        data_scope_note = " (Organization data only)"
    
    total_companies = len(companies)
    annual_predictions_count = len(annual_predictions)
    quarterly_predictions_count = len(quarterly_predictions)
    total_predictions = annual_predictions_count + quarterly_predictions_count
    
    annual_probs = [p.probability for p in annual_predictions if p.probability is not None]
    quarterly_probs = [p.logistic_probability for p in quarterly_predictions if p.logistic_probability is not None]
    all_probs = annual_probs + quarterly_probs
    average_default_rate = sum(all_probs) / len(all_probs) if all_probs else 0
    
    high_risk_annual = len([p for p in annual_predictions if p.probability and p.probability > 0.7])
    high_risk_quarterly = len([p for p in quarterly_predictions if p.logistic_probability and p.logistic_probability > 0.7])
    high_risk_companies = high_risk_annual + high_risk_quarterly
    
    sectors = set([c.sector for c in companies if c.sector])
    sectors_covered = len(sectors)
    
    return {
        "scope": "organization",
        "user_name": current_user.full_name,
        "organization_name": organization.name,
        "total_companies": total_companies,
        "total_predictions": total_predictions,
        "annual_predictions": annual_predictions_count,
        "quarterly_predictions": quarterly_predictions_count,
        "average_default_rate": round(average_default_rate, 4),
        "high_risk_companies": high_risk_companies,
        "sectors_covered": sectors_covered,
        "data_scope": f"Data within {organization.name}" + data_scope_note
    }

async def get_personal_dashboard(db: Session, current_user: User):
    """Get personal dashboard data"""
    companies = db.query(Company).filter(Company.created_by == str(current_user.id)).all()
    
    annual_predictions = db.query(AnnualPrediction).filter(AnnualPrediction.created_by == str(current_user.id)).all()
    quarterly_predictions = db.query(QuarterlyPrediction).filter(QuarterlyPrediction.created_by == str(current_user.id)).all()
    
    total_companies = len(companies)
    annual_predictions_count = len(annual_predictions)
    quarterly_predictions_count = len(quarterly_predictions)
    total_predictions = annual_predictions_count + quarterly_predictions_count
    
    annual_probs = [p.probability for p in annual_predictions if p.probability is not None]
    quarterly_probs = [p.logistic_probability for p in quarterly_predictions if p.logistic_probability is not None]
    all_probs = annual_probs + quarterly_probs
    average_default_rate = sum(all_probs) / len(all_probs) if all_probs else 0
    
    high_risk_annual = len([p for p in annual_predictions if p.probability and p.probability > 0.7])
    high_risk_quarterly = len([p for p in quarterly_predictions if p.logistic_probability and p.logistic_probability > 0.7])
    high_risk_companies = high_risk_annual + high_risk_quarterly
    
    sectors = set([c.sector for c in companies if c.sector])
    sectors_covered = len(sectors)
    
    return {
        "scope": "personal",
        "user_name": current_user.full_name,
        "organization_name": "Personal Data",
        "total_companies": total_companies,
        "total_predictions": total_predictions,
        "annual_predictions": annual_predictions_count,
        "quarterly_predictions": quarterly_predictions_count,
        "average_default_rate": round(average_default_rate, 4),
        "high_risk_companies": high_risk_companies,
        "sectors_covered": sectors_covered,
        "data_scope": "Personal data only"
    }

async def get_platform_statistics(db: Session):
    """Get platform-wide statistics for inclusion in dashboard"""
    total_companies = db.query(Company).count()
    
    total_annual = db.query(AnnualPrediction).count()
    total_quarterly = db.query(QuarterlyPrediction).count()
    total_predictions = total_annual + total_quarterly
    
    annual_avg = db.query(func.avg(AnnualPrediction.probability)).scalar() or 0
    quarterly_avg = db.query(func.avg(QuarterlyPrediction.logistic_probability)).scalar() or 0
    platform_avg_default = (annual_avg + quarterly_avg) / 2 if (annual_avg or quarterly_avg) else 0
    
    high_risk_annual = db.query(AnnualPrediction).filter(AnnualPrediction.probability > 0.7).count()
    high_risk_quarterly = db.query(QuarterlyPrediction).filter(QuarterlyPrediction.logistic_probability > 0.7).count()
    platform_high_risk = high_risk_annual + high_risk_quarterly
    
    platform_sectors = db.query(Company.sector).distinct().count()
    
    return {
        "total_companies": total_companies,
        "total_predictions": total_predictions,
        "annual_predictions": total_annual,
        "quarterly_predictions": total_quarterly,
        "average_default_rate": round(platform_avg_default, 4),
        "high_risk_companies": platform_high_risk,
        "sectors_covered": platform_sectors
    }

@router.get("/debug/prediction/{prediction_id}")
async def debug_prediction_ownership(
    prediction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
    """Debug endpoint to check prediction ownership details"""
    try:
        prediction = db.query(AnnualPrediction).filter(AnnualPrediction.id == prediction_id).first()
        
        if not prediction:
            prediction = db.query(QuarterlyPrediction).filter(QuarterlyPrediction.id == prediction_id).first()
            prediction_type = "quarterly"
        else:
            prediction_type = "annual"
        
        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")
        
        current_user_id_str = str(current_user.id)
        prediction_created_by = prediction.created_by
        
        return {
            "debug_info": {
                "prediction_id": prediction_id,
                "prediction_type": prediction_type,
                "prediction_access_level": prediction.access_level,
                "prediction_created_by": prediction_created_by,
                "prediction_created_by_type": type(prediction_created_by).__name__,
                "current_user_id": current_user.id,
                "current_user_id_str": current_user_id_str,
                "current_user_id_type": type(current_user.id).__name__,
                "current_user_role": current_user.role,
                "ids_match_exact": prediction_created_by == current_user_id_str,
                "ids_match_both_str": str(prediction_created_by) == str(current_user_id_str),
                "permission_should_work": (
                    current_user.role == "super_admin" or 
                    (prediction.access_level != "system" and prediction_created_by == current_user_id_str)
                )
            },
            "current_user_details": {
                "id": current_user.id,
                "email": current_user.email,
                "full_name": current_user.full_name,
                "role": current_user.role,
                "organization_id": current_user.organization_id
            },
            "prediction_details": {
                "id": str(prediction.id),
                "access_level": prediction.access_level,
                "created_by": prediction.created_by,
                "organization_id": str(prediction.organization_id) if prediction.organization_id else None,
                "company_id": str(prediction.company_id),
                "created_at": prediction.created_at.isoformat() if prediction.created_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Debug error: {str(e)}")


@router.get("/health/redis", 
           summary="Redis Connection Health Check",
           description="Check if Redis connection is working for Celery tasks")
async def redis_health_check():
    """Check Redis connection health"""
    try:
        with celery_app.connection() as conn:
            conn.ensure_connection(max_retries=1, timeout=5)
        
        return {
            "status": "healthy",
            "redis": "connected",
            "broker_url": celery_app.conf.broker_url,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        return {
            "status": "unhealthy", 
            "redis": "disconnected", 
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
    """Check Redis connection health"""
    try:
        with celery_app.connection() as conn:
            conn.ensure_connection(max_retries=1, timeout=5)
        
        return {
            "status": "healthy",
            "redis": "connected",
            "broker_url": celery_app.conf.broker_url,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        return {
            "status": "unhealthy", 
            "redis": "disconnected", 
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
