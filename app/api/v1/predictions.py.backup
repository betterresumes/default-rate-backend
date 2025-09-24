from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import Dict, List, Optional
from datetime import datetime
import uuid
import pandas as pd
import io
import math
import logging
import json

# Core imports
from ...core.database import get_db, User, Company, AnnualPrediction, QuarterlyPrediction, Organization, BulkUploadJob
from ...schemas.schemas import (
    AnnualPredictionRequest, QuarterlyPredictionRequest
)
from ...services.ml_service import ml_model
from ...services.quarterly_ml_service import quarterly_ml_model
from .auth_multi_tenant import get_current_active_user as current_verified_user
from app.workers.celery_app import celery_app

router = APIRouter()

# Initialize logger
logger = logging.getLogger(__name__)

# ========================================
# SIMPLIFIED ACCESS CONTROL HELPERS  
# ========================================

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
        # Super admin sees everything only when specifically requesting system data
        return None
    
    # Personal data: only what the user created
    conditions.append(
        and_(
            prediction_model.access_level == "personal",
            prediction_model.created_by == str(user.id)
        )
    )
    
    # Organization data: if user is in an organization
    if user.organization_id:
        conditions.append(
            and_(
                prediction_model.access_level == "organization",
                prediction_model.organization_id == user.organization_id
            )
        )
    
    # System data: only include if explicitly requested
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
    
    # Check for existing company in the same access scope
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
    
    # Create new company
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
        import math
        float_val = float(value)
        if math.isnan(float_val) or math.isinf(float_val):
            return None
        return float_val
    except (ValueError, TypeError):
        return None

# ========================================
# ANNUAL PREDICTION ENDPOINTS
# ========================================

@router.post("/annual", response_model=Dict)
async def create_annual_prediction(
    request: AnnualPredictionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
    """Create annual prediction with simplified 3-level access control"""
    try:
        # Check permissions
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to create predictions"
            )

        # Get user's access level
        access_level = get_user_access_level(current_user)
        organization_id = current_user.organization_id if access_level == "organization" else None
        
        # Create or get company
        company = create_or_get_company(
            db=db,
            company_symbol=request.company_symbol,
            company_name=request.company_name,
            market_cap=request.market_cap,
            sector=request.sector,
            user=current_user
        )
        
        # Check if prediction already exists
        existing_query = db.query(AnnualPrediction).filter(
            AnnualPrediction.company_id == company.id,
            AnnualPrediction.reporting_year == request.reporting_year,
            AnnualPrediction.access_level == access_level
        )
        
        # Add specific filters based on access level
        if access_level == "organization":
            existing_query = existing_query.filter(AnnualPrediction.organization_id == organization_id)
        elif access_level == "personal":
            existing_query = existing_query.filter(AnnualPrediction.created_by == str(current_user.id))
        
        # Check for quarter
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
        
        # Prepare data for ML model
        financial_data = {
            'long_term_debt_to_total_capital': request.long_term_debt_to_total_capital,
            'total_debt_to_ebitda': request.total_debt_to_ebitda,
            'net_income_margin': request.net_income_margin,
            'ebit_to_interest_expense': request.ebit_to_interest_expense,
            'return_on_assets': request.return_on_assets
        }
        
        # Get ML prediction
        ml_result = await ml_model.predict_annual(financial_data)
        
        # Create prediction record
        prediction = AnnualPrediction(
            id=uuid.uuid4(),
            company_id=company.id,
            organization_id=organization_id,
            access_level=access_level,
            reporting_year=request.reporting_year,
            reporting_quarter=request.reporting_quarter,
            
            # Financial input data
            long_term_debt_to_total_capital=request.long_term_debt_to_total_capital,
            total_debt_to_ebitda=request.total_debt_to_ebitda,
            net_income_margin=request.net_income_margin,
            ebit_to_interest_expense=request.ebit_to_interest_expense,
            return_on_assets=request.return_on_assets,
            
            # ML prediction results
            probability=ml_result['probability'],
            risk_level=ml_result['risk_level'],
            confidence=ml_result['confidence'],
            predicted_at=datetime.utcnow(),
            
            # Metadata
            created_by=str(current_user.id)
        )
        
        db.add(prediction)
        db.commit()
        db.refresh(prediction)
        
        # Get organization name for response (if applicable)
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
                
                # Financial input ratios
                "long_term_debt_to_total_capital": float(request.long_term_debt_to_total_capital),
                "total_debt_to_ebitda": float(request.total_debt_to_ebitda),
                "net_income_margin": float(request.net_income_margin),
                "ebit_to_interest_expense": float(request.ebit_to_interest_expense),
                "return_on_assets": float(request.return_on_assets),
                
                # ML prediction results
                "probability": float(ml_result['probability']),
                "risk_level": ml_result['risk_level'],
                "confidence": float(ml_result['confidence']),
                
                # Simplified access control
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
        # Check permissions
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to create predictions"
            )

        # Get user's access level
        access_level = get_user_access_level(current_user)
        organization_id = current_user.organization_id if access_level == "organization" else None
        
        # Create or get company
        company = create_or_get_company(
            db=db,
            company_symbol=request.company_symbol,
            company_name=request.company_name,
            market_cap=request.market_cap,
            sector=request.sector,
            user=current_user
        )
        
        # Check if prediction already exists
        existing_query = db.query(QuarterlyPrediction).filter(
            QuarterlyPrediction.company_id == company.id,
            QuarterlyPrediction.reporting_year == request.reporting_year,
            QuarterlyPrediction.reporting_quarter == request.reporting_quarter,
            QuarterlyPrediction.access_level == access_level
        )
        
        # Add specific filters based on access level
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
        
        # Prepare data for ML model
        financial_data = {
            'total_debt_to_ebitda': request.total_debt_to_ebitda,
            'sga_margin': request.sga_margin,
            'long_term_debt_to_total_capital': request.long_term_debt_to_total_capital,
            'return_on_capital': request.return_on_capital
        }
        
        # Get ML prediction
        ml_result = await quarterly_ml_model.predict_quarterly(financial_data)
        
        # Create prediction record
        prediction = QuarterlyPrediction(
            id=uuid.uuid4(),
            company_id=company.id,
            organization_id=organization_id,
            access_level=access_level,
            reporting_year=request.reporting_year,
            reporting_quarter=request.reporting_quarter,
            
            # Financial input data
            total_debt_to_ebitda=request.total_debt_to_ebitda,
            sga_margin=request.sga_margin,
            long_term_debt_to_total_capital=request.long_term_debt_to_total_capital,
            return_on_capital=request.return_on_capital,
            
            # ML prediction results
            logistic_probability=ml_result.get('logistic_probability'),
            gbm_probability=ml_result.get('gbm_probability'),
            ensemble_probability=ml_result.get('ensemble_probability'),
            risk_level=ml_result['risk_level'],
            confidence=ml_result['confidence'],
            predicted_at=datetime.utcnow(),
            
            # Metadata
            created_by=str(current_user.id)
        )
        
        db.add(prediction)
        db.commit()
        db.refresh(prediction)
        
        # Get organization name if applicable
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
                
                # Financial input ratios
                "total_debt_to_ebitda": float(request.total_debt_to_ebitda),
                "sga_margin": float(request.sga_margin),
                "long_term_debt_to_total_capital": float(request.long_term_debt_to_total_capital),
                "return_on_capital": float(request.return_on_capital),
                
                # ML prediction results
                "logistic_probability": float(ml_result.get('logistic_probability', 0)),
                "gbm_probability": float(ml_result.get('gbm_probability', 0)),
                "ensemble_probability": float(ml_result.get('ensemble_probability', 0)),
                "risk_level": ml_result['risk_level'],
                "confidence": float(ml_result['confidence']),
                
                # Simplified access control
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
        
        # Prepare data for ML model
        financial_data = {
            'total_debt_to_ebitda': request.total_debt_to_ebitda,
            'sga_margin': request.sga_margin,
            'long_term_debt_to_total_capital': request.long_term_debt_to_total_capital,
            'return_on_capital': request.return_on_capital
        }
        
        # Get ML prediction
        ml_result = await quarterly_ml_model.predict_quarterly(financial_data)
        
        # Create prediction record
        prediction = QuarterlyPrediction(
            id=uuid.uuid4(),
            company_id=company.id,
            organization_id=final_org_id,
            reporting_year=request.reporting_year,
            reporting_quarter=request.reporting_quarter,
            
            # Financial input data
            total_debt_to_ebitda=request.total_debt_to_ebitda,
            sga_margin=request.sga_margin,
            long_term_debt_to_total_capital=request.long_term_debt_to_total_capital,
            return_on_capital=request.return_on_capital,
            
            # ML prediction results
            logistic_probability=ml_result.get('logistic_probability'),
            gbm_probability=ml_result.get('gbm_probability'),
            ensemble_probability=ml_result.get('ensemble_probability'),
            risk_level=ml_result['risk_level'],
            confidence=ml_result['confidence'],
            predicted_at=datetime.utcnow(),
            
            # Metadata
            created_by=current_user.id
        )
        
        db.add(prediction)
        db.commit()
        db.refresh(prediction)
        
        # Get organization name if applicable
        organization_name = None
        if final_org_id:
            org = db.query(Organization).filter(Organization.id == final_org_id).first()
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
                
                # Financial input ratios
                "total_debt_to_ebitda": float(request.total_debt_to_ebitda),
                "sga_margin": float(request.sga_margin),
                "long_term_debt_to_total_capital": float(request.long_term_debt_to_total_capital),
                "return_on_capital": float(request.return_on_capital),
                
                # ML prediction results
                "logistic_probability": float(ml_result.get('logistic_probability', 0)),
                "gbm_probability": float(ml_result.get('gbm_probability', 0)),
                "ensemble_probability": float(ml_result.get('ensemble_probability', 0)),
                "risk_level": ml_result['risk_level'],
                "confidence": float(ml_result['confidence']),
                
                # Simplified access control
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

