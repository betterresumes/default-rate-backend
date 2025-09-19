from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from ...core.database import get_db, User, Company as CompanyModel
from ...schemas.schemas import (
    CompanyResponse, CompanyCreate, CompanyUpdate, CompanyListResponse, PaginatedResponse
)
from .auth_multi_tenant import get_current_active_user
from ...services.services import CompanyService
from typing import Optional
from datetime import datetime
import math

# Helper function for user verification  
current_verified_user = get_current_active_user

router = APIRouter()

# New Role-based permission helper for 5-role system
def check_user_permissions(user: User, required_role: str = "user"):
    """Check if user has required permissions with new 5-role system"""
    # Role hierarchy: super_admin > tenant_admin > org_admin > org_member > user
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

def get_organization_filter(user: User, db: Session = None):
    """Get filter conditions based on user's organization access with new role system"""
    if user.role == "super_admin":
        # Super admins see everything
        return None
    
    if user.role == "tenant_admin" and user.tenant_id:
        # Tenant admins should only see orgs in their tenant, NOT everything
        if db:
            from ...core.database import Organization
            tenant_org_ids = db.query(Organization.id).filter(Organization.tenant_id == user.tenant_id).all()
            tenant_org_ids = [str(org.id) for org in tenant_org_ids]
            if tenant_org_ids:
                # Show companies from tenant organizations + global companies
                return or_(
                    CompanyModel.organization_id.in_(tenant_org_ids),
                    CompanyModel.organization_id.is_(None)  # Global companies
                )
            else:
                # No orgs in tenant, only global
                return CompanyModel.organization_id.is_(None)
        else:
            # Fallback without db access - restrict to none
            return CompanyModel.id == None
    
    if user.organization_id is None:
        # Users without organization should NOT see global data (SECURITY FIX)
        # Only super_admin can see global data
        return CompanyModel.id.is_(None)  # This returns no results (correct SQLAlchemy syntax)
    
    # Regular users see:
    # 1. Companies from their organization  
    # 2. Global companies ONLY if organization allows global data access
    if db:
        from ...core.database import Organization
        user_org = db.query(Organization).filter(Organization.id == user.organization_id).first()
        if user_org and user_org.allow_global_data_access:
            # Organization allows global access - show org + global companies
            return or_(
                CompanyModel.organization_id == user.organization_id,
                CompanyModel.organization_id.is_(None)  # Global companies
            )
        else:
            # Organization doesn't allow global access - only org companies
            return CompanyModel.organization_id == user.organization_id
    else:
        # Fallback without db access - only org companies (secure default)
        return CompanyModel.organization_id == user.organization_id

def serialize_datetime(dt):
    """Helper function to serialize datetime objects"""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    return dt

def can_user_see_prediction(user: User, prediction_user_id: str, prediction_org_id: str = None):
    """Check if user can see a specific prediction based on access rules"""
    if user.role == "super_admin":
        return True
    
    if user.role == "tenant_admin" and user.tenant_id:
        # Tenant admin can see predictions from their tenant (need org check)
        return True  # For now, allow tenant admins to see all
    
    # For regular users and org members/admins:
    # 1. They can see their own predictions
    if str(prediction_user_id) == str(user.id):
        return True
    
    # 2. If user has no organization, they can ONLY see their own predictions
    if user.organization_id is None:
        return False  # Strict: no org users can only see their own data
    
    # 3. If prediction has no organization (global), only super_admin can see others' predictions
    if prediction_org_id is None:
        return False  # Regular users can't see global predictions from others
    
    # 4. If both user and prediction are in same organization, allow
    if str(user.organization_id) == str(prediction_org_id):
        return True
    
    return False

