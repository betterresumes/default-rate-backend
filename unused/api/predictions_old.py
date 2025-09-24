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
        return True  # Global companies accessible
    
    # org_admin and org_member can access their org companies
    return company.organization_id == user.organization_id or getattr(company, 'is_global', False)

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
                    "primary_probability": safe_float(annual_prediction.probability),
                    "risk_level": annual_prediction.risk_level,
                    "confidence": safe_float(annual_prediction.confidence),
                    "financial_ratios": {
                        "long_term_debt_to_total_capital": safe_float(annual_prediction.long_term_debt_to_total_capital),
                        "total_debt_to_ebitda": safe_float(annual_prediction.total_debt_to_ebitda),
                        "net_income_margin": safe_float(annual_prediction.net_income_margin),
                        "ebit_to_interest_expense": safe_float(annual_prediction.ebit_to_interest_expense),
                        "return_on_assets": safe_float(annual_prediction.return_on_assets)
                    },
                    "created_at": serialize_datetime(annual_prediction.created_at)
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Unable to create annual prediction. Please try again later."
        )


@router.post("/predict-quarterly")
async def predict_quarterly_default_rate(
    request: QuarterlyPredictionRequest,
    current_user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """Create quarterly default rate prediction using machine learning"""
    try:
        # Check if user has permission to create predictions
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403,
                detail="You need to be part of an organization to create predictions"
            )
        
        company_service = CompanyService(db)
        company = company_service.get_company_by_symbol(request.stock_symbol)
        
        if not company:
            # Only admins can create companies
            if not check_user_permissions(current_user, "admin"):
                raise HTTPException(
                    status_code=403,
                    detail="Company not found and you don't have permission to create companies"
                )
            
            company = company_service.create_company(
                symbol=request.stock_symbol,
                name=request.company_name,
                market_cap=request.market_cap,
                sector=request.sector,
                organization_id=current_user.organization_id,
                created_by=current_user.id
            )
        else:
            # Check if user can access this company
            if current_user.global_role != "super_admin":
                if company.organization_id != current_user.organization_id and not company.is_global:
                    raise HTTPException(
                        status_code=403,
                        detail="You don't have access to this company"
                    )

        # Check for existing prediction in user's context
        existing_prediction = db.query(QuarterlyPrediction).filter(
            and_(
                QuarterlyPrediction.company_id == company.id,
                QuarterlyPrediction.reporting_year == request.reporting_year,
                QuarterlyPrediction.reporting_quarter == request.reporting_quarter,
                or_(
                    QuarterlyPrediction.organization_id == current_user.organization_id,
                    and_(
                        QuarterlyPrediction.organization_id == None,
                        QuarterlyPrediction.created_by == current_user.id
                    )
                )
            )
        ).first()
        
        if existing_prediction:
            raise HTTPException(
                status_code=400,
                detail=f"Quarterly prediction for {request.stock_symbol} in {request.reporting_quarter} {request.reporting_year} already exists"
            )

        ratios = {
            "total_debt_to_ebitda": request.total_debt_to_ebitda,
            "sga_margin": request.sga_margin,
            "long_term_debt_to_total_capital": request.long_term_debt_to_total_capital,
            "return_on_capital": request.return_on_capital
        }

        prediction_result = quarterly_ml_model.predict_default_probability(ratios)

        if "error" in prediction_result:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Quarterly prediction failed",
                    "details": prediction_result["error"]
                }
            )

        quarterly_prediction = company_service.create_quarterly_prediction(
            company=company,
            financial_data=ratios,
            prediction_results=prediction_result,
            reporting_year=request.reporting_year,
            reporting_quarter=request.reporting_quarter,
            organization_id=current_user.organization_id,
            created_by=current_user.id
        )

        return {
            "success": True,
            "message": "Quarterly prediction created successfully",
            "company": {
                "id": str(company.id),
                "symbol": company.symbol,
                "name": company.name,
                "market_cap": safe_float(company.market_cap),
                "sector": company.sector,
                "prediction": {
                    "id": str(quarterly_prediction.id),
                    "type": "quarterly",
                    "reporting_year": quarterly_prediction.reporting_year,
                    "reporting_quarter": quarterly_prediction.reporting_quarter,
                    "probabilities": {
                        "logistic": safe_float(quarterly_prediction.logistic_probability),
                        "gbm": safe_float(quarterly_prediction.gbm_probability),
                        "ensemble": safe_float(quarterly_prediction.ensemble_probability)
                    },
                    "primary_probability": safe_float(quarterly_prediction.ensemble_probability),
                    "risk_level": quarterly_prediction.risk_level,
                    "confidence": safe_float(quarterly_prediction.confidence),
                    "financial_ratios": {
                        "total_debt_to_ebitda": safe_float(quarterly_prediction.total_debt_to_ebitda),
                        "sga_margin": safe_float(quarterly_prediction.sga_margin),
                        "long_term_debt_to_total_capital": safe_float(quarterly_prediction.long_term_debt_to_total_capital),
                        "return_on_capital": safe_float(quarterly_prediction.return_on_capital)
                    },
                    "created_at": serialize_datetime(quarterly_prediction.created_at)
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Quarterly prediction failed",
                "details": str(e)
            }
        )


@router.post("/unified-predict")
async def unified_predict(
    request: UnifiedPredictionRequest,
    current_user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """Unified endpoint for both annual and quarterly predictions"""
    try:
        if request.prediction_type == "annual":
            annual_request = AnnualPredictionRequest(
                stock_symbol=request.stock_symbol,
                company_name=request.company_name,
                market_cap=request.market_cap,
                sector=request.sector,
                reporting_year=request.reporting_year,
                reporting_quarter=request.reporting_quarter,
                long_term_debt_to_total_capital=request.long_term_debt_to_total_capital,
                total_debt_to_ebitda=request.total_debt_to_ebitda,
                net_income_margin=request.net_income_margin,
                ebit_to_interest_expense=request.ebit_to_interest_expense,
                return_on_assets=request.return_on_assets
            )
            return await predict_annual_default_rate(annual_request, current_user, db)
            
        elif request.prediction_type == "quarterly":
            quarterly_request = QuarterlyPredictionRequest(
                stock_symbol=request.stock_symbol,
                company_name=request.company_name,
                market_cap=request.market_cap,
                sector=request.sector,
                reporting_year=request.reporting_year,
                reporting_quarter=request.reporting_quarter,
                total_debt_to_ebitda=request.total_debt_to_ebitda,
                sga_margin=request.sga_margin,
                long_term_debt_to_total_capital=request.long_term_debt_to_total_capital,
                return_on_capital=request.return_on_capital
            )
            return await predict_quarterly_default_rate(quarterly_request, current_user, db)
        
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid prediction_type. Must be 'annual' or 'quarterly'"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"{request.prediction_type.title()} prediction failed",
                "details": str(e)
            }
        )