# ========================================
# RETRIEVE PREDICTIONS
# ========================================

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
        # Check permissions
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to view predictions"
            )

        # Build query with joins for performance
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
        
        # Apply access control - exclude system data from regular endpoint
        access_filter = get_data_access_filter(current_user, AnnualPrediction, include_system=False)
        if access_filter is not None:
            query = query.filter(access_filter)
        
        # Apply additional filters
        if company_symbol:
            query = query.filter(Company.symbol.ilike(f"%{company_symbol}%"))
        if reporting_year:
            query = query.filter(AnnualPrediction.reporting_year == reporting_year)
        
        # Pagination
        total = query.count()
        skip = (page - 1) * size
        results = query.offset(skip).limit(size).all()
        
        # Format response with simplified access control info
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
                
                # Financial input ratios
                "long_term_debt_to_total_capital": safe_float(pred.long_term_debt_to_total_capital),
                "total_debt_to_ebitda": safe_float(pred.total_debt_to_ebitda),
                "net_income_margin": safe_float(pred.net_income_margin),
                "ebit_to_interest_expense": safe_float(pred.ebit_to_interest_expense),
                "return_on_assets": safe_float(pred.return_on_assets),
                
                # ML prediction results
                "probability": safe_float(pred.probability),
                "risk_level": pred.risk_level,
                "confidence": safe_float(pred.confidence),
                
                # Simplified access control
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
        # Check permissions
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to view predictions"
            )

        # Optimized query with joins
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
        
        # Apply access control - exclude system data from regular endpoint
        access_filter = get_data_access_filter(current_user, QuarterlyPrediction, include_system=False)
        if access_filter is not None:
            query = query.filter(access_filter)
        # Apply additional filters
        if company_symbol:
            query = query.filter(Company.symbol.ilike(f"%{company_symbol}%"))
        if reporting_year:
            query = query.filter(QuarterlyPrediction.reporting_year == reporting_year)
        if reporting_quarter:
            query = query.filter(QuarterlyPrediction.reporting_quarter == reporting_quarter)
        
        # Pagination
        total = query.count()
        skip = (page - 1) * size
        results = query.offset(skip).limit(size).all()
        
        # Format response with simplified access control
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
                
                # Financial input ratios
                "total_debt_to_ebitda": safe_float(pred.total_debt_to_ebitda),
                "sga_margin": safe_float(pred.sga_margin),
                "long_term_debt_to_total_capital": safe_float(pred.long_term_debt_to_total_capital),
                "return_on_capital": safe_float(pred.return_on_capital),
                
                # ML prediction results
                "logistic_probability": safe_float(pred.logistic_probability),
                "gbm_probability": safe_float(pred.gbm_probability),
                "ensemble_probability": safe_float(pred.ensemble_probability),
                "risk_level": pred.risk_level,
                "confidence": safe_float(pred.confidence),
                
                # Simplified access control
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

