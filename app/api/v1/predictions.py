from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import Dict, List, Optional
from datetime import datetime
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

def get_prediction_organization_filter(user: User, db: Session):
    """Get filter conditions for predictions based on user's organization access"""
    if user.role == "super_admin":
        # Super admins see everything
        return None
    
    if user.role == "tenant_admin" and user.tenant_id:
        # Tenant admins should only see predictions from orgs in their tenant
        tenant_org_ids = db.query(Organization.id).filter(Organization.tenant_id == user.tenant_id).all()
        tenant_org_ids = [str(org.id) for org in tenant_org_ids]
        if tenant_org_ids:
            # Show predictions from tenant organizations + global predictions
            return or_(
                AnnualPrediction.organization_id.in_(tenant_org_ids),
                AnnualPrediction.organization_id.is_(None)  # Global predictions
            )
        else:
            # No orgs in tenant, only global
            return AnnualPrediction.organization_id.is_(None)
    
    if user.organization_id is None:
        # Users without organization should ONLY see their own predictions (SECURITY FIX)
        return AnnualPrediction.created_by == user.id
    
    # Regular users see:
    # 1. Predictions from their organization  
    # 2. Global predictions ONLY if organization allows global data access
    # 3. Their own predictions regardless of organization setting
    user_org = db.query(Organization).filter(Organization.id == user.organization_id).first()
    if user_org and user_org.allow_global_data_access:
        # Organization allows global access - show org + global + own predictions
        return or_(
            AnnualPrediction.organization_id == user.organization_id,
            AnnualPrediction.organization_id.is_(None),  # Global predictions
            AnnualPrediction.created_by == user.id  # Own predictions
        )
    else:
        # Organization doesn't allow global access - only org + own predictions
        return or_(
            AnnualPrediction.organization_id == user.organization_id,
            AnnualPrediction.created_by == user.id  # Own predictions
        )

def get_quarterly_prediction_organization_filter(user: User, db: Session):
    """Get filter conditions for quarterly predictions based on user's organization access"""
    if user.role == "super_admin":
        # Super admins see everything
        return None
    
    if user.role == "tenant_admin" and user.tenant_id:
        # Tenant admins should only see predictions from orgs in their tenant
        tenant_org_ids = db.query(Organization.id).filter(Organization.tenant_id == user.tenant_id).all()
        tenant_org_ids = [str(org.id) for org in tenant_org_ids]
        if tenant_org_ids:
            # Show predictions from tenant organizations + global predictions
            return or_(
                QuarterlyPrediction.organization_id.in_(tenant_org_ids),
                QuarterlyPrediction.organization_id.is_(None)  # Global predictions
            )
        else:
            # No orgs in tenant, only global
            return QuarterlyPrediction.organization_id.is_(None)
    
    if user.organization_id is None:
        # Users without organization should ONLY see their own predictions (SECURITY FIX)
        return QuarterlyPrediction.created_by == user.id
    
    # Regular users see:
    # 1. Predictions from their organization  
    # 2. Global predictions ONLY if organization allows global data access
    # 3. Their own predictions regardless of organization setting
    user_org = db.query(Organization).filter(Organization.id == user.organization_id).first()
    if user_org and user_org.allow_global_data_access:
        # Organization allows global access - show org + global + own predictions
        return or_(
            QuarterlyPrediction.organization_id == user.organization_id,
            QuarterlyPrediction.organization_id.is_(None),  # Global predictions
            QuarterlyPrediction.created_by == user.id  # Own predictions
        )
    else:
        # Organization doesn't allow global access - only org + own predictions
        return or_(
            QuarterlyPrediction.organization_id == user.organization_id,
            QuarterlyPrediction.created_by == user.id  # Own predictions
        )

