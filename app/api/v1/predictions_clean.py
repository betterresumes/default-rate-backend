from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import Dict, List, Optional
from datetime import datetime
import uuid
import math

# Core imports
from ...core.database import get_db, User, Company, AnnualPrediction, QuarterlyPrediction
from ...schemas.schemas import (
    AnnualPredictionRequest, QuarterlyPredictionRequest
)
from ...services.ml_service import ml_model
from ...services.quarterly_ml_service import quarterly_ml_model
from .auth_multi_tenant import get_current_active_user as current_verified_user

router = APIRouter()

# ========================================
# ACCESS CONTROL HELPERS
# ========================================

def get_organization_context(current_user: User):
    """Get organization context based on user role for access control"""
    if current_user.role == "super_admin":
        return None  # Global access (organization_id = None)
    elif current_user.role in ["tenant_admin", "org_admin", "org_member"]:
        return current_user.organization_id  # Restricted to their organization
    else:
        return current_user.organization_id  # Could be None for basic users

def create_or_get_company(db: Session, company_symbol: str, company_name: str, 
                         market_cap: float, sector: str, organization_id: Optional[str],
                         created_by: str, is_global: bool = False):
    """Create company if it doesn't exist, or get existing one with proper access control"""
    
    # First, try to find existing company by symbol
    existing_company = db.query(Company).filter(Company.symbol == company_symbol.upper()).first()
    
    if existing_company:
        # Company exists - check access permissions
        if is_global and existing_company.is_global:
            return existing_company
        elif organization_id is None:
            # Super admin access - can access any company
            return existing_company
        elif existing_company.organization_id == organization_id:
            return existing_company
        elif existing_company.is_global:
            # Global company - accessible to org users
            return existing_company
        else:
            # Different organization - not accessible
            raise HTTPException(
                status_code=403,
                detail=f"Company {company_symbol} exists but belongs to different organization"
            )
    
    # Create new company
    company = Company(
        symbol=company_symbol.upper(),
        name=company_name,
        market_cap=market_cap * 1_000_000,  # Convert millions to actual value
        sector=sector,
        organization_id=organization_id,
        created_by=created_by,
        is_global=is_global
    )
    
    db.add(company)
    db.commit()
    db.refresh(company)
    return company

def check_user_permissions(user: User, required_role: str = "org_member"):
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

# ========================================
# ANNUAL PREDICTION ENDPOINTS
# ========================================