# ========================================
# SYSTEM-LEVEL PREDICTIONS ENDPOINTS
# ========================================

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
        # Check basic authentication (all roles allowed)
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to view system predictions"
            )

        # Build query with joins for performance - ONLY system-level predictions
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
        
        # Apply additional filters
        if company_symbol:
            query = query.filter(Company.symbol.ilike(f"%{company_symbol}%"))
        if reporting_year:
            query = query.filter(AnnualPrediction.reporting_year == reporting_year)
        if sector:
            query = query.filter(Company.sector.ilike(f"%{sector}%"))
        if risk_level:
            query = query.filter(AnnualPrediction.risk_level == risk_level)
        
        # Order by created_at desc for latest predictions first
        query = query.order_by(AnnualPrediction.created_at.desc())
        
        # Pagination
        total = query.count()
        skip = (page - 1) * size
        results = query.offset(skip).limit(size).all()
        
        # Format response
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
                
                # Financial input ratios
                "long_term_debt_to_total_capital": safe_float(pred.long_term_debt_to_total_capital),
                "total_debt_to_ebitda": safe_float(pred.total_debt_to_ebitda),
                "net_income_margin": safe_float(pred.net_income_margin),
                "ebit_to_interest_expense": safe_float(pred.ebit_to_interest_expense),
                "return_on_assets": safe_float(pred.return_on_assets),
                
                # ML prediction results
                "probability": safe_float(pred.probability),
                "risk_level": pred.risk_level,
                "confidence": safe_float(pred.confidence),
                
                # System-level metadata
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
        # Check basic authentication (all roles allowed)
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to view system predictions"
            )

        # Build query with joins for performance - ONLY system-level predictions
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
        
        # Apply additional filters
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
        
        # Order by created_at desc for latest predictions first
        query = query.order_by(QuarterlyPrediction.created_at.desc())
        
        # Pagination
        total = query.count()
        skip = (page - 1) * size
        results = query.offset(skip).limit(size).all()
        
        # Format response
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
                
                # Financial input ratios
                "total_debt_to_ebitda": safe_float(pred.total_debt_to_ebitda),
                "sga_margin": safe_float(pred.sga_margin),
                "long_term_debt_to_total_capital": safe_float(pred.long_term_debt_to_total_capital),
                "return_on_capital": safe_float(pred.return_on_capital),
                
                # ML prediction results
                "logistic_probability": safe_float(pred.logistic_probability),
                "gbm_probability": safe_float(pred.gbm_probability),
                "ensemble_probability": safe_float(pred.ensemble_probability),
                "risk_level": pred.risk_level,
                "confidence": safe_float(pred.confidence),
                
                # System-level metadata
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

# ========================================
# BULK UPLOAD ENDPOINT
# ========================================

@router.post("/bulk-upload", response_model=Dict)
async def bulk_upload_predictions(
    file: UploadFile = File(...),
    prediction_type: str = "annual",  # annual or quarterly
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
    """Bulk upload predictions from CSV file"""
    try:
        # Check permissions
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to upload predictions"
            )

        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(
                status_code=400,
                detail="Only CSV files are supported for bulk upload"
            )

        # Read CSV content
        import pandas as pd
        import io
        
        content = await file.read()
        df = pd.read_csv(io.StringIO(content.decode('utf-8')))
        
        # Get organization context
        organization_context = get_organization_context(current_user)
        access_level = get_user_access_level(current_user)
        
        # Determine final organization_id for predictions
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
        
        # Process each row
        for index, row in df.iterrows():
            try:
                # Create or get company
                company = create_or_get_company(
                    db=db,
                    company_symbol=row['company_symbol'],
                    company_name=row['company_name'],
                    market_cap=float(row['market_cap']),
                    sector=row['sector'],
                    user=current_user
                )
                
                if prediction_type == "annual":
                    # Check if annual prediction already exists within the same scope
                    existing_query = db.query(AnnualPrediction).filter(
                        AnnualPrediction.company_id == company.id,
                        AnnualPrediction.reporting_year == row['reporting_year'],
                        AnnualPrediction.organization_id == final_org_id
                    )
                    
                    # For user-specific predictions (no org), also check by created_by
                    if final_org_id is None and current_user.role != "super_admin":
                        existing_query = existing_query.filter(AnnualPrediction.created_by == str(current_user.id))
                    
                    existing = existing_query.first()
                    
                    if existing:
                        scope_text = "global" if current_user.role == "super_admin" else ("organization" if final_org_id else "personal")
                        results["errors"].append(f"Row {index + 1}: Annual prediction already exists for {row['company_symbol']} {row['reporting_year']} in your {scope_text} scope")
                        results["failed"] += 1
                        continue
                    
                    # Prepare ML data
                    financial_data = {
                        'long_term_debt_to_total_capital': float(row['long_term_debt_to_total_capital']),
                        'total_debt_to_ebitda': float(row['total_debt_to_ebitda']),
                        'net_income_margin': float(row['net_income_margin']),
                        'ebit_to_interest_expense': float(row['ebit_to_interest_expense']),
                        'return_on_assets': float(row['return_on_assets'])
                    }
                    
                    # Get ML prediction
                    ml_result = await ml_model.predict_annual(financial_data)
                    
                    # Create prediction
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
                    # Check if quarterly prediction already exists within the same scope
                    existing_query = db.query(QuarterlyPrediction).filter(
                        QuarterlyPrediction.company_id == company.id,
                        QuarterlyPrediction.reporting_year == row['reporting_year'],
                        QuarterlyPrediction.reporting_quarter == row['reporting_quarter'],
                        QuarterlyPrediction.organization_id == final_org_id
                    )
                    
                    # For user-specific predictions (no org), also check by created_by
                    if final_org_id is None and current_user.role != "super_admin":
                        existing_query = existing_query.filter(QuarterlyPrediction.created_by == str(current_user.id))
                    
                    existing = existing_query.first()
                    
                    if existing:
                        scope_text = "global" if current_user.role == "super_admin" else ("organization" if final_org_id else "personal")
                        results["errors"].append(f"Row {index + 1}: Quarterly prediction already exists for {row['company_symbol']} {row['reporting_year']} {row['reporting_quarter']} in your {scope_text} scope")
                        results["failed"] += 1
                        continue
                    
                    # Prepare ML data
                    financial_data = {
                        'total_debt_to_ebitda': float(row['total_debt_to_ebitda']),
                        'sga_margin': float(row['sga_margin']),
                        'long_term_debt_to_total_capital': float(row['long_term_debt_to_total_capital']),
                        'return_on_capital': float(row['return_on_capital'])
                    }
                    
                    # Get ML prediction
                    ml_result = await quarterly_ml_model.predict_quarterly(financial_data)
                    
                    # Create prediction
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
        
        # Commit all successful predictions
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