def filter_predictions_for_user(predictions, user: User):
    """Filter predictions list based on user access permissions"""
    if user.role == "super_admin":
        return predictions
    
    filtered_predictions = []
    for pred in predictions:
        # Get prediction creator and organization info
        pred_creator_id = getattr(pred, 'created_by', None)
        pred_org_id = getattr(pred, 'organization_id', None)
        
        if can_user_see_prediction(user, pred_creator_id, pred_org_id):
            filtered_predictions.append(pred)
    
    return filtered_predictions
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
        # Check if user has access to view companies (allow all authenticated users)
        if not check_user_permissions(current_user, "user"):
            raise HTTPException(
                status_code=403, 
                detail="Authentication required to view companies"
            )
        
        # Get organization-based filter with db session for dynamic global access check
        org_filter = get_organization_filter(current_user, db)
        
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
            # Filter predictions based on user access
            filtered_annual = filter_predictions_for_user(company.annual_predictions, current_user)
            filtered_quarterly = filter_predictions_for_user(company.quarterly_predictions, current_user)
            
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
                    } for pred in filtered_annual
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
                    } for pred in filtered_quarterly
                ],
                "annual_predictions_count": len(filtered_annual),
                "quarterly_predictions_count": len(filtered_quarterly)
            }
            companies_data.append(company_data)
        
        pagination = result["pagination"]
        return PaginatedResponse(
            items=companies_data,
            total=pagination["total"],
            page=pagination["page"],
            size=pagination["limit"],  # CompanyService returns 'limit', PaginatedResponse expects 'size'
            pages=pagination["pages"]
        )
    except HTTPException:
        raise
    except Exception as e:
        # For debugging - show actual error
        import traceback
        print(f"Companies endpoint error: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, 
            detail=f"Unable to fetch companies: {str(e)}"
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
            if current_user.role != "super_admin":
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
            if (current_user.role == "super_admin" or
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
            if (current_user.role == "super_admin" or
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
    """Create a new company (requires org_admin or org_member role)"""
    try:
        # Check if user has org_admin or org_member permissions
        if not check_user_permissions(current_user, "org_member"):
            raise HTTPException(
                status_code=403, 
                detail="You need organization member or higher privileges to create companies"
            )
        
        # Ensure user belongs to an organization (except super_admin)
        if current_user.role not in ["super_admin", "tenant_admin"] and not current_user.organization_id:
            raise HTTPException(
                status_code=400,
                detail="You must belong to an organization to create companies"
            )
        
        service = CompanyService(db)
        
        # Determine organization context based on user role FIRST
        organization_id = None
        tenant_id = None
        
        if current_user.role == "super_admin":
            # Super admin can specify any org/tenant or leave global
            organization_id = getattr(company, 'organization_id', None)
            tenant_id = getattr(company, 'tenant_id', None)
        elif current_user.role == "tenant_admin":
            # Tenant admin creates for their tenant
            organization_id = getattr(company, 'organization_id', None)
            tenant_id = current_user.tenant_id
        else:
            # org_admin and org_member create for their organization
            organization_id = current_user.organization_id
            tenant_id = current_user.tenant_id
        
        # Check if company with symbol already exists IN THE SAME ORGANIZATION
        # Different organizations can have companies with same symbol
        if current_user.role == "super_admin" and organization_id is None:
            # Super admin creating global company - check global duplicates
            existing = db.query(CompanyModel).filter(
                and_(CompanyModel.symbol == company.symbol.upper(), 
                     CompanyModel.organization_id.is_(None))
            ).first()
        else:
            # Check for duplicate in specific organization
            existing = db.query(CompanyModel).filter(
                and_(CompanyModel.symbol == company.symbol.upper(), 
                     CompanyModel.organization_id == organization_id)
            ).first()
            
        if existing:
            org_context = "globally" if organization_id is None else f"in organization {organization_id}"
            raise HTTPException(
                status_code=400, 
                detail=f"A company with symbol '{company.symbol.upper()}' already exists {org_context}"
            )
        
        # Create company with proper context
        new_company = service.create_company(
            symbol=company.symbol.upper(),
            name=company.name,
            market_cap=company.market_cap,
            sector=company.sector,
            organization_id=organization_id,
            created_by=current_user.id,
            is_global=(organization_id is None)  # Global if no organization
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
        if current_user.role != "super_admin":
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