@router.get("/companies", response_model=Dict)
async def get_companies_with_predictions(
    page: int = 1,
    limit: int = 10,
    sector: str = None,
    search: str = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    current_user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """Get paginated list of companies with their predictions"""
    try:
        company_service = CompanyService(db)
        result = company_service.get_companies_with_predictions(
            page=page,
            limit=limit,
            sector=sector,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order
        )

        formatted_companies = []
        for company in result["companies"]:
            company_data = {
                "id": str(company.id),
                "symbol": company.symbol,
                "name": company.name,
                "market_cap": safe_float(company.market_cap) if company.market_cap else None,
                "sector": company.sector,
                "created_at": serialize_datetime(company.created_at),
                "updated_at": serialize_datetime(company.updated_at),
                "annual_predictions": [],
                "quarterly_predictions": []
            }

            for pred in company.annual_predictions:
                company_data["annual_predictions"].append({
                    "id": str(pred.id),
                    "reporting_year": pred.reporting_year,
                    "reporting_quarter": pred.reporting_quarter,
                    "probability": safe_float(pred.probability),
                    "risk_level": pred.risk_level,
                    "confidence": safe_float(pred.confidence),
                    "created_at": serialize_datetime(pred.created_at)
                })

            for pred in company.quarterly_predictions:
                company_data["quarterly_predictions"].append({
                    "id": str(pred.id),
                    "reporting_year": pred.reporting_year,
                    "reporting_quarter": pred.reporting_quarter,
                    "probabilities": {
                        "logistic": safe_float(pred.logistic_probability),
                        "gbm": safe_float(pred.gbm_probability),
                        "ensemble": safe_float(pred.ensemble_probability)
                    },
                    "primary_probability": safe_float(pred.ensemble_probability),
                    "risk_level": pred.risk_level,
                    "confidence": safe_float(pred.confidence),
                    "created_at": serialize_datetime(pred.created_at)
                })

            formatted_companies.append(company_data)

        return {
            "success": True,
            "companies": formatted_companies,
            "pagination": result["pagination"]
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to retrieve companies",
                "details": str(e)
            }
        )