# ========================================
# ASYNC BULK UPLOAD WITH JOB TRACKING
# ========================================

@router.post("/annual/bulk-upload-async")
async def bulk_upload_annual_async(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
    """Async bulk upload annual predictions with job tracking"""
    try:
        # Check permissions
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to create predictions"
            )

        # Validate file type
        if not file.filename.endswith(('.csv', '.xlsx')):
            raise HTTPException(
                status_code=400,
                detail="Only CSV and Excel files are supported"
            )

        # Get organization context
        organization_context = get_organization_context(current_user)
        is_global = current_user.role == "super_admin"
        
        # Determine final organization_id for predictions
        if current_user.role == "super_admin":
            final_org_id = None  # Global predictions
        elif current_user.organization_id:
            final_org_id = current_user.organization_id  # Organization predictions
        else:
            final_org_id = None  # User-specific predictions (no org)
        
        # Read and validate file
        contents = await file.read()
        file_size = len(contents)
        
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(contents))
        
        # Validate required columns
        required_columns = [
            'company_symbol', 'company_name', 'market_cap', 'sector',
            'reporting_year', 'reporting_quarter',
            'long_term_debt_to_total_capital', 'total_debt_to_ebitda',
            'net_income_margin', 'ebit_to_interest_expense', 'return_on_assets'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        # Convert DataFrame to list of dictionaries
        data = df.to_dict('records')
        total_rows = len(data)
        
        if total_rows == 0:
            raise HTTPException(status_code=400, detail="No data found in file")
        
        if total_rows > 10000:  # Limit for safety
            raise HTTPException(status_code=400, detail="File contains too many rows (max 10,000)")
        
        # Create bulk upload job
        from app.services.celery_bulk_upload_service import celery_bulk_upload_service
        
        job_id = await celery_bulk_upload_service.create_bulk_upload_job(
            user_id=str(current_user.id),
            organization_id=final_org_id,
            job_type='annual',
            filename=file.filename,
            file_size=file_size,
            total_rows=total_rows
        )
        
        # Start Celery background processing
        task_id = await celery_bulk_upload_service.process_annual_bulk_upload(
            job_id=job_id,
            data=data,
            user_id=str(current_user.id),
            organization_id=final_org_id
        )
        
        return {
            "success": True,
            "message": "Bulk upload job started successfully using Celery workers",
            "job_id": job_id,
            "task_id": task_id,
            "total_rows": total_rows,
            "estimated_time_minutes": max(1, total_rows // 100)  # Rough estimate
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
        # Check permissions
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to create predictions"
            )

        # Validate file type
        if not file.filename.endswith(('.csv', '.xlsx')):
            raise HTTPException(
                status_code=400,
                detail="Only CSV and Excel files are supported"
            )

        # Get organization context
        organization_context = get_organization_context(current_user)
        access_level = get_user_access_level(current_user)
        
        # Determine final organization_id for predictions
        if current_user.role == "super_admin":
            final_org_id = None  # System-level predictions
        elif current_user.organization_id:
            final_org_id = current_user.organization_id  # Organization predictions
        else:
            final_org_id = None  # Personal predictions (no org)
        
        # Read and validate file
        contents = await file.read()
        file_size = len(contents)
        
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(contents))
        
        # Validate required columns
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
        
        # Convert DataFrame to list of dictionaries
        data = df.to_dict('records')
        total_rows = len(data)
        
        if total_rows == 0:
            raise HTTPException(status_code=400, detail="No data found in file")
        
        if total_rows > 10000:
            raise HTTPException(status_code=400, detail="File contains too many rows (max 10,000)")
        
        # Create bulk upload job
        from app.services.celery_bulk_upload_service import celery_bulk_upload_service
        
        job_id = await celery_bulk_upload_service.create_bulk_upload_job(
            user_id=str(current_user.id),
            organization_id=final_org_id,
            job_type='quarterly',
            filename=file.filename,
            file_size=file_size,
            total_rows=total_rows
        )
        
        # Start Celery background processing
        task_id = await celery_bulk_upload_service.process_quarterly_bulk_upload(
            job_id=job_id,
            data=data,
            user_id=str(current_user.id),
            organization_id=final_org_id
        )
        
        return {
            "success": True,
            "message": "Bulk upload job started successfully using Celery workers",
            "job_id": job_id,
            "task_id": task_id,
            "total_rows": total_rows,
            "estimated_time_minutes": max(1, total_rows // 100)
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
        # Check permissions
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
        # Check permissions
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to view jobs"
            )

        # Get organization context
        organization_id = get_organization_context(current_user)
        
        # Build query
        query = db.query(BulkUploadJob)
        
        # Filter by organization/user
        if organization_id:
            query = query.filter(BulkUploadJob.organization_id == organization_id)
        else:
            query = query.filter(BulkUploadJob.user_id == current_user.id)
        
        # Filter by status if provided
        if status:
            query = query.filter(BulkUploadJob.status == status)
        
        # Order by created_at desc
        query = query.order_by(BulkUploadJob.created_at.desc())
        
        # Apply pagination
        total = query.count()
        jobs = query.offset(offset).limit(limit).all()
        
        job_list = []
        for job in jobs:
            # Safe calculation of progress percentage
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
        # Check permissions
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to view job details"
            )

        # Get organization context for access control
        organization_id = get_organization_context(current_user)
        
        # Query the job with access control
        query = db.query(BulkUploadJob).filter(BulkUploadJob.id == job_id)
        
        # Apply organization/user filtering
        if organization_id:
            query = query.filter(BulkUploadJob.organization_id == organization_id)
        else:
            query = query.filter(BulkUploadJob.user_id == current_user.id)
        
        job = query.first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found or access denied")

        # Calculate progress percentage safely
        progress_percentage = 0
        if job.total_rows and job.total_rows > 0 and job.processed_rows is not None:
            try:
                progress = (job.processed_rows / job.total_rows) * 100
                import math
                progress_percentage = round(progress, 2) if not (math.isnan(progress) or math.isinf(progress)) else 0
            except (ZeroDivisionError, TypeError):
                progress_percentage = 0

        # Get Celery task status if available
        celery_status = None
        celery_meta = None
        task_result = None
        
        # Try to get celery task information
        try:
            from app.workers.celery_app import celery_app
            # Note: We would need to store celery_task_id in database for this to work
            # For now, we'll skip celery status integration
        except Exception:
            pass

        # Parse error details if they exist
        error_details_parsed = None
        if job.error_details and include_errors:
            try:
                import json
                error_details_parsed = json.loads(job.error_details)
            except (json.JSONDecodeError, TypeError):
                error_details_parsed = {"raw_error": job.error_details}

        # Calculate processing time
        processing_time_seconds = None
        if job.started_at and job.completed_at:
            processing_time_seconds = (job.completed_at - job.started_at).total_seconds()
        elif job.started_at:
            from datetime import datetime
            processing_time_seconds = (datetime.utcnow() - job.started_at).total_seconds()

        # Build comprehensive response
        job_details = {
            "id": str(job.id),
            "status": job.status,
            "job_type": job.job_type,
            
            # File information
            "file_info": {
                "original_filename": job.original_filename,
                "file_size": job.file_size,
                "file_size_mb": round(job.file_size / (1024 * 1024), 2) if job.file_size else None
            },
            
            # Progress information
            "progress": {
                "total_rows": job.total_rows or 0,
                "processed_rows": job.processed_rows or 0,
                "successful_rows": job.successful_rows or 0,
                "failed_rows": job.failed_rows or 0,
                "progress_percentage": progress_percentage,
                "remaining_rows": (job.total_rows or 0) - (job.processed_rows or 0)
            },
            
            # Performance metrics
            "performance": {
                "processing_time_seconds": processing_time_seconds,
                "rows_per_second": round((job.processed_rows or 0) / processing_time_seconds, 2) if processing_time_seconds and processing_time_seconds > 0 else None,
                "estimated_completion_time": None  # Could calculate based on current rate
            },
            
            # Timestamps
            "timestamps": {
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "updated_at": job.updated_at.isoformat() if job.updated_at else None
            },
            
            # User and organization info
            "context": {
                "user_id": str(job.user_id),
                "organization_id": str(job.organization_id) if job.organization_id else None,
                "created_by": job.user.username if job.user else None
            },
            
            # Error information (only if requested and exists)
            "errors": {
                "has_errors": bool(job.error_message or job.error_details),
                "error_message": job.error_message if include_errors else None,
                "error_details": error_details_parsed if include_errors else None,
                "error_count": len(error_details_parsed.get('errors', [])) if error_details_parsed and isinstance(error_details_parsed, dict) else None
            } if include_errors else {
                "has_errors": bool(job.error_message or job.error_details),
                "error_count": len(json.loads(job.error_details).get('errors', [])) if job.error_details else 0
            },
            
            # Celery information (if available)
            "celery_info": {
                "task_id": getattr(job, 'celery_task_id', None),
                "celery_status": celery_status,
                "celery_meta": celery_meta
            }
        }

        # Add estimated completion time for active jobs
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
        # Check permissions
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to delete jobs"
            )

        # Get organization context for access control
        organization_id = get_organization_context(current_user)
        
        # Query the job with access control
        query = db.query(BulkUploadJob).filter(BulkUploadJob.id == job_id)
        
        # Apply organization/user filtering
        if organization_id:
            query = query.filter(BulkUploadJob.organization_id == organization_id)
        else:
            query = query.filter(BulkUploadJob.user_id == current_user.id)
        
        job = query.first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found or access denied")

        # Enhanced job deletion logic
        # Allow deletion of jobs that aren't actively processing or that can be safely cancelled
        if job.status == "processing":
            # Check if job has been running for a reasonable time
            # If it's been processing for less than 30 seconds, allow deletion (likely just started)
            processing_duration = None
            if job.started_at:
                processing_duration = (datetime.utcnow() - job.started_at).total_seconds()
            
            if processing_duration and processing_duration > 30:
                # Job has been processing for more than 30 seconds, require explicit cancellation
                raise HTTPException(
                    status_code=400, 
                    detail="Cannot delete job that has been processing for more than 30 seconds. Please cancel the job first or wait for it to complete."
                )
            else:
                # Job just started processing or no start time, allow deletion but try to cancel Celery task
                if hasattr(job, 'celery_task_id') and job.celery_task_id:
                    try:
                        from app.workers.celery_app import celery_app
                        celery_app.control.revoke(job.celery_task_id, terminate=True)
                        logger.info(f"Cancelled Celery task {job.celery_task_id} for job {job_id}")
                    except Exception as e:
                        logger.warning(f"Failed to cancel Celery task {job.celery_task_id}: {str(e)}")
        
        # For pending/queued jobs, also try to cancel Celery task if it exists
        elif job.status in ["pending", "queued"] and hasattr(job, 'celery_task_id') and job.celery_task_id:
            try:
                from app.workers.celery_app import celery_app
                celery_app.control.revoke(job.celery_task_id, terminate=True)
                logger.info(f"Cancelled Celery task {job.celery_task_id} for {job.status} job {job_id}")
            except Exception as e:
                logger.warning(f"Failed to cancel Celery task {job.celery_task_id}: {str(e)}")

        # Delete the job
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
        # Check permissions
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to cancel jobs"
            )

        # Get organization context for access control
        organization_id = get_organization_context(current_user)
        
        # Query the job with access control
        query = db.query(BulkUploadJob).filter(BulkUploadJob.id == job_id)
        
        # Apply organization/user filtering
        if organization_id:
            query = query.filter(BulkUploadJob.organization_id == organization_id)
        else:
            query = query.filter(BulkUploadJob.user_id == current_user.id)
        
        job = query.first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found or access denied")

        # Only allow cancellation of pending or processing jobs
        if job.status not in ["pending", "processing"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot cancel job with status '{job.status}'. Only pending or processing jobs can be cancelled."
            )

        # Try to cancel Celery task if available
        celery_cancelled = False
        if hasattr(job, 'celery_task_id') and job.celery_task_id:
            try:
                from app.workers.celery_app import celery_app
                celery_app.control.revoke(job.celery_task_id, terminate=True)
                celery_cancelled = True
            except Exception as e:
                logger.warning(f"Failed to cancel Celery task {job.celery_task_id}: {str(e)}")

        # Update job status
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

