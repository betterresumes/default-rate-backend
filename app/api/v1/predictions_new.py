from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from ...core.database import get_db, User, Company, AnnualPrediction, QuarterlyPrediction
from ...schemas.schemas import (
    CompanyCreate, CompanyResponse, 
    PredictionResponse, BulkPredictionResponse
)
from ...services.services import CompanyService
from ...services.ml_service import ml_model
from ...services.quarterly_ml_service import quarterly_ml_model
from .auth_multi_tenant import get_current_active_user as current_verified_user
from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import uuid
import pandas as pd
import io
import json
import time
import math

router = APIRouter()

# ========================================
# PREDICTION REQUEST SCHEMAS
# ========================================

class UnifiedPredictionRequest(BaseModel):
    company_id: str = Field(..., description="Company UUID")
    prediction_type: str = Field(..., regex="^(annual|quarterly)$", description="Type of prediction")
    year: int = Field(..., ge=2020, le=2030, description="Reporting year")
    quarter: Optional[str] = Field(None, regex="^Q[1-4]$", description="Quarter (required for quarterly)")
    financial_data: Dict = Field(..., description="Financial metrics for prediction")

class AnnualPredictionRequest(BaseModel):
    company_id: str = Field(..., description="Company UUID")
    year: int = Field(..., ge=2020, le=2030)
    total_assets: float = Field(..., gt=0)
    total_liabilities: float = Field(..., ge=0)
    revenue: float = Field(..., gt=0)
    net_income: float = Field(...)
    cash_flow: float = Field(...)
    debt_to_equity: float = Field(..., ge=0)
    current_ratio: float = Field(..., gt=0)
    quick_ratio: float = Field(..., ge=0)
    return_on_assets: float = Field(...)
    return_on_equity: float = Field(...)
    working_capital: Optional[float] = None
    retained_earnings: Optional[float] = None
    ebit: Optional[float] = None
    market_value_equity: Optional[float] = None
    sales: Optional[float] = None

class QuarterlyPredictionRequest(BaseModel):
    company_id: str = Field(..., description="Company UUID")
    year: int = Field(..., ge=2020, le=2030)
    quarter: str = Field(..., regex="^Q[1-4]$")
    total_assets: float = Field(..., gt=0)
    total_liabilities: float = Field(..., ge=0)
    revenue: float = Field(..., gt=0)
    net_income: float = Field(...)
    cash_flow: float = Field(...)
    debt_to_equity: float = Field(..., ge=0)
    current_ratio: float = Field(..., gt=0)
    quick_ratio: float = Field(..., ge=0)
    return_on_assets: float = Field(...)
    return_on_equity: float = Field(...)
    working_capital: Optional[float] = None
    retained_earnings: Optional[float] = None
    ebit: Optional[float] = None
    market_value_equity: Optional[float] = None
    sales: Optional[float] = None

class BulkPredictionRequest(BaseModel):
    predictions: List[UnifiedPredictionRequest] = Field(..., min_items=1, max_items=100)

class PredictionUpdateRequest(BaseModel):
    financial_data: Dict = Field(..., description="Updated financial data")

# ========================================
# RESPONSE SCHEMAS
# ========================================

class PredictionDetailResponse(BaseModel):
    id: str
    prediction_type: str
    company_id: str
    company_name: str
    company_symbol: str
    year: int
    quarter: Optional[str] = None
    probability: float
    risk_level: str
    confidence: float
    organization_id: Optional[str] = None
    created_by: str
    created_at: str
    updated_at: Optional[str] = None

# ========================================
# ROLE-BASED PERMISSION HELPERS
# ========================================

def check_user_permissions(user: User, required_role: str = "org_member"):
    """Check if user has required permissions based on 5-role hierarchy:
    1. super_admin: Full access
    2. tenant_admin: Tenant scope access  
    3. org_admin: Organization admin access
    4. org_member: Organization member access
    5. user: No organization access
    """
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

def get_organization_context(user: User):
    """Get organization context for the current user"""
    if user.role == "super_admin":
        return None  # No restriction for super admin
    return user.organization_id

def validate_company_access(user: User, company: Company, db: Session):
    """Validate if user can access the company"""
    if user.role == "super_admin":
        return True
    
    if user.role == "tenant_admin":
        if company.organization_id:
            from ...core.database import Organization
            org = db.query(Organization).filter(Organization.id == company.organization_id).first()
            return org and org.tenant_id == user.tenant_id
        return True  # Global companies accessible to tenant admins
    
    # org_admin and org_member need proper organization checks
    if not user.organization_id:
        return False  # Users without organization can't access companies
    
    # Check if company belongs to user's organization
    if company.organization_id == user.organization_id:
        return True
    
    # Check if company is global and user's organization allows global access
    if company.organization_id is None:  # Global company
        from ...core.database import Organization
        user_org = db.query(Organization).filter(Organization.id == user.organization_id).first()
        return user_org and user_org.allow_global_data_access
    
    return False