@router.get("/companies/{company_id}")
async def get_company_by_id(
    company_id: str,
    current_user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """Get specific company by ID with all predictions"""
    try:
        company_service = CompanyService(db)
        company = company_service.get_company_by_id(company_id)
        
        if not company:
            raise HTTPException(
                status_code=404,
                detail=f"Company with ID {company_id} not found"
            )

        company_data = {
            "id": str(company.id),
            "symbol": company.symbol,
            "name": company.name,
            "market_cap": safe_float(company.market_cap) if company.market_cap else None,
            "sector": company.sector,
            "created_at": serialize_datetime(company.created_at),
            "updated_at": serialize_datetime(company.updated_at),
            "annual_predictions": [],
            "quarterly_predictions": []
        }

        for pred in company.annual_predictions:
            company_data["annual_predictions"].append({
                "id": str(pred.id),
                "reporting_year": pred.reporting_year,
                "reporting_quarter": pred.reporting_quarter,
                "probability": safe_float(pred.probability),
                "risk_level": pred.risk_level,
                "confidence": safe_float(pred.confidence),
                "financial_ratios": {
                    "long_term_debt_to_total_capital": safe_float(pred.long_term_debt_to_total_capital),
                    "total_debt_to_ebitda": safe_float(pred.total_debt_to_ebitda),
                    "net_income_margin": safe_float(pred.net_income_margin),
                    "ebit_to_interest_expense": safe_float(pred.ebit_to_interest_expense),
                    "return_on_assets": safe_float(pred.return_on_assets)
                },
                "created_at": serialize_datetime(pred.created_at)
            })

        for pred in company.quarterly_predictions:
            company_data["quarterly_predictions"].append({
                "id": str(pred.id),
                "reporting_year": pred.reporting_year,
                "reporting_quarter": pred.reporting_quarter,
                "probabilities": {
                    "logistic": safe_float(pred.logistic_probability),
                    "gbm": safe_float(pred.gbm_probability),
                    "ensemble": safe_float(pred.ensemble_probability)
                },
                "primary_probability": safe_float(pred.ensemble_probability),
                "risk_level": pred.risk_level,
                "confidence": safe_float(pred.confidence),
                "financial_ratios": {
                    "total_debt_to_ebitda": safe_float(pred.total_debt_to_ebitda),
                    "sga_margin": safe_float(pred.sga_margin),
                    "long_term_debt_to_total_capital": safe_float(pred.long_term_debt_to_total_capital),
                    "return_on_capital": safe_float(pred.return_on_capital)
                },
                "created_at": serialize_datetime(pred.created_at)
            })

        return {
            "success": True,
            "company": company_data
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to retrieve company",
                "details": str(e)
            }
        )

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Prediction API is running",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "annual": "/api/predictions/predict-annual",
            "quarterly": "/api/predictions/predict-quarterly", 
            "unified": "/api/predictions/unified-predict",
            "companies": "/api/predictions/companies",
            "bulk_upload": "/api/predictions/bulk-predict",
            "update": "/api/predictions/update/{company_id}",
            "delete": "/api/predictions/delete/{company_id}",
            "summary": "/api/predictions/summary"
        }
    }