def create_or_get_company(db: Session, company_symbol: str, company_name: str, 
                         market_cap: float, sector: str, organization_id: Optional[str],
                         created_by: str, is_global: bool = False):
    """Create company if it doesn't exist, or get existing one with proper scoped access control"""
    
    # NEW LOGIC: Check for existing company within the same scope
    if is_global or organization_id is None:
        # Super admin creating global company OR user without organization - check for existing global company only
        existing_company = db.query(Company).filter(
            Company.symbol == company_symbol.upper(),
            Company.is_global == True
        ).first()
    else:
        # Organization user - check for existing company within their organization only
        existing_company = db.query(Company).filter(
            Company.symbol == company_symbol.upper(),
            Company.organization_id == organization_id
        ).first()
    
    if existing_company:
        # Company exists within the same scope - return it
        return existing_company
    
    # Create new company
    # SECURITY FIX: Only super_admin can create global companies
    # Regular users without organization should NOT create global companies
    if organization_id is None:
        # Only super admin can create global companies
        from ...core.database import User
        user = db.query(User).filter(User.id == created_by).first()
        if not user or user.role != "super_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admin can create global companies. Users without organization must join an organization first."
            )
        is_global = True
    else:
        is_global = False
    
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
        # Check permissions (allow regular users to create predictions)
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to create predictions"
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
        
        # Check if prediction already exists for this company/year/quarter combination
        existing_query = db.query(AnnualPrediction).filter(
            AnnualPrediction.company_id == company.id,
            AnnualPrediction.reporting_year == request.reporting_year
        )
        
        # If quarter is provided, check for that specific quarter, otherwise check for null quarter
        if request.reporting_quarter:
            existing_query = existing_query.filter(AnnualPrediction.reporting_quarter == request.reporting_quarter)
        else:
            existing_query = existing_query.filter(AnnualPrediction.reporting_quarter.is_(None))
        
        existing_prediction = existing_query.first()
        
        if existing_prediction:
            quarter_text = f" {request.reporting_quarter}" if request.reporting_quarter else ""
            raise HTTPException(
                status_code=400,
                detail=f"Annual prediction for {request.company_symbol} in {request.reporting_year}{quarter_text} already exists"
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
            reporting_quarter=request.reporting_quarter,  # Can be None for annual-only predictions
            
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
                "reporting_quarter": request.reporting_quarter,
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
        # Check permissions (allow regular users to create predictions)
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to create predictions"
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
        # Check permissions (allow regular users to view predictions)
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to view predictions"
            )

        # Get organization context for access control
        organization_id = get_organization_context(current_user)
        
        # Build query with access control using dynamic organization filter
        query = db.query(AnnualPrediction).join(Company)
        
        # Apply organization-based filter with dynamic global access checking
        org_filter = get_prediction_organization_filter(current_user, db)
        if org_filter is not None:
            query = query.filter(org_filter)
        
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
                "reporting_quarter": pred.reporting_quarter,
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
        # Check permissions (allow regular users to view predictions)
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="Authentication required to view predictions"
            )

        # Get organization context for access control
        organization_id = get_organization_context(current_user)
        
        # Build query with access control using dynamic organization filter
        query = db.query(QuarterlyPrediction).join(Company)
        
        # Apply organization-based filter with dynamic global access checking
        org_filter = get_quarterly_prediction_organization_filter(current_user, db)
        if org_filter is not None:
            query = query.filter(org_filter)
        elif organization_id is not None:
            # Organization users see only their organization's predictions
            query = query.filter(QuarterlyPrediction.organization_id == organization_id)
        else:
            # Users without organization see only their own predictions
            query = query.filter(QuarterlyPrediction.created_by == current_user.id)
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
        if not check_user_permissions(current_user, "org_member"):
            raise HTTPException(
                status_code=403,
                detail="You need to be an organization member or higher to create predictions"
            )

        # Validate file type
        if not file.filename.endswith(('.csv', '.xlsx')):
            raise HTTPException(
                status_code=400,
                detail="Only CSV and Excel files are supported"
            )

        # Get organization context
        organization_id = get_organization_context(current_user)
        
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
        from app.services.bulk_upload_service import bulk_upload_service
        
        job_id = await bulk_upload_service.create_bulk_upload_job(
            user_id=str(current_user.id),
            organization_id=organization_id,
            job_type='annual',
            filename=file.filename,
            file_size=file_size,
            total_rows=total_rows
        )
        
        # Start background processing
        background_tasks.add_task(
            bulk_upload_service.process_annual_bulk_upload,
            job_id=job_id,
            data=data,
            user_id=str(current_user.id),
            organization_id=organization_id
        )
        
        return {
            "success": True,
            "message": "Bulk upload job started successfully",
            "job_id": job_id,
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
        if not check_user_permissions(current_user, "org_member"):
            raise HTTPException(
                status_code=403,
                detail="You need to be an organization member or higher to create predictions"
            )

        # Validate file type
        if not file.filename.endswith(('.csv', '.xlsx')):
            raise HTTPException(
                status_code=400,
                detail="Only CSV and Excel files are supported"
            )

        # Get organization context
        organization_id = get_organization_context(current_user)
        
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
        from app.services.bulk_upload_service import bulk_upload_service
        
        job_id = await bulk_upload_service.create_bulk_upload_job(
            user_id=str(current_user.id),
            organization_id=organization_id,
            job_type='quarterly',
            filename=file.filename,
            file_size=file_size,
            total_rows=total_rows
        )
        
        # Start background processing
        background_tasks.add_task(
            bulk_upload_service.process_quarterly_bulk_upload,
            job_id=job_id,
            data=data,
            user_id=str(current_user.id),
            organization_id=organization_id
        )
        
        return {
            "success": True,
            "message": "Bulk upload job started successfully",
            "job_id": job_id,
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
        if not check_user_permissions(current_user, "org_member"):
            raise HTTPException(
                status_code=403,
                detail="You need to be an organization member or higher to view job status"
            )

        from app.services.bulk_upload_service import bulk_upload_service
        
        job_status = await bulk_upload_service.get_job_status(job_id)
        
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
        if not check_user_permissions(current_user, "org_member"):
            raise HTTPException(
                status_code=403,
                detail="You need to be an organization member or higher to view jobs"
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
            job_data = {
                'id': str(job.id),
                'status': job.status,
                'job_type': job.job_type,
                'original_filename': job.original_filename,
                'total_rows': job.total_rows,
                'processed_rows': job.processed_rows,
                'successful_rows': job.successful_rows,
                'failed_rows': job.failed_rows,
                'created_at': job.created_at.isoformat() if job.created_at else None,
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'progress_percentage': round((job.processed_rows / job.total_rows) * 100, 2) if job.total_rows > 0 else 0
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
        if not check_user_permissions(current_user, "org_member"):
            raise HTTPException(
                status_code=403,
                detail="You need to be an organization member or higher to update predictions"
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
        company.market_cap = request.market_cap * 1_000_000
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
        
        return {
            "success": True,
            "message": f"Annual prediction updated for {request.company_symbol}",
            "prediction": {
                "id": str(prediction.id),
                "company_symbol": request.company_symbol,
                "company_name": request.company_name,
                "reporting_year": request.reporting_year,
                "reporting_quarter": request.reporting_quarter,
                "probability": float(ml_result['probability']),
                "risk_level": ml_result['risk_level'],
                "confidence": float(ml_result['confidence']),
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
        if not check_user_permissions(current_user, "org_member"):
            raise HTTPException(
                status_code=403,
                detail="You need to be an organization member or higher to update predictions"
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
        company.market_cap = request.market_cap * 1_000_000
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
        
        return {
            "success": True,
            "message": f"Quarterly prediction updated for {request.company_symbol}",
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
