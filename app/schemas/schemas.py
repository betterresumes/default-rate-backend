from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid

class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"      
    TENANT_ADMIN = "tenant_admin"    
    ORG_ADMIN = "org_admin"          
    ORG_MEMBER = "org_member"        
    USER = "user"                    
 
class WhitelistStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class PaginatedResponse(BaseModel):
    """Generic paginated response schema."""
    items: List[dict]
    total: int
    page: int
    size: int
    pages: int

class UserBase(BaseModel):
    email: EmailStr
    username: Optional[str] = None
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    role: Optional[str] = "user"  
    first_name: Optional[str] = None  
    last_name: Optional[str] = None   
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isalpha() for c in v):
            raise ValueError('Password must contain at least one letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)
    
    @validator('new_password')
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('New password must be at least 8 characters long')
        if not any(c.isalpha() for c in v):
            raise ValueError('New password must contain at least one letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('New password must contain at least one number')
        return v

class ChangePasswordResponse(BaseModel):
    success: bool
    message: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    email: str
    username: Optional[str]
    full_name: Optional[str]
    role: str
    organization_id: Optional[str]
    tenant_id: Optional[str]
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]
    
    @validator('id', 'organization_id', 'tenant_id', pre=True)
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v
    
    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int
    skip: int
    limit: int

class UserRoleUpdate(BaseModel):
    role: Optional[UserRole] = None

class UserRoleUpdateResponse(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str]
    old_role: str
    new_role: str
    updated_by: str
    updated_at: datetime

class TenantBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    domain: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None

class TenantCreate(TenantBase):
    pass

class TenantUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    domain: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    is_active: Optional[bool] = None

class TenantResponse(BaseModel):
    id: str
    name: str
    slug: str
    domain: Optional[str]
    description: Optional[str]
    logo_url: Optional[str]
    is_active: bool
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime]
    
    @validator('id', 'created_by', pre=True)
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v
    
    class Config:
        from_attributes = True

class TenantListResponse(BaseModel):
    tenants: List[TenantResponse]
    total: int
    skip: int
    limit: int

class TenantStatsResponse(BaseModel):
    tenant_id: str
    tenant_name: str
    total_organizations: int
    active_organizations: int
    total_users: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    domain: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None

class OrganizationCreate(OrganizationBase):
    tenant_id: Optional[str] = None
    max_users: Optional[int] = Field(500, ge=1, le=10000)
    default_role: Optional[str] = "org_member"  

class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    domain: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    max_users: Optional[int] = Field(None, ge=1, le=10000)
    default_role: Optional[str] = None  
    join_enabled: Optional[bool] = None
    is_active: Optional[bool] = None
    allow_global_data_access: Optional[bool] = None  

class OrganizationResponse(BaseModel):
    id: str
    tenant_id: Optional[str]
    name: str
    slug: str
    domain: Optional[str]
    description: Optional[str]
    logo_url: Optional[str]
    max_users: int
    join_token: str
    join_enabled: bool
    default_role: str
    is_active: bool
    allow_global_data_access: bool
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime]
    join_created_at: datetime
    
    @validator('id', 'tenant_id', 'created_by', pre=True)
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v
    
    class Config:
        from_attributes = True

class OrganizationListResponse(BaseModel):
    organizations: List[OrganizationResponse]
    total: int
    skip: int
    limit: int

class JoinOrganizationRequest(BaseModel):
    join_token: str = Field(..., min_length=1)

class JoinOrganizationResponse(BaseModel):
    success: bool
    message: str
    organization_id: str
    organization_name: str
    user_role: str

class WhitelistCreate(BaseModel):
    email: EmailStr

class WhitelistResponse(BaseModel):
    id: str
    organization_id: str
    email: str
    added_by: str
    added_at: datetime
    status: str
    
    @validator('id', 'organization_id', 'added_by', pre=True)
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v
    
    class Config:
        from_attributes = True