# ========================================
# UPDATE AND DELETE PREDICTIONS
# ========================================

@router.put("/annual/{prediction_id}")
async def update_annual_prediction(
    prediction_id: str,
    request: AnnualPredictionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
    """Update an existing annual prediction with proper access control"""
    try:
        # Basic authentication check
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to update predictions"
            )

        # Find the prediction first
        prediction = db.query(AnnualPrediction).filter(AnnualPrediction.id == prediction_id).first()
        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")
        
        # ENHANCED PERMISSION LOGIC:
        # 1. System-level predictions: ONLY super_admin can modify
        if prediction.access_level == "system":
            if current_user.role != "super_admin":
                raise HTTPException(
                    status_code=403,
                    detail="Only super admin can update system-level predictions"
                )
        else:
            # 2. Non-system predictions: Multiple permission paths
            can_update = False
            
            # Path 1: Super admin can edit anything
            if current_user.role == "super_admin":
                can_update = True
                
            # Path 2: Creator can edit their own prediction
            elif prediction.created_by == str(current_user.id):
                can_update = True
                
            # Path 3: Organization-level predictions - org members can edit
            elif (prediction.access_level == "organization" and 
                  current_user.organization_id and 
                  prediction.organization_id == current_user.organization_id and
                  current_user.role in ["org_admin", "org_member"]):
                can_update = True
            
            if not can_update:
                # Provide detailed error message for debugging
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
        
        # Update company information
        company = prediction.company
        company.name = request.company_name
        company.market_cap = request.market_cap  # Market cap should be stored as-is (already in millions)
        company.sector = request.sector
        
        # Prepare data for ML model
        financial_data = {
            'long_term_debt_to_total_capital': request.long_term_debt_to_total_capital,
            'total_debt_to_ebitda': request.total_debt_to_ebitda,
            'net_income_margin': request.net_income_margin,
            'ebit_to_interest_expense': request.ebit_to_interest_expense,
            'return_on_assets': request.return_on_assets
        }
        
        # Get new ML prediction
        ml_result = await ml_model.predict_annual(financial_data)
        
        # Update prediction
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
        
        # Get organization name for response (if applicable)
        organization_name = None
        if prediction.organization_id:
            org = db.query(Organization).filter(Organization.id == prediction.organization_id).first()
            organization_name = org.name if org else None
        
        # Use the new access level system
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
                
                # Financial input ratios (updated values)
                "long_term_debt_to_total_capital": float(request.long_term_debt_to_total_capital),
                "total_debt_to_ebitda": float(request.total_debt_to_ebitda),
                "net_income_margin": float(request.net_income_margin),
                "ebit_to_interest_expense": float(request.ebit_to_interest_expense),
                "return_on_assets": float(request.return_on_assets),
                
                # ML prediction results (updated values)
                "probability": float(ml_result['probability']),
                "risk_level": ml_result['risk_level'],
                "confidence": float(ml_result['confidence']),
                "predicted_at": prediction.predicted_at.isoformat(),
                
                # Organization context
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
        # Basic authentication check
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to delete predictions"
            )

        # Find the prediction first
        prediction = db.query(AnnualPrediction).filter(AnnualPrediction.id == prediction_id).first()
        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")
        
        # ENHANCED PERMISSION LOGIC:
        # 1. System-level predictions: ONLY super_admin can modify
        if prediction.access_level == "system":
            if current_user.role != "super_admin":
                raise HTTPException(
                    status_code=403,
                    detail="Only super admin can delete system-level predictions"
                )
        else:
            # 2. Non-system predictions: Multiple permission paths
            can_delete = False
            
            # Path 1: Super admin can delete anything
            if current_user.role == "super_admin":
                can_delete = True
                
            # Path 2: Creator can delete their own prediction
            elif prediction.created_by == str(current_user.id):
                can_delete = True
                
            # Path 3: Organization-level predictions - org members can delete
            elif (prediction.access_level == "organization" and 
                  current_user.organization_id and 
                  prediction.organization_id == current_user.organization_id and
                  current_user.role in ["org_admin", "org_member"]):
                can_delete = True
            
            if not can_delete:
                # Provide detailed error message for debugging
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
        # Basic authentication check
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to update predictions"
            )

        # Find the prediction first
        prediction = db.query(QuarterlyPrediction).filter(QuarterlyPrediction.id == prediction_id).first()
        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")
        
        # ENHANCED PERMISSION LOGIC:
        # 1. System-level predictions: ONLY super_admin can modify
        if prediction.access_level == "system":
            if current_user.role != "super_admin":
                raise HTTPException(
                    status_code=403,
                    detail="Only super admin can update system-level predictions"
                )
        else:
            # 2. Non-system predictions: Multiple permission paths
            can_update = False
            
            # Path 1: Super admin can update anything
            if current_user.role == "super_admin":
                can_update = True
                
            # Path 2: Creator can update their own prediction
            elif prediction.created_by == str(current_user.id):
                can_update = True
                
            # Path 3: Organization-level predictions - org members can update
            elif (prediction.access_level == "organization" and 
                  current_user.organization_id and 
                  prediction.organization_id == current_user.organization_id and
                  current_user.role in ["org_admin", "org_member"]):
                can_update = True
            
            if not can_update:
                # Provide detailed error message for debugging
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
        
        # Update company information
        company = prediction.company
        company.name = request.company_name
        company.market_cap = request.market_cap   # Market cap should be stored as-is (already in millions)
        company.sector = request.sector
        
        # Prepare data for ML model
        financial_data = {
            'total_debt_to_ebitda': request.total_debt_to_ebitda,
            'sga_margin': request.sga_margin,
            'long_term_debt_to_total_capital': request.long_term_debt_to_total_capital,
            'return_on_capital': request.return_on_capital
        }
        
        # Get new ML prediction
        ml_result = await quarterly_ml_model.predict_quarterly(financial_data)
        
        # Update prediction
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
        
        # Get organization name for response (if applicable)
        organization_name = None
        if prediction.organization_id:
            org = db.query(Organization).filter(Organization.id == prediction.organization_id).first()
            organization_name = org.name if org else None
        
        # Use the new access level system
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
                
                # Financial input ratios (updated values)
                "total_debt_to_ebitda": float(request.total_debt_to_ebitda),
                "sga_margin": float(request.sga_margin),
                "long_term_debt_to_total_capital": float(request.long_term_debt_to_total_capital),
                "return_on_capital": float(request.return_on_capital),
                
                # ML prediction results (updated values)
                "logistic_probability": float(ml_result.get('logistic_probability', 0)),
                "gbm_probability": float(ml_result.get('gbm_probability', 0)),
                "ensemble_probability": float(ml_result.get('ensemble_probability', 0)),
                "risk_level": ml_result['risk_level'],
                "confidence": float(ml_result['confidence']),
                "predicted_at": prediction.predicted_at.isoformat(),
                
                # Organization context
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
        # Basic authentication check
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to delete predictions"
            )

        # Find the prediction first
        prediction = db.query(QuarterlyPrediction).filter(QuarterlyPrediction.id == prediction_id).first()
        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")
        
        # ENHANCED PERMISSION LOGIC:
        # 1. System-level predictions: ONLY super_admin can modify
        if prediction.access_level == "system":
            if current_user.role != "super_admin":
                raise HTTPException(
                    status_code=403,
                    detail="Only super admin can delete system-level predictions"
                )
        else:
            # 2. Non-system predictions: Multiple permission paths
            can_delete = False
            
            # Path 1: Super admin can delete anything
            if current_user.role == "super_admin":
                can_delete = True
                
            # Path 2: Creator can delete their own prediction
            elif prediction.created_by == str(current_user.id):
                can_delete = True
                
            # Path 3: Organization-level predictions - org members can delete
            elif (prediction.access_level == "organization" and 
                  current_user.organization_id and 
                  prediction.organization_id == current_user.organization_id and
                  current_user.role in ["org_admin", "org_member"]):
                can_delete = True
            
            if not can_delete:
                # Provide detailed error message for debugging
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