def serialize_datetime(dt):
    """Helper function to serialize datetime objects"""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    return dt

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
# CORE PREDICTION ENDPOINTS
# ========================================

@router.post("/unified-predict", response_model=dict)
async def unified_predict(
    request: UnifiedPredictionRequest,
    current_user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """Unified endpoint for both annual and quarterly predictions with ML integration"""
    try:
        # Check permissions
        if not check_user_permissions(current_user, "org_member"):
            raise HTTPException(
                status_code=403,
                detail="You need to be an organization member or higher to create predictions"
            )
        
        # Validate company exists and user has access
        company = db.query(Company).filter(Company.id == request.company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        if not validate_company_access(current_user, company, db):
            raise HTTPException(status_code=403, detail="You don't have access to this company")
        
        # Route to specific prediction type
        if request.prediction_type == "annual":
            return await create_annual_prediction_internal(
                company_id=request.company_id,
                year=request.year,
                financial_data=request.financial_data,
                current_user=current_user,
                db=db
            )
        elif request.prediction_type == "quarterly":
            if not request.quarter:
                raise HTTPException(status_code=400, detail="Quarter is required for quarterly predictions")
            return await create_quarterly_prediction_internal(
                company_id=request.company_id,
                year=request.year,
                quarter=request.quarter,
                financial_data=request.financial_data,
                current_user=current_user,
                db=db
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid prediction_type. Must be 'annual' or 'quarterly'")
            
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.post("/annual", response_model=dict)
async def create_annual_prediction(
    request: AnnualPredictionRequest,
    current_user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """Create annual default rate prediction"""
    try:
        # Check permissions
        if not check_user_permissions(current_user, "org_member"):
            raise HTTPException(
                status_code=403,
                detail="You need to be an organization member or higher to create predictions"
            )
        
        # Validate company
        company = db.query(Company).filter(Company.id == request.company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        if not validate_company_access(current_user, company, db):
            raise HTTPException(status_code=403, detail="You don't have access to this company")
        
        # Build financial data
        financial_data = {
            "total_assets": request.total_assets,
            "total_liabilities": request.total_liabilities,
            "revenue": request.revenue,
            "net_income": request.net_income,
            "cash_flow": request.cash_flow,
            "debt_to_equity": request.debt_to_equity,
            "current_ratio": request.current_ratio,
            "quick_ratio": request.quick_ratio,
            "return_on_assets": request.return_on_assets,
            "return_on_equity": request.return_on_equity
        }
        
        # Add optional fields if provided
        if request.working_capital is not None:
            financial_data["working_capital"] = request.working_capital
        if request.retained_earnings is not None:
            financial_data["retained_earnings"] = request.retained_earnings
        if request.ebit is not None:
            financial_data["ebit"] = request.ebit
        if request.market_value_equity is not None:
            financial_data["market_value_equity"] = request.market_value_equity
        if request.sales is not None:
            financial_data["sales"] = request.sales
        
        return await create_annual_prediction_internal(
            company_id=request.company_id,
            year=request.year,
            financial_data=financial_data,
            current_user=current_user,
            db=db
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Annual prediction failed: {str(e)}")


@router.post("/quarterly", response_model=dict)
async def create_quarterly_prediction(
    request: QuarterlyPredictionRequest,
    current_user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """Create quarterly default rate prediction"""
    try:
        # Check permissions
        if not check_user_permissions(current_user, "org_member"):
            raise HTTPException(
                status_code=403,
                detail="You need to be an organization member or higher to create predictions"
            )
        
        # Validate company
        company = db.query(Company).filter(Company.id == request.company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        if not validate_company_access(current_user, company, db):
            raise HTTPException(status_code=403, detail="You don't have access to this company")
        
        # Validate quarter
        if request.quarter not in ["Q1", "Q2", "Q3", "Q4"]:
            raise HTTPException(status_code=400, detail="Invalid quarter. Must be Q1, Q2, Q3, or Q4")
        
        # Build financial data
        financial_data = {
            "total_assets": request.total_assets,
            "total_liabilities": request.total_liabilities,
            "revenue": request.revenue,
            "net_income": request.net_income,
            "cash_flow": request.cash_flow,
            "debt_to_equity": request.debt_to_equity,
            "current_ratio": request.current_ratio,
            "quick_ratio": request.quick_ratio,
            "return_on_assets": request.return_on_assets,
            "return_on_equity": request.return_on_equity
        }
        
        # Add optional fields if provided
        if request.working_capital is not None:
            financial_data["working_capital"] = request.working_capital
        if request.retained_earnings is not None:
            financial_data["retained_earnings"] = request.retained_earnings
        if request.ebit is not None:
            financial_data["ebit"] = request.ebit
        if request.market_value_equity is not None:
            financial_data["market_value_equity"] = request.market_value_equity
        if request.sales is not None:
            financial_data["sales"] = request.sales
        
        return await create_quarterly_prediction_internal(
            company_id=request.company_id,
            year=request.year,
            quarter=request.quarter,
            financial_data=financial_data,
            current_user=current_user,
            db=db
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Quarterly prediction failed: {str(e)}")


# ========================================
# INTERNAL ML PREDICTION HELPERS
# ========================================

async def create_annual_prediction_internal(
    company_id: str,
    year: int,
    financial_data: Dict,
    current_user: User,
    db: Session
):
    """Internal function to create annual prediction with ML"""
    try:
        # Get company
        company = db.query(Company).filter(Company.id == company_id).first()
        
        # Check for duplicate prediction
        existing_prediction = db.query(AnnualPrediction).filter(
            and_(
                AnnualPrediction.company_id == company_id,
                AnnualPrediction.year == year,
                AnnualPrediction.organization_id == get_organization_context(current_user),
                AnnualPrediction.created_by == current_user.id
            )
        ).first()
        
        if existing_prediction:
            raise HTTPException(
                status_code=400,
                detail=f"Annual prediction for {company.symbol} in {year} already exists"
            )
        
        # Prepare ML input - convert financial data to ratios expected by ML model
        ml_ratios = prepare_annual_ml_ratios(financial_data)
        
        # Run ML prediction
        prediction_result = ml_model.predict_probability(ml_ratios)
        
        if prediction_result is None:
            raise HTTPException(
                status_code=422,
                detail="ML prediction failed. Please check your financial data."
            )
        
        # Create prediction record
        prediction = AnnualPrediction(
            id=uuid.uuid4(),
            company_id=company_id,
            year=year,
            # Store original financial data
            total_assets=financial_data.get("total_assets"),
            total_liabilities=financial_data.get("total_liabilities"),
            revenue=financial_data.get("revenue"),
            net_income=financial_data.get("net_income"),
            cash_flow=financial_data.get("cash_flow"),
            debt_to_equity=financial_data.get("debt_to_equity"),
            current_ratio=financial_data.get("current_ratio"),
            quick_ratio=financial_data.get("quick_ratio"),
            return_on_assets=financial_data.get("return_on_assets"),
            return_on_equity=financial_data.get("return_on_equity"),
            working_capital=financial_data.get("working_capital"),
            retained_earnings=financial_data.get("retained_earnings"),
            ebit=financial_data.get("ebit"),
            market_value_equity=financial_data.get("market_value_equity"),
            sales=financial_data.get("sales"),
            # Store ML results
            probability=prediction_result["probability"],
            risk_level=prediction_result["risk_level"],
            confidence=prediction_result["confidence"],
            # Track context
            organization_id=get_organization_context(current_user),
            created_by=current_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(prediction)
        db.commit()
        db.refresh(prediction)
        
        return {
            "success": True,
            "message": "Annual prediction created successfully",
            "prediction_id": str(prediction.id),
            "data": {
                "prediction": {
                    "id": str(prediction.id),
                    "type": "annual",
                    "company_id": str(company.id),
                    "company_symbol": company.symbol,
                    "company_name": company.name,
                    "year": prediction.year,
                    "probability": safe_float(prediction.probability),
                    "risk_level": prediction.risk_level,
                    "confidence": safe_float(prediction.confidence),
                    "organization_id": str(prediction.organization_id) if prediction.organization_id else None,
                    "created_by": str(prediction.created_by),
                    "created_at": serialize_datetime(prediction.created_at)
                },
                "financial_data": financial_data,
                "ml_result": prediction_result
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise Exception(f"Annual prediction creation failed: {str(e)}")


async def create_quarterly_prediction_internal(
    company_id: str,
    year: int,
    quarter: str,
    financial_data: Dict,
    current_user: User,
    db: Session
):
    """Internal function to create quarterly prediction with ML"""
    try:
        # Get company
        company = db.query(Company).filter(Company.id == company_id).first()
        
        # Check for duplicate prediction
        existing_prediction = db.query(QuarterlyPrediction).filter(
            and_(
                QuarterlyPrediction.company_id == company_id,
                QuarterlyPrediction.year == year,
                QuarterlyPrediction.quarter == quarter,
                QuarterlyPrediction.organization_id == get_organization_context(current_user),
                QuarterlyPrediction.created_by == current_user.id
            )
        ).first()
        
        if existing_prediction:
            raise HTTPException(
                status_code=400,
                detail=f"Quarterly prediction for {company.symbol} in {quarter} {year} already exists"
            )
        
        # Prepare ML input - convert financial data to ratios expected by ML model
        ml_ratios = prepare_quarterly_ml_ratios(financial_data)
        
        # Run ML prediction
        prediction_result = quarterly_ml_model.predict_probability(ml_ratios)
        
        if prediction_result is None:
            raise HTTPException(
                status_code=422,
                detail="ML prediction failed. Please check your financial data."
            )
        
        # Create prediction record
        prediction = QuarterlyPrediction(
            id=uuid.uuid4(),
            company_id=company_id,
            year=year,
            quarter=quarter,
            # Store original financial data
            total_assets=financial_data.get("total_assets"),
            total_liabilities=financial_data.get("total_liabilities"),
            revenue=financial_data.get("revenue"),
            net_income=financial_data.get("net_income"),
            cash_flow=financial_data.get("cash_flow"),
            debt_to_equity=financial_data.get("debt_to_equity"),
            current_ratio=financial_data.get("current_ratio"),
            quick_ratio=financial_data.get("quick_ratio"),
            return_on_assets=financial_data.get("return_on_assets"),
            return_on_equity=financial_data.get("return_on_equity"),
            working_capital=financial_data.get("working_capital"),
            retained_earnings=financial_data.get("retained_earnings"),
            ebit=financial_data.get("ebit"),
            market_value_equity=financial_data.get("market_value_equity"),
            sales=financial_data.get("sales"),
            # Store ML results
            probability=prediction_result["probability"],
            risk_level=prediction_result["risk_level"],
            confidence=prediction_result["confidence"],
            # Track context
            organization_id=get_organization_context(current_user),
            created_by=current_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(prediction)
        db.commit()
        db.refresh(prediction)
        
        return {
            "success": True,
            "message": "Quarterly prediction created successfully",
            "prediction_id": str(prediction.id),
            "data": {
                "prediction": {
                    "id": str(prediction.id),
                    "type": "quarterly",
                    "company_id": str(company.id),
                    "company_symbol": company.symbol,
                    "company_name": company.name,
                    "year": prediction.year,
                    "quarter": prediction.quarter,
                    "probability": safe_float(prediction.probability),
                    "risk_level": prediction.risk_level,
                    "confidence": safe_float(prediction.confidence),
                    "organization_id": str(prediction.organization_id) if prediction.organization_id else None,
                    "created_by": str(prediction.created_by),
                    "created_at": serialize_datetime(prediction.created_at)
                },
                "financial_data": financial_data,
                "ml_result": prediction_result
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise Exception(f"Quarterly prediction creation failed: {str(e)}")


def prepare_annual_ml_ratios(financial_data: Dict) -> Dict:
    """Convert financial data to ratios expected by annual ML model"""
    try:
        # Calculate ratios from financial data
        total_assets = financial_data.get("total_assets", 0)
        total_liabilities = financial_data.get("total_liabilities", 0)
        revenue = financial_data.get("revenue", 0)
        net_income = financial_data.get("net_income", 0)
        ebit = financial_data.get("ebit", net_income * 1.5 if net_income else 0)  # Estimate if not provided
        
        # Calculate key ratios for ML model (these should match your model's expected inputs)
        ratios = {
            "debt_to_assets": total_liabilities / total_assets if total_assets > 0 else 0,
            "return_on_assets": net_income / total_assets if total_assets > 0 else 0,
            "net_income_margin": net_income / revenue if revenue > 0 else 0,
            "current_ratio": financial_data.get("current_ratio", 1.0),
            "debt_to_equity": financial_data.get("debt_to_equity", 0)
        }
        
        return ratios
    except Exception as e:
        raise ValueError(f"Failed to prepare ML ratios: {str(e)}")


def prepare_quarterly_ml_ratios(financial_data: Dict) -> Dict:
    """Convert financial data to ratios expected by quarterly ML model"""
    try:
        # Similar to annual but may have different ratios for quarterly model
        total_assets = financial_data.get("total_assets", 0)
        total_liabilities = financial_data.get("total_liabilities", 0)
        revenue = financial_data.get("revenue", 0)
        net_income = financial_data.get("net_income", 0)
        
        ratios = {
            "debt_to_assets": total_liabilities / total_assets if total_assets > 0 else 0,
            "return_on_assets": net_income / total_assets if total_assets > 0 else 0,
            "net_income_margin": net_income / revenue if revenue > 0 else 0,
            "current_ratio": financial_data.get("current_ratio", 1.0),
            "debt_to_equity": financial_data.get("debt_to_equity", 0)
        }
        
        return ratios
    except Exception as e:
        raise ValueError(f"Failed to prepare quarterly ML ratios: {str(e)}")


# ========================================
# PREDICTION RETRIEVAL ENDPOINTS
# ========================================

@router.get("/annual", response_model=dict)
async def get_annual_predictions(
    page: int = 1,
    limit: int = 10,
    year: Optional[int] = None,
    company_id: Optional[str] = None,
    current_user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """Get annual predictions with filtering and pagination"""
    try:
        if not check_user_permissions(current_user, "org_member"):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Build query with organization context
        query = db.query(AnnualPrediction).join(Company)
        
        # Apply organization filtering
        org_context = get_organization_context(current_user)
        if org_context:
            query = query.filter(AnnualPrediction.organization_id == org_context)
        elif current_user.role != "super_admin":
            query = query.filter(AnnualPrediction.created_by == current_user.id)
        
        # Apply filters
        if year:
            query = query.filter(AnnualPrediction.year == year)
        if company_id:
            query = query.filter(AnnualPrediction.company_id == company_id)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        predictions = query.order_by(AnnualPrediction.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
        
        # Format response
        results = []
        for pred in predictions:
            results.append({
                "id": str(pred.id),
                "company_id": str(pred.company_id),
                "company_name": pred.company.name,
                "company_symbol": pred.company.symbol,
                "year": pred.year,
                "probability": safe_float(pred.probability),
                "risk_level": pred.risk_level,
                "confidence": safe_float(pred.confidence),
                "created_at": serialize_datetime(pred.created_at)
            })
        
        return {
            "success": True,
            "data": results,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": math.ceil(total / limit)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get annual predictions: {str(e)}")


@router.get("/quarterly", response_model=dict)
async def get_quarterly_predictions(
    page: int = 1,
    limit: int = 10,
    year: Optional[int] = None,
    quarter: Optional[str] = None,
    company_id: Optional[str] = None,
    current_user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """Get quarterly predictions with filtering and pagination"""
    try:
        if not check_user_permissions(current_user, "org_member"):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Build query with organization context
        query = db.query(QuarterlyPrediction).join(Company)
        
        # Apply organization filtering
        org_context = get_organization_context(current_user)
        if org_context:
            query = query.filter(QuarterlyPrediction.organization_id == org_context)
        elif current_user.role != "super_admin":
            query = query.filter(QuarterlyPrediction.created_by == current_user.id)
        
        # Apply filters
        if year:
            query = query.filter(QuarterlyPrediction.year == year)
        if quarter:
            query = query.filter(QuarterlyPrediction.quarter == quarter)
        if company_id:
            query = query.filter(QuarterlyPrediction.company_id == company_id)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        predictions = query.order_by(QuarterlyPrediction.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
        
        # Format response
        results = []
        for pred in predictions:
            results.append({
                "id": str(pred.id),
                "company_id": str(pred.company_id),
                "company_name": pred.company.name,
                "company_symbol": pred.company.symbol,
                "year": pred.year,
                "quarter": pred.quarter,
                "probability": safe_float(pred.probability),
                "risk_level": pred.risk_level,
                "confidence": safe_float(pred.confidence),
                "created_at": serialize_datetime(pred.created_at)
            })
        
        return {
            "success": True,
            "data": results,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": math.ceil(total / limit)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get quarterly predictions: {str(e)}")


@router.get("/companies/{company_id}", response_model=dict)
async def get_company_predictions(
    company_id: str,
    page: int = 1,
    limit: int = 10,
    current_user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """Get all predictions for a specific company"""
    try:
        if not check_user_permissions(current_user, "org_member"):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Validate company access
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        if not validate_company_access(current_user, company, db):
            raise HTTPException(status_code=403, detail="You don't have access to this company")
        
        # Get organization context for filtering predictions
        org_context = get_organization_context(current_user)
        
        # Get annual predictions
        annual_query = db.query(AnnualPrediction).filter(AnnualPrediction.company_id == company_id)
        if org_context:
            annual_query = annual_query.filter(AnnualPrediction.organization_id == org_context)
        elif current_user.role != "super_admin":
            annual_query = annual_query.filter(AnnualPrediction.created_by == current_user.id)
        
        annual_predictions = annual_query.order_by(AnnualPrediction.created_at.desc()).all()
        
        # Get quarterly predictions
        quarterly_query = db.query(QuarterlyPrediction).filter(QuarterlyPrediction.company_id == company_id)
        if org_context:
            quarterly_query = quarterly_query.filter(QuarterlyPrediction.organization_id == org_context)
        elif current_user.role != "super_admin":
            quarterly_query = quarterly_query.filter(QuarterlyPrediction.created_by == current_user.id)
        
        quarterly_predictions = quarterly_query.order_by(QuarterlyPrediction.created_at.desc()).all()
        
        # Format response
        annual_data = []
        for pred in annual_predictions:
            annual_data.append({
                "id": str(pred.id),
                "year": pred.year,
                "probability": safe_float(pred.probability),
                "risk_level": pred.risk_level,
                "confidence": safe_float(pred.confidence),
                "created_at": serialize_datetime(pred.created_at)
            })
        
        quarterly_data = []
        for pred in quarterly_predictions:
            quarterly_data.append({
                "id": str(pred.id),
                "year": pred.year,
                "quarter": pred.quarter,
                "probability": safe_float(pred.probability),
                "risk_level": pred.risk_level,
                "confidence": safe_float(pred.confidence),
                "created_at": serialize_datetime(pred.created_at)
            })
        
        return {
            "success": True,
            "company": {
                "id": str(company.id),
                "name": company.name,
                "symbol": company.symbol,
                "sector": company.sector
            },
            "predictions": {
                "annual": annual_data,
                "quarterly": quarterly_data
            },
            "summary": {
                "total_annual": len(annual_data),
                "total_quarterly": len(quarterly_data)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get company predictions: {str(e)}")


@router.get("/summary", response_model=dict)
async def get_prediction_summary(
    period: str = "month",
    current_user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """Get prediction analytics summary"""
    try:
        if not check_user_permissions(current_user, "org_member"):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get organization context
        org_context = get_organization_context(current_user)
        
        # Build base queries
        annual_query = db.query(AnnualPrediction)
        quarterly_query = db.query(QuarterlyPrediction)
        
        # Apply organization filtering
        if org_context:
            annual_query = annual_query.filter(AnnualPrediction.organization_id == org_context)
            quarterly_query = quarterly_query.filter(QuarterlyPrediction.organization_id == org_context)
        elif current_user.role != "super_admin":
            annual_query = annual_query.filter(AnnualPrediction.created_by == current_user.id)
            quarterly_query = quarterly_query.filter(QuarterlyPrediction.created_by == current_user.id)
        
        # Get counts
        total_annual = annual_query.count()
        total_quarterly = quarterly_query.count()
        
        # Get risk level distribution
        annual_risk_dist = db.query(
            AnnualPrediction.risk_level,
            func.count(AnnualPrediction.id).label('count')
        ).filter(annual_query.whereclause).group_by(AnnualPrediction.risk_level).all()
        
        quarterly_risk_dist = db.query(
            QuarterlyPrediction.risk_level,
            func.count(QuarterlyPrediction.id).label('count')
        ).filter(quarterly_query.whereclause).group_by(QuarterlyPrediction.risk_level).all()
        
        return {
            "success": True,
            "summary": {
                "total_predictions": total_annual + total_quarterly,
                "annual_predictions": total_annual,
                "quarterly_predictions": total_quarterly,
                "risk_distribution": {
                    "annual": {item.risk_level: item.count for item in annual_risk_dist},
                    "quarterly": {item.risk_level: item.count for item in quarterly_risk_dist}
                },
                "period": period,
                "organization_context": str(org_context) if org_context else "personal"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get prediction summary: {str(e)}")


# ========================================
# UPDATE AND DELETE ENDPOINTS
# ========================================

@router.put("/annual/{prediction_id}", response_model=dict)
async def update_annual_prediction(
    prediction_id: str,
    request: PredictionUpdateRequest,
    current_user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """Update an annual prediction with new financial data"""
    try:
        if not check_user_permissions(current_user, "org_member"):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Find the prediction
        prediction = db.query(AnnualPrediction).filter(AnnualPrediction.id == prediction_id).first()
        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")
        
        # Check ownership or admin access
        org_context = get_organization_context(current_user)
        if (current_user.role not in ["super_admin", "tenant_admin"] and 
            prediction.created_by != current_user.id and 
            prediction.organization_id != org_context):
            raise HTTPException(status_code=403, detail="You can only update your own predictions")
        
        # Re-run ML prediction with new data
        ml_ratios = prepare_annual_ml_ratios(request.financial_data)
        prediction_result = ml_model.predict_probability(ml_ratios)
        
        if prediction_result is None:
            raise HTTPException(status_code=422, detail="ML prediction failed")
        
        # Update prediction with new data
        for key, value in request.financial_data.items():
            if hasattr(prediction, key):
                setattr(prediction, key, value)
        
        # Update ML results
        prediction.probability = prediction_result["probability"]
        prediction.risk_level = prediction_result["risk_level"]
        prediction.confidence = prediction_result["confidence"]
        prediction.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(prediction)
        
        return {
            "success": True,
            "message": "Annual prediction updated successfully",
            "data": {
                "id": str(prediction.id),
                "probability": safe_float(prediction.probability),
                "risk_level": prediction.risk_level,
                "confidence": safe_float(prediction.confidence),
                "updated_at": serialize_datetime(prediction.updated_at)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update prediction: {str(e)}")


@router.put("/quarterly/{prediction_id}", response_model=dict)
async def update_quarterly_prediction(
    prediction_id: str,
    request: PredictionUpdateRequest,
    current_user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """Update a quarterly prediction with new financial data"""
    try:
        if not check_user_permissions(current_user, "org_member"):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Find the prediction
        prediction = db.query(QuarterlyPrediction).filter(QuarterlyPrediction.id == prediction_id).first()
        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")
        
        # Check ownership or admin access
        org_context = get_organization_context(current_user)
        if (current_user.role not in ["super_admin", "tenant_admin"] and 
            prediction.created_by != current_user.id and 
            prediction.organization_id != org_context):
            raise HTTPException(status_code=403, detail="You can only update your own predictions")
        
        # Re-run ML prediction with new data
        ml_ratios = prepare_quarterly_ml_ratios(request.financial_data)
        prediction_result = quarterly_ml_model.predict_probability(ml_ratios)
        
        if prediction_result is None:
            raise HTTPException(status_code=422, detail="ML prediction failed")
        
        # Update prediction with new data
        for key, value in request.financial_data.items():
            if hasattr(prediction, key):
                setattr(prediction, key, value)
        
        # Update ML results
        prediction.probability = prediction_result["probability"]
        prediction.risk_level = prediction_result["risk_level"]
        prediction.confidence = prediction_result["confidence"]
        prediction.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(prediction)
        
        return {
            "success": True,
            "message": "Quarterly prediction updated successfully",
            "data": {
                "id": str(prediction.id),
                "probability": safe_float(prediction.probability),
                "risk_level": prediction.risk_level,
                "confidence": safe_float(prediction.confidence),
                "updated_at": serialize_datetime(prediction.updated_at)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update prediction: {str(e)}")


@router.delete("/annual/{prediction_id}", response_model=dict)
async def delete_annual_prediction(
    prediction_id: str,
    current_user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """Delete an annual prediction"""
    try:
        if not check_user_permissions(current_user, "org_admin"):
            raise HTTPException(status_code=403, detail="Only organization admins or higher can delete predictions")
        
        # Find the prediction
        prediction = db.query(AnnualPrediction).filter(AnnualPrediction.id == prediction_id).first()
        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")
        
        # Check ownership or admin access
        org_context = get_organization_context(current_user)
        if (current_user.role not in ["super_admin", "tenant_admin"] and 
            prediction.organization_id != org_context):
            raise HTTPException(status_code=403, detail="You can only delete predictions from your organization")
        
        db.delete(prediction)
        db.commit()
        
        return {
            "success": True,
            "message": "Annual prediction deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete prediction: {str(e)}")


@router.delete("/quarterly/{prediction_id}", response_model=dict)
async def delete_quarterly_prediction(
    prediction_id: str,
    current_user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """Delete a quarterly prediction"""
    try:
        if not check_user_permissions(current_user, "org_admin"):
            raise HTTPException(status_code=403, detail="Only organization admins or higher can delete predictions")
        
        # Find the prediction
        prediction = db.query(QuarterlyPrediction).filter(QuarterlyPrediction.id == prediction_id).first()
        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")
        
        # Check ownership or admin access
        org_context = get_organization_context(current_user)
        if (current_user.role not in ["super_admin", "tenant_admin"] and 
            prediction.organization_id != org_context):
            raise HTTPException(status_code=403, detail="You can only delete predictions from your organization")
        
        db.delete(prediction)
        db.commit()
        
        return {
            "success": True,
            "message": "Quarterly prediction deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete prediction: {str(e)}")


# ========================================
# BULK PROCESSING ENDPOINTS
# ========================================

@router.post("/bulk", response_model=dict)
async def bulk_predictions_sync(
    request: BulkPredictionRequest,
    current_user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """Process multiple predictions synchronously"""
    try:
        if not check_user_permissions(current_user, "org_member"):
            raise HTTPException(status_code=403, detail="Access denied")
        
        results = []
        successful = 0
        failed = 0
        
        for pred_request in request.predictions:
            try:
                if pred_request.prediction_type == "annual":
                    result = await create_annual_prediction_internal(
                        company_id=pred_request.company_id,
                        year=pred_request.year,
                        financial_data=pred_request.financial_data,
                        current_user=current_user,
                        db=db
                    )
                    results.append({
                        "status": "success",
                        "company_id": pred_request.company_id,
                        "prediction_id": result["prediction_id"],
                        "message": "Created successfully"
                    })
                    successful += 1
                    
                elif pred_request.prediction_type == "quarterly":
                    if not pred_request.quarter:
                        raise ValueError("Quarter is required for quarterly predictions")
                    
                    result = await create_quarterly_prediction_internal(
                        company_id=pred_request.company_id,
                        year=pred_request.year,
                        quarter=pred_request.quarter,
                        financial_data=pred_request.financial_data,
                        current_user=current_user,
                        db=db
                    )
                    results.append({
                        "status": "success",
                        "company_id": pred_request.company_id,
                        "prediction_id": result["prediction_id"],
                        "message": "Created successfully"
                    })
                    successful += 1
                    
                else:
                    raise ValueError("Invalid prediction type")
                    
            except Exception as e:
                results.append({
                    "status": "failed",
                    "company_id": pred_request.company_id,
                    "error": str(e)
                })
                failed += 1
        
        return {
            "success": True,
            "message": f"Bulk processing completed. {successful} successful, {failed} failed",
            "summary": {
                "total": len(request.predictions),
                "successful": successful,
                "failed": failed
            },
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Bulk prediction failed: {str(e)}")


@router.post("/bulk-async", response_model=dict)
async def bulk_predictions_async(
    request: BulkPredictionRequest,
    current_user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """Process multiple predictions asynchronously"""
    try:
        if not check_user_permissions(current_user, "org_member"):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # For now, we'll process synchronously but return a job-like response
        # In a real implementation, you'd use Celery or similar for true async processing
        job_id = str(uuid.uuid4())
        
        # Process the bulk request (same logic as sync version)
        results = []
        successful = 0
        failed = 0
        
        for pred_request in request.predictions:
            try:
                if pred_request.prediction_type == "annual":
                    result = await create_annual_prediction_internal(
                        company_id=pred_request.company_id,
                        year=pred_request.year,
                        financial_data=pred_request.financial_data,
                        current_user=current_user,
                        db=db
                    )
                    successful += 1
                elif pred_request.prediction_type == "quarterly":
                    if not pred_request.quarter:
                        raise ValueError("Quarter is required for quarterly predictions")
                    
                    result = await create_quarterly_prediction_internal(
                        company_id=pred_request.company_id,
                        year=pred_request.year,
                        quarter=pred_request.quarter,
                        financial_data=pred_request.financial_data,
                        current_user=current_user,
                        db=db
                    )
                    successful += 1
                else:
                    raise ValueError("Invalid prediction type")
                    
            except Exception as e:
                failed += 1
        
        return {
            "success": True,
            "message": "Bulk predictions processing completed",
            "job_id": job_id,
            "status": "completed",
            "summary": {
                "total": len(request.predictions),
                "successful": successful,
                "failed": failed
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Async bulk prediction failed: {str(e)}")


@router.get("/bulk-status/{job_id}", response_model=dict)
async def get_bulk_job_status(
    job_id: str,
    current_user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """Get status of a bulk prediction job"""
    try:
        if not check_user_permissions(current_user, "org_member"):
            raise HTTPException(status_code=403, detail="Access denied")
        
        # In a real implementation, you'd query a job status table
        # For now, return a mock response
        return {
            "success": True,
            "job_id": job_id,
            "status": "completed",
            "message": "Job completed successfully",
            "progress": {
                "total": 0,
                "completed": 0,
                "failed": 0
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")


# ========================================
# API HEALTH AND INFO ENDPOINTS
# ========================================

@router.get("/", response_model=dict)
async def get_predictions_info():
    """Get predictions API information and available endpoints"""
    return {
        "service": "Financial Default Risk Prediction API",
        "version": "2.0.0",
        "description": "ML-powered prediction system for financial default risk analysis",
        "endpoints": {
            "unified": "/api/v1/predictions/unified-predict",
            "annual": "/api/v1/predictions/annual",
            "quarterly": "/api/v1/predictions/quarterly",
            "bulk_sync": "/api/v1/predictions/bulk",
            "bulk_async": "/api/v1/predictions/bulk-async",
            "company_predictions": "/api/v1/predictions/companies/{company_id}",
            "summary": "/api/v1/predictions/summary",
            "update_annual": "/api/v1/predictions/annual/{prediction_id}",
            "update_quarterly": "/api/v1/predictions/quarterly/{prediction_id}",
            "delete_annual": "/api/v1/predictions/annual/{prediction_id}",
            "delete_quarterly": "/api/v1/predictions/quarterly/{prediction_id}"
        },
        "features": [
            "Annual and quarterly predictions",
            "ML-powered risk assessment", 
            "Organization-based access control",
            "Bulk processing (sync and async)",
            "Prediction CRUD operations",
            "Analytics and reporting"
        ],
        "status": "active"
    }