@router.get("/summary")
async def get_summary_stats(
    current_user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """Get optimized summary statistics without fetching full company data"""
    try:
        company_service = CompanyService(db)
        
        total_companies = db.query(Company).count()
        
        high_risk_annual = db.query(AnnualPrediction).filter(
            AnnualPrediction.risk_level.in_(['High', 'Critical'])
        ).count()
        
        high_risk_quarterly = db.query(QuarterlyPrediction).filter(
            QuarterlyPrediction.risk_level.in_(['High', 'Critical'])
        ).count()
        
        high_risk_company_ids = set()
        
        annual_high_risk_ids = db.query(AnnualPrediction.company_id).filter(
            AnnualPrediction.risk_level.in_(['High', 'Critical'])
        ).all()
        high_risk_company_ids.update([id[0] for id in annual_high_risk_ids])
        
        quarterly_high_risk_ids = db.query(QuarterlyPrediction.company_id).filter(
            QuarterlyPrediction.risk_level.in_(['High', 'Critical'])
        ).all()
        high_risk_company_ids.update([id[0] for id in quarterly_high_risk_ids])
        
        high_risk_companies = len(high_risk_company_ids)

        annual_avg = db.query(func.avg(AnnualPrediction.probability)).scalar() or 0
        
        quarterly_avg = db.query(func.avg(QuarterlyPrediction.ensemble_probability)).scalar() or 0
        
        annual_count = db.query(AnnualPrediction).count()
        quarterly_count = db.query(QuarterlyPrediction).count()
        total_predictions = annual_count + quarterly_count
        
        if total_predictions > 0:
            average_default_rate = (
                (annual_avg * annual_count + quarterly_avg * quarterly_count) / total_predictions
            ) * 100  
        else:
            average_default_rate = 0
        
        sectors_covered = db.query(func.count(func.distinct(Company.sector))).scalar() or 0
        
        return {
            "success": True,
            "data": {
                "total_companies": total_companies,
                "average_default_rate": round(safe_float(average_default_rate), 2),
                "high_risk_companies": high_risk_companies,
                "sectors_covered": sectors_covered,
                "prediction_breakdown": {
                    "annual_predictions": annual_count,
                    "quarterly_predictions": quarterly_count,
                    "total_predictions": total_predictions
                },
                "last_updated": datetime.utcnow().isoformat(),
                "model_version": "1.0.0"
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to fetch summary statistics",
                "details": str(e)
            }
        )


@router.post("/bulk-predict", response_model=BulkPredictionResponse)
async def bulk_predict_from_file(
    file: UploadFile = File(...),
    prediction_type: str = "annual",
    current_user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Bulk prediction endpoint that accepts CSV/Excel files with company data.
    
    Supports 1000-5000 companies at once.
    
    Expected columns for Annual predictions:
    - stock_symbol, company_name, market_cap, sector, reporting_year
    - long_term_debt_to_total_capital, total_debt_to_ebitda, net_income_margin
    - ebit_to_interest_expense, return_on_assets
    
    Expected columns for Quarterly predictions:
    - stock_symbol, company_name, market_cap, sector, reporting_year, reporting_quarter
    - total_debt_to_ebitda, sga_margin, long_term_debt_to_total_capital, return_on_capital
    """
    start_time = time.time()
    
    try:
        if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
            raise HTTPException(
                status_code=400,
                detail="File must be CSV (.csv) or Excel (.xlsx, .xls)"
            )
        
        content = await file.read()
        
        try:
            if file.filename.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(content))
            else:
                df = pd.read_excel(io.BytesIO(content))
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error reading file: {str(e)}"
            )
        
        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="File contains no data"
            )
        
        if len(df) > 5000:
            raise HTTPException(
                status_code=400,
                detail=f"File contains {len(df)} rows. Maximum allowed is 5000 companies."
            )
        
        if prediction_type == "annual":
            required_columns = [
                'stock_symbol', 'company_name', 'long_term_debt_to_total_capital',
                'total_debt_to_ebitda', 'net_income_margin', 'ebit_to_interest_expense', 'return_on_assets'
            ]
        elif prediction_type == "quarterly":
            required_columns = [
                'stock_symbol', 'company_name', 'reporting_year', 'reporting_quarter',
                'total_debt_to_ebitda', 'sga_margin', 'long_term_debt_to_total_capital', 'return_on_capital'
            ]
        else:
            raise HTTPException(
                status_code=400,
                detail="prediction_type must be 'annual' or 'quarterly'"
            )
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {missing_columns}"
            )
        
        company_service = CompanyService(db)
        results = []
        successful_predictions = 0
        failed_predictions = 0
        
        for index, row in df.iterrows():
            try:
                company = company_service.create_company(
                    symbol=str(row['stock_symbol']).strip().upper(),
                    name=str(row['company_name']).strip(),
                    market_cap=safe_float(row.get('market_cap', 1000000000)),
                    sector=str(row.get('sector', 'Unknown')).strip(),
                    organization_id=current_user.organization_id,
                    created_by=current_user.id
                )
                
                if prediction_type == "annual":
                    financial_data = {
                        "long_term_debt_to_total_capital": safe_float(row['long_term_debt_to_total_capital']),
                        "total_debt_to_ebitda": safe_float(row['total_debt_to_ebitda']),
                        "net_income_margin": safe_float(row['net_income_margin']),
                        "ebit_to_interest_expense": safe_float(row['ebit_to_interest_expense']),
                        "return_on_assets": safe_float(row['return_on_assets'])
                    }
                    
                    prediction_result = ml_model.predict_default_probability(financial_data)
                    
                    if "error" in prediction_result:
                        raise Exception(prediction_result["error"])
                    
                    prediction = company_service.create_annual_prediction(
                        company=company,
                        financial_data=financial_data,
                        prediction_results=prediction_result,
                        reporting_year=str(row.get('reporting_year', '2024')),
                        reporting_quarter=str(row['reporting_quarter']),
                        organization_id=current_user.organization_id,
                        created_by=current_user.id
                    )
                    
                    result_item = BulkPredictionItem(
                        stock_symbol=company.symbol,
                        company_name=company.name,
                        sector=company.sector,
                        market_cap=safe_float(company.market_cap) if company.market_cap else None,
                        prediction={
                            "id": str(prediction.id),
                            "type": "annual",
                            "probability": safe_float(prediction.probability),
                            "primary_probability": safe_float(prediction.probability),
                            "risk_level": prediction.risk_level,
                            "confidence": safe_float(prediction.confidence)
                        },
                        status="success"
                    )
                    
                elif prediction_type == "quarterly":
                    financial_data = {
                        "total_debt_to_ebitda": safe_float(row['total_debt_to_ebitda']),
                        "sga_margin": safe_float(row['sga_margin']),
                        "long_term_debt_to_total_capital": safe_float(row['long_term_debt_to_total_capital']),
                        "return_on_capital": safe_float(row['return_on_capital'])
                    }
                    
                    prediction_result = quarterly_ml_model.predict_default_probability(financial_data)
                    
                    if "error" in prediction_result:
                        raise Exception(prediction_result["error"])
                    
                    prediction = company_service.create_quarterly_prediction(
                        company=company,
                        financial_data=financial_data,
                        prediction_results=prediction_result,
                        reporting_year=str(row['reporting_year']),
                        reporting_quarter=str(row['reporting_quarter']),
                        organization_id=current_user.organization_id,
                        created_by=current_user.id
                    )
                    
                    result_item = BulkPredictionItem(
                        stock_symbol=company.symbol,
                        company_name=company.name,
                        sector=company.sector,
                        market_cap=safe_float(company.market_cap) if company.market_cap else None,
                        prediction={
                            "id": str(prediction.id),
                            "type": "quarterly",
                            "probabilities": {
                                "logistic": safe_float(prediction.logistic_probability),
                                "gbm": safe_float(prediction.gbm_probability),
                                "ensemble": safe_float(prediction.ensemble_probability)
                            },
                            "primary_probability": safe_float(prediction.ensemble_probability),
                            "risk_level": prediction.risk_level,
                            "confidence": safe_float(prediction.confidence)
                        },
                        status="success"
                    )
                
                successful_predictions += 1
                
            except Exception as e:
                result_item = BulkPredictionItem(
                    stock_symbol=str(row.get('stock_symbol', 'UNKNOWN')),
                    company_name=str(row.get('company_name', 'Unknown Company')),
                    sector=str(row.get('sector', 'Unknown')),
                    market_cap=safe_float(row.get('market_cap', 0)) if row.get('market_cap') else None,
                    prediction={},
                    status="failed",
                    error_message=str(e)
                )
                failed_predictions += 1
            
            results.append(result_item)
        
        processing_time = time.time() - start_time
        
        return BulkPredictionResponse(
            success=True,
            message=f"Bulk prediction completed. {successful_predictions} successful, {failed_predictions} failed.",
            total_companies=len(df),
            successful_predictions=successful_predictions,
            failed_predictions=failed_predictions,
            results=results,
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Bulk prediction failed",
                "details": str(e)
            }
        )

@router.post("/bulk-predict-async", response_model=BulkJobResponse)
async def bulk_predict_async(
    file: UploadFile = File(...),
    prediction_type: str = "annual",
    current_user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Submit a bulk prediction job that runs in the background.
    Returns a job ID that can be used to check status and retrieve results.
    
    This endpoint is recommended for very large files (>1000 companies) to avoid timeouts.
    For smaller files, use the synchronous /bulk-predict endpoint.
    
    Supports CSV and Excel files with 1000-50000 companies.
    """
    
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(
            status_code=400,
            detail="File must be Excel (.xlsx, .xls) or CSV (.csv) format"
        )
    
    if prediction_type not in ["annual", "quarterly"]:
        raise HTTPException(
            status_code=400,
            detail="prediction_type must be 'annual' or 'quarterly'"
        )
    
    try:
        contents = await file.read()
        
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(contents))
        
        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="File is empty"
            )
        
        company_count = len(df)
        
        base_required = ['stock_symbol', 'company_name']
        
        if prediction_type == "annual":
            required_columns = base_required + [
                'long_term_debt_to_total_capital', 'total_debt_to_ebitda', 
                'net_income_margin', 'ebit_to_interest_expense', 'return_on_assets'
            ]
        else:  # quarterly
            required_columns = base_required + [
                'reporting_year', 'reporting_quarter', 'total_debt_to_ebitda', 
                'sga_margin', 'long_term_debt_to_total_capital', 'return_on_capital'
            ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        file_content_b64 = base64.b64encode(contents).decode('utf-8')
        
        from ...workers.tasks import process_bulk_normalized_task
        task = process_bulk_normalized_task.delay(
            file_content_b64, 
            file.filename, 
            prediction_type,
            current_user.organization_id,
            current_user.id
        )
        
        if company_count <= 100:
            estimated_time = f"{company_count * 2:.0f}-{company_count * 4:.0f} seconds"
        elif company_count <= 1000:
            estimated_time = f"{company_count * 1.5 / 60:.1f}-{company_count * 3 / 60:.1f} minutes"
        else:
            estimated_time = f"{company_count * 1 / 60:.1f}-{company_count * 2 / 60:.1f} minutes"
        
        return BulkJobResponse(
            success=True,
            message=f"Bulk {prediction_type} prediction job submitted successfully. Processing {company_count} companies in background.",
            job_id=task.id,
            status="PENDING",
            filename=file.filename,
            estimated_processing_time=estimated_time
        )
        
    except pd.errors.EmptyDataError:
        raise HTTPException(
            status_code=400,
            detail="File is empty or contains no data"
        )
    except pd.errors.ParserError as e:
        raise HTTPException(
            status_code=400,
            detail=f"File parsing error: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to submit bulk prediction job",
                "details": str(e)
            }
        )