# ========================================
# SUPER ADMIN STATISTICS API
# ========================================

@router.get("/stats")
async def get_prediction_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
    """Get comprehensive prediction statistics - Available to all authenticated users"""
    try:
        # All authenticated users can access platform statistics
        pass  # Removed super admin restriction

        # === BASIC COUNTS ===
        total_annual = db.query(AnnualPrediction).count()
        total_quarterly = db.query(QuarterlyPrediction).count()
        total_companies = db.query(Company).count()
        total_users = db.query(User).count()
        total_organizations = db.query(Organization).count()

        # === ACCESS LEVEL BREAKDOWN ===
        # Annual predictions by access level
        annual_by_access = {
            "personal": db.query(AnnualPrediction).filter(AnnualPrediction.access_level == "personal").count(),
            "organization": db.query(AnnualPrediction).filter(AnnualPrediction.access_level == "organization").count(),
            "system": db.query(AnnualPrediction).filter(AnnualPrediction.access_level == "system").count()
        }

        # Quarterly predictions by access level
        quarterly_by_access = {
            "personal": db.query(QuarterlyPrediction).filter(QuarterlyPrediction.access_level == "personal").count(),
            "organization": db.query(QuarterlyPrediction).filter(QuarterlyPrediction.access_level == "organization").count(),
            "system": db.query(QuarterlyPrediction).filter(QuarterlyPrediction.access_level == "system").count()
        }

        # === ORGANIZATION BREAKDOWN ===
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

        # === USER ROLE BREAKDOWN ===
        user_role_stats = {}
        for role in ["super_admin", "tenant_admin", "org_admin", "org_member", "user"]:
            role_users = db.query(User).filter(User.role == role).all()
            role_count = len(role_users)
            
            # Count predictions by users with this role
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

        # === TOP CONTRIBUTORS ===
        # Get users who created the most predictions using simple ORM queries
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
                # Get organization name
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
        
        # Sort by total predictions and take top 10
        top_contributors = sorted(
            user_contributions.values(), 
            key=lambda x: x["total_predictions"], 
            reverse=True
        )[:10]

        # === COMPANY BREAKDOWN ===
        # Most predicted companies
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

        # === RECENT ACTIVITY ===
        # Get recent predictions (last 7 days)
        from datetime import datetime, timedelta
        
        seven_days_ago = datetime.now() - timedelta(days=7)
        
        recent_annual = db.query(AnnualPrediction).filter(
            AnnualPrediction.created_at >= seven_days_ago
        ).count()
        
        recent_quarterly = db.query(QuarterlyPrediction).filter(
            QuarterlyPrediction.created_at >= seven_days_ago
        ).count()

        # === COMPILE RESPONSE ===
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