class WhitelistListResponse(BaseModel):
    whitelist: List[WhitelistResponse]
    total: int
    skip: int
    limit: int

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class TokenData(BaseModel):
    user_id: Optional[str] = None

class CompanyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    symbol: Optional[str] = Field(None, max_length=20)
    exchange: Optional[str] = Field(None, max_length=50)
    sector: Optional[str] = Field(None, max_length=100)
    industry: Optional[str] = Field(None, max_length=100)
    market_cap: Optional[float] = Field(None, ge=0)
    description: Optional[str] = None

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    symbol: Optional[str] = Field(None, max_length=20)
    exchange: Optional[str] = Field(None, max_length=50)
    sector: Optional[str] = Field(None, max_length=100)
    industry: Optional[str] = Field(None, max_length=100)
    market_cap: Optional[float] = Field(None, ge=0)
    description: Optional[str] = None

class CompanyResponse(BaseModel):
    id: str
    organization_id: Optional[str]
    name: str
    symbol: Optional[str]
    exchange: Optional[str]
    sector: Optional[str]
    industry: Optional[str]
    market_cap: Optional[float]
    description: Optional[str]
    created_by: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    
    @validator('id', 'organization_id', 'created_by', pre=True)
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v
    
    class Config:
        from_attributes = True

class CompanyListResponse(BaseModel):
    companies: List[CompanyResponse]
    total: int
    skip: int
    limit: int

class PredictionRequest(BaseModel):
    """Base prediction request schema for backward compatibility"""
    company_name: str = Field(..., min_length=1, max_length=255)
    revenue: float = Field(..., gt=0)
    expenses: float = Field(..., ge=0)
    assets: float = Field(..., gt=0)
    liabilities: float = Field(..., ge=0)
    year: int = Field(..., ge=2020, le=2030)

class AnnualPredictionRequest(BaseModel):
    """Annual prediction with required company data and 5 ratios"""
    company_symbol: str = Field(..., min_length=1, max_length=20)
    company_name: str = Field(..., min_length=1, max_length=255)
    market_cap: float = Field(..., gt=0, description="Market cap in millions of dollars")
    sector: str = Field(..., min_length=1, max_length=100)
    
    reporting_year: str = Field(..., pattern=r'^\d{4}$')
    reporting_quarter: Optional[str] = Field(None, pattern=r'^Q[1-4]$', description="Optional quarter (Q1, Q2, Q3, Q4)")
    
    long_term_debt_to_total_capital: float = Field(..., ge=0, le=100)
    total_debt_to_ebitda: float = Field(..., ge=0)
    net_income_margin: float = Field(..., ge=-100, le=100)
    ebit_to_interest_expense: float = Field(..., ge=0)
    return_on_assets: float = Field(..., ge=-100, le=100)

class QuarterlyPredictionRequest(BaseModel):
    """Quarterly prediction with required company data and 4 ratios"""
    company_symbol: str = Field(..., min_length=1, max_length=20)
    company_name: str = Field(..., min_length=1, max_length=255)
    market_cap: float = Field(..., gt=0, description="Market cap in millions of dollars")
    sector: str = Field(..., min_length=1, max_length=100)
    
    reporting_year: str = Field(..., pattern=r'^\d{4}$')
    reporting_quarter: str = Field(..., pattern=r'^(Q[1-4]|[1-4])$')
    
    total_debt_to_ebitda: float = Field(..., ge=0)
    sga_margin: float = Field(..., ge=-100, le=100)
    long_term_debt_to_total_capital: float = Field(..., ge=0, le=100)
    return_on_capital: float = Field(..., ge=-100, le=100)

class PredictionBase(BaseModel):
    company_id: str
    reporting_year: str = Field(..., pattern=r'^\d{4}$')
    reporting_quarter: Optional[str] = Field(None, pattern=r'^(Q[1-4]|[1-4])$')

