from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import Dict, List, Optional
from datetime import datetime
import uuid
import pandas as pd
import io
import math
import uuid
import math
import pandas as pd
import io

# Core imports
from ...core.database import get_db, User, Company, AnnualPrediction, QuarterlyPrediction, Organization, BulkUploadJob
from ...schemas.schemas import (
    AnnualPredictionRequest, QuarterlyPredictionRequest
)
from ...services.ml_service import ml_model
from ...services.quarterly_ml_service import quarterly_ml_model
from .auth_multi_tenant import get_current_active_user as current_verified_user

router = APIRouter()

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

def get_data_access_filter(user: User, prediction_model):
    """Get simple 3-level access filter for predictions"""
    conditions = []
    
    if user.role == "super_admin":
        # Super admin sees everything
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
    
    # System data: everyone can see it
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
    """Get paginated annual predictions with simplified 3-level access control"""
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
        
        # Apply simplified 3-level access control
        access_filter = get_data_access_filter(current_user, AnnualPrediction)
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
    """Get paginated quarterly predictions with simplified 3-level access control"""
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
        
        # Apply simplified 3-level access control
        access_filter = get_data_access_filter(current_user, QuarterlyPrediction)
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
    """Update an existing annual prediction"""
    try:
        # Check permissions
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to update predictions"
            )

        # Get organization context
        organization_id = get_organization_context(current_user)
        
        # Find existing prediction
        query = db.query(AnnualPrediction).filter(AnnualPrediction.id == prediction_id)
        
        # Apply access control
        if organization_id is not None:
            query = query.filter(
                or_(
                    AnnualPrediction.organization_id == organization_id,
                    AnnualPrediction.organization_id.is_(None)  # Can update global if org allows
                )
            )
        
        prediction = query.first()
        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")
        
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
    """Delete an annual prediction"""
    try:
        # Check permissions
        if not check_user_permissions(current_user, "org_admin"):
            raise HTTPException(
                status_code=403,
                detail="You need to be an organization admin or higher to delete predictions"
            )

        # Get organization context
        organization_id = get_organization_context(current_user)
        
        # Find existing prediction
        query = db.query(AnnualPrediction).filter(AnnualPrediction.id == prediction_id)
        
        # Apply access control
        if organization_id is not None:
            query = query.filter(AnnualPrediction.organization_id == organization_id)
        
        prediction = query.first()
        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")
        
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
    """Update an existing quarterly prediction"""
    try:
        # Check permissions
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to update predictions"
            )

        # Get organization context
        organization_id = get_organization_context(current_user)
        
        # Find existing prediction
        query = db.query(QuarterlyPrediction).filter(QuarterlyPrediction.id == prediction_id)
        
        # Apply access control
        if organization_id is not None:
            query = query.filter(
                or_(
                    QuarterlyPrediction.organization_id == organization_id,
                    QuarterlyPrediction.organization_id.is_(None)
                )
            )
        
        prediction = query.first()
        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")
        
        # Update company information
        company = prediction.company
        company.name = request.company_name
        company.market_cap = request.market_cap  # Market cap should be stored as-is (already in millions)
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
    """Delete a quarterly prediction"""
    try:
        # Check permissions
        if not check_user_permissions(current_user, "org_admin"):
            raise HTTPException(
                status_code=403,
                detail="You need to be an organization admin or higher to delete predictions"
            )

        # Get organization context
        organization_id = get_organization_context(current_user)
        
        # Find existing prediction
        query = db.query(QuarterlyPrediction).filter(QuarterlyPrediction.id == prediction_id)
        
        # Apply access control
        if organization_id is not None:
            query = query.filter(QuarterlyPrediction.organization_id == organization_id)
        
        prediction = query.first()
        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")
        
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