@router.get("/job-status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(current_verified_user)
):
    """
    Check the status of a bulk prediction job.
    
    Status values:
    - PENDING: Job is waiting to be processed
    - PROGRESS: Job is currently being processed
    - SUCCESS: Job completed successfully
    - FAILURE: Job failed
    """
    try:
        from ...workers.celery_app import celery_app
        
        task_result = celery_app.AsyncResult(job_id)
        
        if task_result.state == "PENDING":
            return JobStatusResponse(
                success=True,
                job_id=job_id,
                status="PENDING",
                message="Job is waiting to be processed...",
                progress=None,
                result=None
            )
        
        elif task_result.state == "PROGRESS":
            progress_info = task_result.info or {}
            return JobStatusResponse(
                success=True,
                job_id=job_id,
                status="PROGRESS",
                message=progress_info.get("status", "Processing..."),
                progress={
                    "current": progress_info.get("current", 0),
                    "total": progress_info.get("total", 0),
                    "filename": progress_info.get("filename", ""),
                    "successful": progress_info.get("successful", 0),
                    "failed": progress_info.get("failed", 0),
                    "prediction_type": progress_info.get("prediction_type", "unknown")
                },
                result=None
            )
        
        elif task_result.state == "SUCCESS":
            result_data = task_result.result
            return JobStatusResponse(
                success=True,
                job_id=job_id,
                status="SUCCESS",
                message="Job completed successfully",
                progress=None,
                result=result_data
            )
        
        elif task_result.state == "FAILURE":
            error_info = task_result.info or {}
            return JobStatusResponse(
                success=False,
                job_id=job_id,
                status="FAILURE",
                message="Job failed",
                progress=None,
                result=None,
                error=error_info.get("error", str(task_result.info))
            )
        
        else:
            return JobStatusResponse(
                success=True,
                job_id=job_id,
                status=task_result.state,
                message=f"Job status: {task_result.state}",
                progress=None,
                result=None
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to get job status",
                "details": str(e)
            }
        )


