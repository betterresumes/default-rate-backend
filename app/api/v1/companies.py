from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from ...core.database import get_db, User, Company as CompanyModel
from ...schemas.schemas import (
    CompanyResponse, CompanyCreate, CompanyUpdate, CompanyListResponse, PaginatedResponse
)
from .auth_multi_tenant import get_current_active_user
from typing import Optional
from datetime import datetime
import math

# Helper function for user verification  
current_verified_user = get_current_active_user

router = APIRouter()

# Role-based permission helper
def check_user_permissions(user: User, required_role: str = "user"):
    """Check if user has required permissions"""
    if user.global_role == "super_admin":
        return True
    
    if user.organization_id is None:
        return False
    
    # Simplified role hierarchy: admin > user
    role_hierarchy = {"user": 0, "admin": 1}
    user_level = role_hierarchy.get(user.organization_role, -1)
    required_level = role_hierarchy.get(required_role, 0)
    
    return user_level >= required_level

def get_organization_filter(user: User):
    """Get filter conditions based on user's organization access"""
    if user.global_role == "super_admin":
        # Super admins see everything
        return None
    
    if user.organization_id is None:
        # Users without organization see nothing
        return CompanyModel.id == None  # This will return no results
    
    # Regular users see:
    # 1. Companies from their organization
    # 2. Global companies (is_global = True)
    return or_(
        CompanyModel.organization_id == user.organization_id,
        CompanyModel.is_global == True
    )

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
        # Check if it's NaN or infinite
        if math.isnan(float_val) or math.isinf(float_val):
            return None
        return float_val
    except (ValueError, TypeError):
        return None