class AnnualPredictionCreate(PredictionBase):
    long_term_debt_to_total_capital: float = Field(..., ge=0, le=100)
    total_debt_to_ebitda: float = Field(..., ge=0)
    net_income_margin: float = Field(..., ge=-100, le=100)
    ebit_to_interest_expense: float = Field(..., ge=0)
    return_on_assets: float = Field(..., ge=-100, le=100)

class QuarterlyPredictionCreate(PredictionBase):
    total_debt_to_ebitda: float = Field(..., ge=0)
    sga_margin: float = Field(..., ge=-100, le=100)
    long_term_debt_to_total_capital: float = Field(..., ge=0, le=100)
    return_on_capital: float = Field(..., ge=-100, le=100)

class UnifiedPredictionRequest(BaseModel):
    """Unified prediction request that can handle both annual and quarterly"""
    company_symbol: str = Field(..., min_length=1, max_length=20)
    company_name: str = Field(..., min_length=1, max_length=255)
    market_cap: float = Field(..., gt=0, description="Market cap in millions of dollars")
    sector: str = Field(..., min_length=1, max_length=100)
    
    reporting_year: str = Field(..., pattern=r'^\d{4}$')
    reporting_quarter: Optional[str] = Field(None, pattern=r'^(Q[1-4]|[1-4])$', description="Optional - if provided, creates quarterly prediction")
    
    long_term_debt_to_total_capital: Optional[float] = Field(None, ge=0, le=100)
    total_debt_to_ebitda: Optional[float] = Field(None, ge=0)
    net_income_margin: Optional[float] = Field(None, ge=-100, le=100)
    ebit_to_interest_expense: Optional[float] = Field(None, ge=0)
    return_on_assets: Optional[float] = Field(None, ge=-100, le=100)
    
    sga_margin: Optional[float] = Field(None, ge=-100, le=100)
    return_on_capital: Optional[float] = Field(None, ge=-100, le=100)

class PredictionResponse(BaseModel):
    id: str
    company_id: str
    organization_id: Optional[str]
    reporting_year: str
    reporting_quarter: str
    logistic_probability: float
    gbm_probability: float
    ensemble_probability: float
    risk_level: str
    confidence: float
    predicted_at: datetime
    created_by: Optional[str]
    created_at: datetime
    
    @validator('id', 'company_id', 'organization_id', 'created_by', pre=True)
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v
    
    class Config:
        from_attributes = True

class PredictionListResponse(BaseModel):
    predictions: List[PredictionResponse]
    total: int
    skip: int
    limit: int

class BulkUploadResponse(BaseModel):
    success: bool
    message: str
    total_processed: int
    successful: int
    failed: int
    errors: List[dict] = []

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    message: str
    errors: Optional[List[dict]] = None

class OrgAdminInfo(BaseModel):
    """Schema for organization admin information."""
    user_id: str
    email: str
    full_name: Optional[str]
    username: Optional[str]
    is_active: bool
    assigned_at: datetime
    
    @validator('user_id', pre=True)
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v
    
    class Config:
        from_attributes = True

class OrganizationDetailedResponse(BaseModel):
    """Enhanced organization response with admin information."""
    id: str
    tenant_id: Optional[str]
    name: str
    slug: str
    domain: Optional[str]
    description: Optional[str]
    logo_url: Optional[str]
    max_users: int
    join_token: str
    join_enabled: bool
    default_role: str
    is_active: bool
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime]
    join_created_at: datetime
    
    org_admins: List[OrgAdminInfo] = []
    total_users: int = 0
    active_users: int = 0
    admin_count: int = 0
    
    @validator('id', 'tenant_id', 'created_by', pre=True)
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v
    
    class Config:
        from_attributes = True

class TenantAdminInfo(BaseModel):
    """Tenant admin user information"""
    id: str
    email: str
    username: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]
    
    @validator('id', pre=True)
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v
    
    class Config:
        from_attributes = True