@router.post("/annual", response_model=Dict)
async def create_annual_prediction(
    request: AnnualPredictionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
    """Create annual prediction with comprehensive data including company creation"""
    try:
        # Check permissions
        if not check_user_permissions(current_user, "org_member"):
            raise HTTPException(
                status_code=403,
                detail="You need to be an organization member or higher to create predictions"
            )

        # Get organization context based on user role
        organization_id = get_organization_context(current_user)
        is_global = current_user.role == "super_admin"
        
        # Create or get company with proper access control
        company = create_or_get_company(
            db=db,
            company_symbol=request.company_symbol,
            company_name=request.company_name,
            market_cap=request.market_cap,
            sector=request.sector,
            organization_id=organization_id,
            created_by=str(current_user.id),
            is_global=is_global
        )
        
        # Check if prediction already exists for this company/year
        existing_prediction = db.query(AnnualPrediction).filter(
            AnnualPrediction.company_id == company.id,
            AnnualPrediction.reporting_year == request.reporting_year
        ).first()
        
        if existing_prediction:
            raise HTTPException(
                status_code=400,
                detail=f"Annual prediction for {request.company_symbol} in {request.reporting_year} already exists"
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
            reporting_year=request.reporting_year,
            reporting_quarter=None,  # Annual prediction
            
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
            created_by=current_user.id
        )
        
        db.add(prediction)
        db.commit()
        db.refresh(prediction)
        
        return {
            "success": True,
            "message": f"Annual prediction created for {request.company_symbol}",
            "prediction": {
                "id": str(prediction.id),
                "company_symbol": request.company_symbol,
                "company_name": request.company_name,
                "reporting_year": request.reporting_year,
                "probability": float(ml_result['probability']),
                "risk_level": ml_result['risk_level'],
                "confidence": float(ml_result['confidence']),
                "organization_access": "global" if is_global else "organization",
                "created_by": current_user.email,
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
    """Create quarterly prediction with comprehensive data including company creation"""
    try:
        # Check permissions
        if not check_user_permissions(current_user, "org_member"):
            raise HTTPException(
                status_code=403,
                detail="You need to be an organization member or higher to create predictions"
            )

        # Get organization context based on user role
        organization_id = get_organization_context(current_user)
        is_global = current_user.role == "super_admin"
        
        # Create or get company with proper access control
        company = create_or_get_company(
            db=db,
            company_symbol=request.company_symbol,
            company_name=request.company_name,
            market_cap=request.market_cap,
            sector=request.sector,
            organization_id=organization_id,
            created_by=str(current_user.id),
            is_global=is_global
        )
        
        # Check if prediction already exists for this company/year/quarter
        existing_prediction = db.query(QuarterlyPrediction).filter(
            QuarterlyPrediction.company_id == company.id,
            QuarterlyPrediction.reporting_year == request.reporting_year,
            QuarterlyPrediction.reporting_quarter == request.reporting_quarter
        ).first()
        
        if existing_prediction:
            raise HTTPException(
                status_code=400,
                detail=f"Quarterly prediction for {request.company_symbol} in {request.reporting_year} {request.reporting_quarter} already exists"
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
        
        return {
            "success": True,
            "message": f"Quarterly prediction created for {request.company_symbol}",
            "prediction": {
                "id": str(prediction.id),
                "company_symbol": request.company_symbol,
                "company_name": request.company_name,
                "reporting_year": request.reporting_year,
                "reporting_quarter": request.reporting_quarter,
                "logistic_probability": float(ml_result.get('logistic_probability', 0)),
                "gbm_probability": float(ml_result.get('gbm_probability', 0)),
                "ensemble_probability": float(ml_result.get('ensemble_probability', 0)),
                "risk_level": ml_result['risk_level'],
                "confidence": float(ml_result['confidence']),
                "organization_access": "global" if is_global else "organization",
                "created_by": current_user.email,
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
    """Get paginated annual predictions with filtering"""
    try:
        # Check permissions
        if not check_user_permissions(current_user, "org_member"):
            raise HTTPException(
                status_code=403,
                detail="You need to be an organization member or higher to view predictions"
            )

        # Get organization context for access control
        organization_id = get_organization_context(current_user)
        
        # Build query with access control
        query = db.query(AnnualPrediction).join(Company)
        
        # Apply organization filter
        if organization_id is not None:
            # Organization users see org predictions + global predictions
            query = query.filter(
                or_(
                    AnnualPrediction.organization_id == organization_id,
                    AnnualPrediction.organization_id.is_(None)  # Global predictions
                )
            )
        # Super admin sees all predictions (no filter needed)
        
        # Apply additional filters
        if company_symbol:
            query = query.filter(Company.symbol.ilike(f"%{company_symbol}%"))
        if reporting_year:
            query = query.filter(AnnualPrediction.reporting_year == reporting_year)
        
        # Pagination
        total = query.count()
        skip = (page - 1) * size
        predictions = query.offset(skip).limit(size).all()
        
        # Format response
        prediction_data = []
        for pred in predictions:
            prediction_data.append({
                "id": str(pred.id),
                "company_symbol": pred.company.symbol,
                "company_name": pred.company.name,
                "reporting_year": pred.reporting_year,
                "probability": safe_float(pred.probability),
                "risk_level": pred.risk_level,
                "confidence": safe_float(pred.confidence),
                "organization_access": "global" if pred.organization_id is None else "organization",
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
    """Get paginated quarterly predictions with filtering"""
    try:
        # Check permissions
        if not check_user_permissions(current_user, "org_member"):
            raise HTTPException(
                status_code=403,
                detail="You need to be an organization member or higher to view predictions"
            )

        # Get organization context for access control
        organization_id = get_organization_context(current_user)
        
        # Build query with access control
        query = db.query(QuarterlyPrediction).join(Company)
        
        # Apply organization filter
        if organization_id is not None:
            query = query.filter(
                or_(
                    QuarterlyPrediction.organization_id == organization_id,
                    QuarterlyPrediction.organization_id.is_(None)
                )
            )
        
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
        predictions = query.offset(skip).limit(size).all()
        
        # Format response
        prediction_data = []
        for pred in predictions:
            prediction_data.append({
                "id": str(pred.id),
                "company_symbol": pred.company.symbol,
                "company_name": pred.company.name,
                "reporting_year": pred.reporting_year,
                "reporting_quarter": pred.reporting_quarter,
                "logistic_probability": safe_float(pred.logistic_probability),
                "gbm_probability": safe_float(pred.gbm_probability),
                "ensemble_probability": safe_float(pred.ensemble_probability),
                "risk_level": pred.risk_level,
                "confidence": safe_float(pred.confidence),
                "organization_access": "global" if pred.organization_id is None else "organization",
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
        if not check_user_permissions(current_user, "org_admin"):
            raise HTTPException(
                status_code=403,
                detail="You need to be an organization admin or higher for bulk uploads"
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
        organization_id = get_organization_context(current_user)
        is_global = current_user.role == "super_admin"
        
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
                    organization_id=organization_id,
                    created_by=str(current_user.id),
                    is_global=is_global
                )
                
                if prediction_type == "annual":
                    # Check if annual prediction already exists
                    existing = db.query(AnnualPrediction).filter(
                        AnnualPrediction.company_id == company.id,
                        AnnualPrediction.reporting_year == row['reporting_year']
                    ).first()
                    
                    if existing:
                        results["errors"].append(f"Row {index + 1}: Annual prediction already exists for {row['company_symbol']} {row['reporting_year']}")
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
                        organization_id=organization_id,
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
                    # Check if quarterly prediction already exists
                    existing = db.query(QuarterlyPrediction).filter(
                        QuarterlyPrediction.company_id == company.id,
                        QuarterlyPrediction.reporting_year == row['reporting_year'],
                        QuarterlyPrediction.reporting_quarter == row['reporting_quarter']
                    ).first()
                    
                    if existing:
                        results["errors"].append(f"Row {index + 1}: Quarterly prediction already exists for {row['company_symbol']} {row['reporting_year']} {row['reporting_quarter']}")
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
                        organization_id=organization_id,
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