@router.get("/job-result/{job_id}")
async def get_job_result(
    job_id: str,
    current_user: User = Depends(current_verified_user)
):
    """
    Get the complete result of a completed bulk prediction job.
    Only returns results for successfully completed jobs.
    """
    try:
        from ...workers.celery_app import celery_app
        
        task_result = celery_app.AsyncResult(job_id)
        
        if task_result.state == "SUCCESS":
            return task_result.result
        elif task_result.state == "PENDING":
            raise HTTPException(
                status_code=202,
                detail="Job is still pending. Please check job status."
            )
        elif task_result.state == "PROGRESS":
            raise HTTPException(
                status_code=202,
                detail="Job is still in progress. Please check job status."
            )
        elif task_result.state == "FAILURE":
            raise HTTPException(
                status_code=400,
                detail="Job failed. Check job status for error details."
            )
        else:
            raise HTTPException(
                status_code=404,
                detail="Job not found or in unknown state"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to get job result",
                "details": str(e)
            }
        )


@router.put("/update/{company_id}")
async def update_company_prediction(
    company_id: str,
    request: PredictionUpdateRequest,
    current_user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """Update company data and recalculate predictions if financial ratios change"""
    try:
        try:
            uuid.UUID(company_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid company ID format. Must be a valid UUID."
            )

        company_service = CompanyService(db)
        company = company_service.get_company_by_id(company_id)
        
        if not company:
            raise HTTPException(
                status_code=404,
                detail="Company not found"
            )

        if request.company_name:
            company.name = request.company_name
        if request.market_cap is not None:
            company.market_cap = request.market_cap
        if request.sector:
            company.sector = request.sector
        
        company.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(company)
        
        response_data = {
            "success": True,
            "message": "Company updated successfully",
            "company": {
                "id": str(company.id),
                "symbol": company.symbol,
                "name": company.name,
                "market_cap": safe_float(company.market_cap) if company.market_cap else None,
                "sector": company.sector,
                "updated_at": serialize_datetime(company.updated_at)
            }
        }
        
        updated_prediction = None
        if request.prediction_type and request.reporting_year:
            
            if request.prediction_type == "annual":
                if not all([
                    request.long_term_debt_to_total_capital is not None,
                    request.total_debt_to_ebitda is not None,
                    request.net_income_margin is not None,
                    request.ebit_to_interest_expense is not None,
                    request.return_on_assets is not None
                ]):
                    raise HTTPException(
                        status_code=400,
                        detail="All annual prediction fields are required for annual prediction update"
                    )
                
                existing_prediction = company_service.get_annual_prediction(
                    company.id, request.reporting_year
                )
                
                if existing_prediction:
                    db.delete(existing_prediction)
                    db.flush() 
                
                financial_data = {
                    "long_term_debt_to_total_capital": request.long_term_debt_to_total_capital,
                    "total_debt_to_ebitda": request.total_debt_to_ebitda,
                    "net_income_margin": request.net_income_margin,
                    "ebit_to_interest_expense": request.ebit_to_interest_expense,
                    "return_on_assets": request.return_on_assets
                }
                
                prediction_result = ml_model.predict_default_probability(financial_data)
                
                if "error" in prediction_result:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Annual prediction failed: {prediction_result['error']}"
                    )
                
                updated_prediction = company_service.create_annual_prediction(
                    company=company,
                    financial_data=financial_data,
                    prediction_results=prediction_result,
                    reporting_year=request.reporting_year,
                    reporting_quarter=request.reporting_quarter
                )
                
                response_data["updated_prediction"] = {
                    "type": "annual",
                    "id": str(updated_prediction.id),
                    "reporting_year": updated_prediction.reporting_year,
                    "reporting_quarter": updated_prediction.reporting_quarter,
                    "probability": safe_float(updated_prediction.probability),
                    "primary_probability": safe_float(updated_prediction.probability),
                    "risk_level": updated_prediction.risk_level,
                    "confidence": safe_float(updated_prediction.confidence),
                    "action": "replaced" if existing_prediction else "created",
                    "financial_ratios": {
                        "long_term_debt_to_total_capital": safe_float(updated_prediction.long_term_debt_to_total_capital),
                        "total_debt_to_ebitda": safe_float(updated_prediction.total_debt_to_ebitda),
                        "net_income_margin": safe_float(updated_prediction.net_income_margin),
                        "ebit_to_interest_expense": safe_float(updated_prediction.ebit_to_interest_expense),
                        "return_on_assets": safe_float(updated_prediction.return_on_assets)
                    }
                }
                
            elif request.prediction_type == "quarterly":
                if not all([
                    request.total_debt_to_ebitda is not None,
                    request.sga_margin is not None,
                    request.long_term_debt_to_total_capital is not None,
                    request.return_on_capital is not None,
                    request.reporting_quarter is not None
                ]):
                    raise HTTPException(
                        status_code=400,
                        detail="All quarterly prediction fields are required for quarterly prediction update"
                    )
                
                existing_prediction = company_service.get_quarterly_prediction(
                    company.id, request.reporting_year, request.reporting_quarter
                )
                
                if existing_prediction:
                    db.delete(existing_prediction)
                    db.flush()  
                
                financial_data = {
                    "total_debt_to_ebitda": request.total_debt_to_ebitda,
                    "sga_margin": request.sga_margin,
                    "long_term_debt_to_total_capital": request.long_term_debt_to_total_capital,
                    "return_on_capital": request.return_on_capital
                }
                
                prediction_result = quarterly_ml_model.predict_default_probability(financial_data)
                
                if "error" in prediction_result:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Quarterly prediction failed: {prediction_result['error']}"
                    )
                
                updated_prediction = company_service.create_quarterly_prediction(
                    company=company,
                    financial_data=financial_data,
                    prediction_results=prediction_result,
                    reporting_year=request.reporting_year,
                    reporting_quarter=request.reporting_quarter
                )
                
                response_data["updated_prediction"] = {
                    "type": "quarterly",
                    "id": str(updated_prediction.id),
                    "reporting_year": updated_prediction.reporting_year,
                    "reporting_quarter": updated_prediction.reporting_quarter,
                    "probabilities": {
                        "logistic": safe_float(updated_prediction.logistic_probability),
                        "gbm": safe_float(updated_prediction.gbm_probability),
                        "ensemble": safe_float(updated_prediction.ensemble_probability)
                    },
                    "primary_probability": safe_float(updated_prediction.ensemble_probability),
                    "risk_level": updated_prediction.risk_level,
                    "confidence": safe_float(updated_prediction.confidence),
                    "action": "replaced" if existing_prediction else "created",
                    "financial_ratios": {
                        "total_debt_to_ebitda": safe_float(updated_prediction.total_debt_to_ebitda),
                        "sga_margin": safe_float(updated_prediction.sga_margin),
                        "long_term_debt_to_total_capital": safe_float(updated_prediction.long_term_debt_to_total_capital),
                        "return_on_capital": safe_float(updated_prediction.return_on_capital)
                    }
                }
            
            else:
                raise HTTPException(
                    status_code=400,
                    detail="prediction_type must be 'annual' or 'quarterly'"
                )
        
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to update company",
                "details": str(e)
            }
        )