@router.get("/", response_model=PaginatedResponse)
async def get_companies(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    sector: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("name"),
    sort_order: str = Query("asc"),
    current_user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """Get paginated list of companies with filtering and sorting"""
    try:
        # Check if user has access to view companies
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403, 
                detail="You need to be part of an organization to view companies"
            )
        
        # Get organization-based filter
        org_filter = get_organization_filter(current_user)
        
        service = CompanyService(db)
        result = service.get_companies_with_predictions(
            page=page,
            limit=limit,
            sector=sector,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            organization_filter=org_filter  # Pass the filter to service
        )
        
        companies_data = []
        for company in result["companies"]:
            company_data = {
                "id": str(company.id),
                "symbol": company.symbol,
                "name": company.name,
                "market_cap": safe_float(company.market_cap),
                "sector": company.sector,
                "created_at": serialize_datetime(company.created_at),
                "updated_at": serialize_datetime(company.updated_at),
                "annual_predictions": [
                    {
                        "id": str(pred.id),
                        "reporting_year": pred.reporting_year,
                        "reporting_quarter": pred.reporting_quarter,
                        "risk_level": pred.risk_level,
                        "confidence": safe_float(pred.confidence),
                        "probability": safe_float(pred.probability),
                        "primary_probability": safe_float(pred.probability),
                        "long_term_debt_to_total_capital": safe_float(pred.long_term_debt_to_total_capital),
                        "total_debt_to_ebitda": safe_float(pred.total_debt_to_ebitda),
                        "net_income_margin": safe_float(pred.net_income_margin),
                        "ebit_to_interest_expense": safe_float(pred.ebit_to_interest_expense),
                        "return_on_assets": safe_float(pred.return_on_assets),
                        "created_at": serialize_datetime(pred.created_at)
                    } for pred in company.annual_predictions
                ],
                "quarterly_predictions": [
                    {
                        "id": str(pred.id),
                        "reporting_year": pred.reporting_year,
                        "reporting_quarter": pred.reporting_quarter,
                        "risk_level": pred.risk_level,
                        "confidence": safe_float(pred.confidence),
                        "ensemble_probability": safe_float(pred.ensemble_probability),
                        "logistic_probability": safe_float(pred.logistic_probability),
                        "gbm_probability": safe_float(pred.gbm_probability),
                        "total_debt_to_ebitda": safe_float(pred.total_debt_to_ebitda),
                        "sga_margin": safe_float(pred.sga_margin),
                        "long_term_debt_to_total_capital": safe_float(pred.long_term_debt_to_total_capital),
                        "return_on_capital": safe_float(pred.return_on_capital),
                        "created_at": serialize_datetime(pred.created_at)
                    } for pred in company.quarterly_predictions
                ],
                "annual_predictions_count": len(company.annual_predictions),
                "quarterly_predictions_count": len(company.quarterly_predictions)
            }
            companies_data.append(company_data)
        
        return PaginatedResponse(
            success=True,
            data={"companies": companies_data},
            pagination=result["pagination"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail="Unable to fetch companies. Please try again later."
        )


@router.get("/{company_id}", response_model=dict)
async def get_company_by_id(
    company_id: str, 
    current_user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """Get company by ID with full details"""
    try:
        # Check if user has access to view companies
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403, 
                detail="You need to be part of an organization to view companies"
            )
        
        service = CompanyService(db)
        
        # First get the company to check access
        company = service.get_company_by_id(company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Check if user can access this specific company
        org_filter = get_organization_filter(current_user)
        if org_filter is not None:  # If not super admin, check access
            # Verify company access based on organization
            if current_user.global_role != "super_admin":
                if company.organization_id != current_user.organization_id and not company.is_global:
                    raise HTTPException(
                        status_code=404, 
                        detail="Company not found"  # Don't reveal existence
                    )
        
        # Filter predictions based on organization access
        annual_predictions = []
        quarterly_predictions = []
        
        for pred in company.annual_predictions:
            # Users can see predictions from their org or without org (if they created them)
            if (current_user.global_role == "super_admin" or
                pred.organization_id == current_user.organization_id or
                (pred.organization_id is None and pred.created_by == current_user.id)):
                annual_predictions.append({
                    "id": str(pred.id),
                    "reporting_year": pred.reporting_year,
                    "reporting_quarter": pred.reporting_quarter,
                    "risk_level": pred.risk_level,
                    "confidence": safe_float(pred.confidence),
                    "probability": safe_float(pred.probability),
                    "primary_probability": safe_float(pred.probability),
                    "created_at": serialize_datetime(pred.created_at)
                })
        
        for pred in company.quarterly_predictions:
            # Same filtering logic for quarterly predictions
            if (current_user.global_role == "super_admin" or
                pred.organization_id == current_user.organization_id or
                (pred.organization_id is None and pred.created_by == current_user.id)):
                quarterly_predictions.append({
                    "id": str(pred.id),
                    "reporting_year": pred.reporting_year,
                    "reporting_quarter": pred.reporting_quarter,
                    "risk_level": pred.risk_level,
                    "confidence": safe_float(pred.confidence),
                    "ensemble_probability": safe_float(pred.ensemble_probability),
                    "logistic_probability": safe_float(pred.logistic_probability),
                    "gbm_probability": safe_float(pred.gbm_probability),
                    "created_at": serialize_datetime(pred.created_at)
                })
        
        
        return {
            "success": True,
            "data": {
                "id": str(company.id),
                "symbol": company.symbol,
                "name": company.name,
                "market_cap": safe_float(company.market_cap),
                "sector": company.sector,
                "created_at": serialize_datetime(company.created_at),
                "updated_at": serialize_datetime(company.updated_at),
                "annual_predictions": annual_predictions,
                "quarterly_predictions": quarterly_predictions
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail="Unable to fetch company details. Please try again later."
        )


@router.post("/", response_model=dict)
async def create_company(
    company: CompanyCreate,
    current_user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """Create a new company (requires admin role)"""
    try:
        # Check if user has admin permissions
        if not check_user_permissions(current_user, "admin"):
            raise HTTPException(
                status_code=403, 
                detail="You need admin privileges to create companies"
            )
        
        service = CompanyService(db)
        
        # Check if company with symbol already exists
        existing = service.get_company_by_symbol(company.symbol)
        if existing:
            raise HTTPException(
                status_code=400, 
                detail="A company with this symbol already exists"
            )
        
        # Create company with user's organization context
        new_company = service.create_company(
            symbol=company.symbol.upper(),
            name=company.name,
            market_cap=company.market_cap,
            sector=company.sector,
            organization_id=current_user.organization_id,
            created_by=current_user.id
        )
        
        return {
            "success": True,
            "data": {
                "id": str(new_company.id),
                "symbol": new_company.symbol,
                "name": new_company.name,
                "market_cap": safe_float(new_company.market_cap),
                "sector": new_company.sector,
                "created_at": serialize_datetime(new_company.created_at)
            },
            "message": "Company created successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail="Unable to create company. Please try again later."
        )


@router.get("/search/{symbol}", response_model=dict)
async def get_company_by_symbol(
    symbol: str,
    current_user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """Get company by symbol"""
    try:
        # Check if user has access to view companies
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403, 
                detail="You need to be part of an organization to view companies"
            )
        
        service = CompanyService(db)
        company = service.get_company_by_symbol(symbol.upper())
        
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # Check organization access
        if current_user.global_role != "super_admin":
            if company.organization_id != current_user.organization_id and not company.is_global:
                raise HTTPException(status_code=404, detail="Company not found")
        
        return {
            "success": True,
            "data": {
                "id": str(company.id),
                "symbol": company.symbol,
                "name": company.name,
                "market_cap": safe_float(company.market_cap),
                "sector": company.sector,
                "created_at": serialize_datetime(company.created_at),
                "updated_at": serialize_datetime(company.updated_at)
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail="Unable to fetch company. Please try again later."
        )