# ========================================
# DASHBOARD API - POST ENDPOINT WITH PLATFORM STATS

# ========================================

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
        # FIXED: Proper role-based scope determination
        if current_user.role == "super_admin":
            # Super admin sees system-wide data
            scope = "system"
        elif current_user.role in ["tenant_admin", "org_admin", "org_member"] and current_user.organization_id:
            # Organization users see organization data (filtered properly)
            scope = "organization"
        else:
            # Regular users see only personal data
            scope = "personal"

        # Get user's scope data (separate from platform stats)
        if scope == "system":
            user_dashboard = await get_system_dashboard(db, current_user)
        elif scope == "organization":
            user_dashboard = await get_organization_dashboard(db, current_user)
        else:
            user_dashboard = await get_personal_dashboard(db, current_user)

        # Build response with separate objects
        response = {
            "user_dashboard": user_dashboard,
            "scope": scope
        }

        # Add platform statistics as SEPARATE object if requested
        if request.include_platform_stats:
            platform_stats = await get_platform_statistics(db)
            response["platform_statistics"] = platform_stats

        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")

# Helper functions for different dashboard scopes
async def get_system_dashboard(db: Session, current_user: User):
    """Get system-wide dashboard data"""
    total_companies = db.query(Company).count()
    
    # Get annual and quarterly prediction counts
    annual_predictions = db.query(AnnualPrediction).count()
    quarterly_predictions = db.query(QuarterlyPrediction).count()
    total_predictions = annual_predictions + quarterly_predictions
    
    # Calculate average default rate
    annual_avg = db.query(func.avg(AnnualPrediction.probability)).scalar() or 0
    quarterly_avg = db.query(func.avg(QuarterlyPrediction.logistic_probability)).scalar() or 0
    average_default_rate = (annual_avg + quarterly_avg) / 2 if (annual_avg or quarterly_avg) else 0
    
    # High risk companies (>70% probability)
    high_risk_annual = db.query(AnnualPrediction).filter(AnnualPrediction.probability > 0.7).count()
    high_risk_quarterly = db.query(QuarterlyPrediction).filter(QuarterlyPrediction.logistic_probability > 0.7).count()
    high_risk_companies = high_risk_annual + high_risk_quarterly
    
    # Sectors covered
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
    
    # Get organization info
    organization = db.query(Organization).filter(Organization.id == current_user.organization_id).first()
    if not organization:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # FIXED: Get ONLY organization-specific data (no system data mixed in)
    if current_user.role == "tenant_admin":
        # Tenant admin sees ALL organizations' data (cross-org access)
        companies = db.query(Company).all()
        annual_predictions = db.query(AnnualPrediction).all()
        quarterly_predictions = db.query(QuarterlyPrediction).all()
        data_scope_note = " (Cross-organization access - all orgs)"
    else:
        # Regular org users see ONLY their organization's data (NOT system data)
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
    
    # Calculate average default rate
    annual_probs = [p.probability for p in annual_predictions if p.probability is not None]
    quarterly_probs = [p.logistic_probability for p in quarterly_predictions if p.logistic_probability is not None]
    all_probs = annual_probs + quarterly_probs
    average_default_rate = sum(all_probs) / len(all_probs) if all_probs else 0
    
    # High risk companies
    high_risk_annual = len([p for p in annual_predictions if p.probability and p.probability > 0.7])
    high_risk_quarterly = len([p for p in quarterly_predictions if p.logistic_probability and p.logistic_probability > 0.7])
    high_risk_companies = high_risk_annual + high_risk_quarterly
    
    # Sectors covered
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
    # Personal companies
    companies = db.query(Company).filter(Company.created_by == str(current_user.id)).all()
    
    # Personal predictions
    annual_predictions = db.query(AnnualPrediction).filter(AnnualPrediction.created_by == str(current_user.id)).all()
    quarterly_predictions = db.query(QuarterlyPrediction).filter(QuarterlyPrediction.created_by == str(current_user.id)).all()
    
    total_companies = len(companies)
    annual_predictions_count = len(annual_predictions)
    quarterly_predictions_count = len(quarterly_predictions)
    total_predictions = annual_predictions_count + quarterly_predictions_count
    
    # Calculate average default rate
    annual_probs = [p.probability for p in annual_predictions if p.probability is not None]
    quarterly_probs = [p.logistic_probability for p in quarterly_predictions if p.logistic_probability is not None]
    all_probs = annual_probs + quarterly_probs
    average_default_rate = sum(all_probs) / len(all_probs) if all_probs else 0
    
    # High risk companies
    high_risk_annual = len([p for p in annual_predictions if p.probability and p.probability > 0.7])
    high_risk_quarterly = len([p for p in quarterly_predictions if p.logistic_probability and p.logistic_probability > 0.7])
    high_risk_companies = high_risk_annual + high_risk_quarterly
    
    # Sectors covered
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
    
    # Calculate platform average default rate
    annual_avg = db.query(func.avg(AnnualPrediction.probability)).scalar() or 0
    quarterly_avg = db.query(func.avg(QuarterlyPrediction.logistic_probability)).scalar() or 0
    platform_avg_default = (annual_avg + quarterly_avg) / 2 if (annual_avg or quarterly_avg) else 0
    
    # High risk companies platform-wide
    high_risk_annual = db.query(AnnualPrediction).filter(AnnualPrediction.probability > 0.7).count()
    high_risk_quarterly = db.query(QuarterlyPrediction).filter(QuarterlyPrediction.logistic_probability > 0.7).count()
    platform_high_risk = high_risk_annual + high_risk_quarterly
    
    # Platform sectors
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

# DEBUG ENDPOINT - Remove this after fixing the issue
@router.get("/debug/prediction/{prediction_id}")
async def debug_prediction_ownership(
    prediction_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
    """Debug endpoint to check prediction ownership details"""
    try:
        # Find the prediction
        prediction = db.query(AnnualPrediction).filter(AnnualPrediction.id == prediction_id).first()
        
        if not prediction:
            # Try quarterly predictions
            prediction = db.query(QuarterlyPrediction).filter(QuarterlyPrediction.id == prediction_id).first()
            prediction_type = "quarterly"
        else:
            prediction_type = "annual"
        
        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")
        
        # Get detailed comparison info
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

# ========================================
# REDIS HEALTH CHECK ENDPOINT
# ========================================

@router.get("/health/redis", 
           summary="Redis Connection Health Check",
           description="Check if Redis connection is working for Celery tasks")
async def redis_health_check():
    """Check Redis connection health"""
    try:
        # Test connection to Redis
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
