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
def check_user_permissions(user: User, required_role: str = "member"):
    """Check if user has required permissions based on 5-role hierarchy:
    1. super_admin: Full access
    2. tenant_admin: Tenant scope access  
    3. org admin: Organization admin access
    4. member: Organization member access
    5. user: No organization access
    """
    # Super admin and tenant admin have full permissions
    if user.global_role in ["super_admin", "tenant_admin"]:
        return True
    
    # Users without organization have no access (except super/tenant admin)
    if user.organization_id is None:
        return False
    
    # Organization level permissions: admin > member
    role_hierarchy = {"member": 0, "admin": 1}
    user_level = role_hierarchy.get(user.organization_role, -1)
    required_level = role_hierarchy.get(required_role, 0)
    
    return user_level >= required_level

def get_organization_filter(user: User, db: Session = None):
    """Get filter conditions based on user's organization access"""
    if user.global_role == "super_admin":
        # Super admins see everything
        return None
    elif user.global_role == "tenant_admin":
        # Tenant admins see companies from all organizations in their tenant
        if user.tenant_id and db:
            from ...core.database import Organization
            org_subquery = db.query(Organization.id).filter(Organization.tenant_id == user.tenant_id).subquery()
            return or_(
                CompanyModel.organization_id.in_(org_subquery),
                CompanyModel.is_global == True
            )
        return CompanyModel.id == None  # No tenant assigned
    
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
    """Get paginated list of companies with role-based filtering
    
    Access Control:
    - Members+ with organization can view companies
    - Users see only companies from their organization scope
    - Super admins see all companies
    - Tenant admins see companies from their tenant organizations
    """
    try:
        # Check if user has access to view companies (member+ with organization)
        if not check_user_permissions(current_user, "member"):
            raise HTTPException(
                status_code=403, 
                detail="You need to be a member of an organization to view companies"
            )
        
        # Get organization-based filter for data isolation
        org_filter = get_organization_filter(current_user, db)
        
        service = CompanyService(db)
        result = service.get_companies_with_predictions(
            page=page,
            limit=limit,
            sector=sector,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            organization_filter=org_filter  # Apply role-based filtering
        )
        
        companies_data = []
        for company in result["companies"]:
            company_data = {
                "id": str(company.id),
                "symbol": company.symbol,
                "name": company.name,
                "market_cap": safe_float(company.market_cap),
                "sector": company.sector,
                "organization_id": str(company.organization_id) if company.organization_id else None,
                "created_by": str(company.created_by) if company.created_by else None,
                "is_global": getattr(company, 'is_global', False),
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
                        "created_by": str(pred.created_by) if pred.created_by else None,
                        "organization_id": str(pred.organization_id) if pred.organization_id else None,
                        "created_at": serialize_datetime(pred.created_at)
                    } for pred in company.annual_predictions[:5]  # Limit to 5 recent predictions
                ],
                "prediction_count": len(company.annual_predictions)
            }
            companies_data.append(company_data)
        
        return {
            "companies": companies_data,
            "total": result["total"],
            "page": page,
            "limit": limit,
            "total_pages": math.ceil(result["total"] / limit),
            "has_next": page < math.ceil(result["total"] / limit),
            "has_prev": page > 1,
            "access_info": {
                "user_role": current_user.global_role,
                "organization_role": current_user.organization_role,
                "organization_id": str(current_user.organization_id) if current_user.organization_id else None,
                "tenant_id": str(current_user.tenant_id) if current_user.tenant_id else None,
                "data_scope": "global" if current_user.global_role == "super_admin" else 
                            "tenant" if current_user.global_role == "tenant_admin" else "organization"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to retrieve companies: {str(e)}"
        )
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
    """Create a new company (Members+ with organization)
    
    Access Control:
    - Members+ with organization can create companies
    - Companies are automatically assigned to user's organization
    - Symbol must be unique within user's access scope
    """
    try:
        # Check if user has permission to create companies (member+ with organization)
        if not check_user_permissions(current_user, "member"):
            raise HTTPException(
                status_code=403, 
                detail="You need to be a member of an organization to create companies"
            )
        
        # Ensure user has an organization (unless super_admin/tenant_admin)
        if current_user.global_role not in ["super_admin", "tenant_admin"] and not current_user.organization_id:
            raise HTTPException(
                status_code=403, 
                detail="You must be assigned to an organization to create companies"
            )
        
        service = CompanyService(db)
        
        # Check if company with symbol already exists in user's scope
        org_filter = get_organization_filter(current_user, db)
        
        if org_filter is None:  # Super admin
            existing = service.get_company_by_symbol(company.symbol)
        else:
            # Check within user's scope
            existing = db.query(CompanyModel).filter(
                and_(
                    CompanyModel.symbol == company.symbol.upper(),
                    org_filter
                )
            ).first()
        
        if existing:
            raise HTTPException(
                status_code=400, 
                detail=f"Company with symbol '{company.symbol}' already exists in your scope"
            )
        
        # Determine organization_id for the new company
        organization_id = None
        if current_user.global_role == "super_admin":
            # Super admin can create global companies or assign to specific org
            organization_id = getattr(company, 'organization_id', None)
        elif current_user.global_role == "tenant_admin":
            # Tenant admin creates for their tenant (use their org or specified)
            organization_id = getattr(company, 'organization_id', current_user.organization_id)
        else:
            # Regular users create for their organization
            organization_id = current_user.organization_id
        
        # Create company with enhanced tracking
        new_company = service.create_company(
            symbol=company.symbol.upper(),
            name=company.name,
            market_cap=company.market_cap,
            sector=company.sector,
            organization_id=organization_id,
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
                "organization_id": str(new_company.organization_id) if new_company.organization_id else None,
                "created_by": str(new_company.created_by),
                "created_at": serialize_datetime(new_company.created_at)
            },
            "message": f"Company created successfully and assigned to organization",
            "access_info": {
                "user_role": current_user.global_role,
                "organization_role": current_user.organization_role,
                "organization_id": str(current_user.organization_id) if current_user.organization_id else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Unable to create company: {str(e)}"
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