@router.delete("/delete/{company_id}")
async def delete_company_and_predictions(
    company_id: str,
    current_user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """Delete a company and all its predictions (annual and quarterly)"""
    try:
        try:
            uuid.UUID(company_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid company ID format. Must be a valid UUID."
            )

        company_service = CompanyService(db)
        company = company_service.get_company_by_id(company_id)
        
        if not company:
            raise HTTPException(
                status_code=404,
                detail="Company not found"
            )

        company_symbol = company.symbol
        company_name = company.name
        annual_predictions_count = len(company.annual_predictions)
        quarterly_predictions_count = len(company.quarterly_predictions)

        db.delete(company)
        db.commit()
        
        return {
            "success": True,
            "message": f"Company '{company_name}' ({company_symbol}) and all predictions deleted successfully",
            "deleted_company": {
                "id": company_id,
                "symbol": company_symbol,
                "name": company_name,
                "annual_predictions_deleted": annual_predictions_count,
                "quarterly_predictions_deleted": quarterly_predictions_count
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to delete company",
                "details": str(e)
            }
        )

@router.delete("/predictions/annual/{prediction_id}")
async def delete_annual_prediction(
    prediction_id: str,
    current_user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """Delete a specific annual prediction"""
    try:
        try:
            uuid.UUID(prediction_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid prediction ID format. Must be a valid UUID."
            )

        prediction = db.query(AnnualPrediction).filter(AnnualPrediction.id == prediction_id).first()
        
        if not prediction:
            raise HTTPException(
                status_code=404,
                detail="Annual prediction not found"
            )

        db.delete(prediction)
        db.commit()
        
        return {
            "success": True,
            "message": "Annual prediction deleted successfully",
            "deleted_prediction": {
                "id": prediction_id,
                "type": "annual"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to delete annual prediction",
                "details": str(e)
            }
        )

@router.delete("/predictions/quarterly/{prediction_id}")
async def delete_quarterly_prediction(
    prediction_id: str,
    current_user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """Delete a specific quarterly prediction"""
    try:
        try:
            uuid.UUID(prediction_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid prediction ID format. Must be a valid UUID."
            )

        prediction = db.query(QuarterlyPrediction).filter(QuarterlyPrediction.id == prediction_id).first()
        
        if not prediction:
            raise HTTPException(
                status_code=404,
                detail="Quarterly prediction not found"
            )

        db.delete(prediction)
        db.commit()
        
        return {
            "success": True,
        }
        raise HTTPException(
            status_code=400,
            detail="File is empty or contains no data"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Quarterly bulk prediction job failed",
                "details": str(e)
            }
        )