class OrganizationAdminInfo(BaseModel):
    """Organization admin information"""
    id: str
    email: str
    username: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    
    @validator('id', pre=True)
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v
    
    class Config:
        from_attributes = True

class OrganizationUserInfo(BaseModel):
    """Organization member information"""
    id: str
    email: str
    username: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    
    @validator('id', pre=True)
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v
    
    class Config:
        from_attributes = True

class DetailedOrganizationInfo(BaseModel):
    """Detailed organization information with users"""
    id: str
    name: str
    slug: str
    description: Optional[str]
    is_active: bool
    join_token: str
    join_enabled: bool
    default_role: str
    max_users: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    # Users in this organization
    admin: Optional[OrganizationAdminInfo] = None
    members: List[OrganizationUserInfo] = []
    total_users: int = 0
    
    @validator('id', pre=True)
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v
    
    class Config:
        from_attributes = True

class ComprehensiveTenantResponse(BaseModel):
    """Comprehensive tenant information for super admin"""
    id: str
    name: str
    slug: str
    domain: Optional[str]
    description: Optional[str]
    logo_url: Optional[str]
    is_active: bool
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime]
    
    tenant_admins: List[TenantAdminInfo] = []
    total_tenant_admins: int = 0
    
    organizations: List[DetailedOrganizationInfo] = []
    total_organizations: int = 0
    active_organizations: int = 0
    
    total_users_in_tenant: int = 0
    total_active_users: int = 0
    
    @validator('id', 'created_by', pre=True)
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v
    
    class Config:
        from_attributes = True

class ComprehensiveTenantListResponse(BaseModel):
    """List response with comprehensive tenant information"""
    tenants: List[ComprehensiveTenantResponse]
    total: int
    skip: int
    limit: int
    
    # Summary statistics
    total_tenant_admins: int = 0
    total_organizations: int = 0
    total_users: int = 0

class TenantInfo(BaseModel):
    """Basic tenant information for organization responses"""
    id: str
    name: str
    slug: str
    domain: Optional[str]
    
    @validator('id', pre=True)
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v

class OrganizationMemberInfo(BaseModel):
    """Organization member information"""
    id: str
    tenant_id: Optional[str]
    organization_id: Optional[str]
    email: str
    username: Optional[str]
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    
    @validator('id', pre=True)
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v

class EnhancedTenantInfo(BaseModel):
    """Enhanced tenant information with admin details"""
    id: str
    name: str
    description: Optional[str]
    tenant_code: str
    logo_url: Optional[str]
    is_active: bool
    created_at: datetime
    # Tenant admin details
    tenant_admins: List[OrganizationMemberInfo] = []
    total_tenant_admins: int = 0
    
    @validator('id', pre=True)
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v

class EnhancedOrganizationResponse(BaseModel):
    """Enhanced organization response with tenant, admin, and member details"""
    id: str
    tenant_id: Optional[str]
    name: str
    slug: str
    domain: Optional[str]
    description: Optional[str]
    logo_url: Optional[str]
    max_users: int
    join_token: str
    join_enabled: bool
    default_role: str
    is_active: bool
    created_by: str
    created_at: datetime
    updated_at: Optional[datetime]
    join_created_at: datetime
    
    tenant: Optional[EnhancedTenantInfo] = None
    org_admin: Optional[OrganizationMemberInfo] = None
    members: List[OrganizationMemberInfo] = []
    total_users: int = 0
    active_users: int = 0
    total_members: int = 0
    active_members: int = 0
    
    @validator('id', 'tenant_id', 'created_by', pre=True)
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v
    
    class Config:
        from_attributes = True

class EnhancedOrganizationListResponse(BaseModel):
    """Enhanced organization list response"""
    organizations: List[EnhancedOrganizationResponse]
    total: int
    skip: int
    limit: int
    total_admins: int = 0
    total_members: int = 0
    total_users: int = 0
