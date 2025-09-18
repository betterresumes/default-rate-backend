from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid

# ========================================
# ENUMS
# ========================================

class GlobalRole(str, Enum):
    USER = "user"
    TENANT_ADMIN = "tenant_admin"
    SUPER_ADMIN = "super_admin"

class OrganizationRole(str, Enum):
    USER = "user"
    MEMBER = "member"
    ADMIN = "admin"

class WhitelistStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

# ========================================
# GENERIC RESPONSE SCHEMAS
# ========================================

class PaginatedResponse(BaseModel):
    """Generic paginated response schema."""
    items: List[dict]
    total: int
    page: int
    size: int
    pages: int

# ========================================
# USER SCHEMAS
# ========================================

class UserBase(BaseModel):
    email: EmailStr
    username: Optional[str] = None
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    
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

class UserUpdate(BaseModel):
    username: Optional[str] = None
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    email: str
    username: Optional[str]
    full_name: Optional[str]
    global_role: str
    organization_role: str
    organization_id: Optional[str]
    tenant_id: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime]
    
    @validator('id', 'organization_id', 'tenant_id', pre=True)
    def convert_uuid_to_str(cls, v):
        if v is not None:
            return str(v)
        return v
    
    class Config:
        from_attributes = True
        from_attributes = True

class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int
    skip: int
    limit: int

class UserRoleUpdate(BaseModel):
    global_role: Optional[GlobalRole] = None
    organization_role: Optional[OrganizationRole] = None

class UserRoleUpdateResponse(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str]
    old_global_role: str
    new_global_role: str
    old_organization_role: str
    new_organization_role: str
    updated_by: str
    updated_at: datetime

# ========================================
# TENANT SCHEMAS
# ========================================

class TenantBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    domain: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None

class TenantCreate(TenantBase):
    max_organizations: Optional[int] = Field(50, ge=1, le=1000)

class TenantUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    domain: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    max_organizations: Optional[int] = Field(None, ge=1, le=1000)
    is_active: Optional[bool] = None

class TenantResponse(BaseModel):
    id: str
    name: str
    slug: str
    domain: Optional[str]
    description: Optional[str]
    logo_url: Optional[str]
    max_organizations: int
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
    max_organizations: int
    created_at: datetime

# ========================================
# ORGANIZATION SCHEMAS
# ========================================

class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    domain: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None

class OrganizationCreate(OrganizationBase):
    tenant_id: Optional[str] = None
    max_users: Optional[int] = Field(100, ge=1, le=10000)
    default_role: Optional[OrganizationRole] = OrganizationRole.USER

class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    domain: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    max_users: Optional[int] = Field(None, ge=1, le=10000)
    default_role: Optional[OrganizationRole] = None
    join_enabled: Optional[bool] = None
    is_active: Optional[bool] = None

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
        from_attributes = True

class OrganizationListResponse(BaseModel):
    organizations: List[OrganizationResponse]
    total: int
    skip: int
    limit: int

# ========================================
# ORGANIZATION JOINING SCHEMAS
# ========================================

class JoinOrganizationRequest(BaseModel):
    join_token: str = Field(..., min_length=1)

class JoinOrganizationResponse(BaseModel):
    success: bool
    message: str
    organization_id: str
    organization_name: str
    user_role: str

# ========================================
# WHITELIST SCHEMAS
# ========================================

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
        from_attributes = True

class WhitelistListResponse(BaseModel):
    whitelist: List[WhitelistResponse]
    total: int
    skip: int
    limit: int

# ========================================
# AUTHENTICATION SCHEMAS
# ========================================

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class TokenData(BaseModel):
    user_id: Optional[str] = None

# ========================================
# COMPANY SCHEMAS (for reference - update existing)
# ========================================

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
        from_attributes = True

class CompanyListResponse(BaseModel):
    companies: List[CompanyResponse]
    total: int
    skip: int
    limit: int

# ========================================
# PREDICTION SCHEMAS (for reference - update existing)
# ========================================

class PredictionBase(BaseModel):
    company_id: str
    reporting_year: str = Field(..., pattern=r'^\d{4}$')
    reporting_quarter: str = Field(..., pattern=r'^(Q[1-4]|[1-4])$')

class QuarterlyPredictionCreate(PredictionBase):
    total_debt_to_ebitda: float = Field(..., ge=0)
    sga_margin: float = Field(..., ge=-100, le=100)
    long_term_debt_to_total_capital: float = Field(..., ge=0, le=100)
    return_on_capital: float = Field(..., ge=-100, le=100)

class AnnualPredictionCreate(PredictionBase):
    long_term_debt_to_total_capital: float = Field(..., ge=0, le=100)
    total_debt_to_ebitda: float = Field(..., ge=0)
    net_income_margin: float = Field(..., ge=-100, le=100)
    ebit_to_interest_expense: float = Field(..., ge=0)
    return_on_assets: float = Field(..., ge=-100, le=100)

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
        from_attributes = True

class PredictionListResponse(BaseModel):
    predictions: List[PredictionResponse]
    total: int
    skip: int
    limit: int

# ========================================
# BULK UPLOAD SCHEMAS
# ========================================

class BulkUploadResponse(BaseModel):
    success: bool
    message: str
    total_processed: int
    successful: int
    failed: int
    errors: List[dict] = []

# ========================================
# ADDITIONAL PREDICTION SCHEMAS
# ========================================

class PredictionRequest(BaseModel):
    """Base prediction request schema."""
    company_name: str = Field(..., min_length=1, max_length=255)
    revenue: float = Field(..., gt=0)
    expenses: float = Field(..., ge=0)
    assets: float = Field(..., gt=0)
    liabilities: float = Field(..., ge=0)
    year: int = Field(..., ge=2020, le=2030)

class QuarterlyPredictionRequest(BaseModel):
    """Request schema for quarterly predictions."""
    company_name: str = Field(..., min_length=1, max_length=255)
    revenue: float = Field(..., gt=0)
    expenses: float = Field(..., ge=0)
    assets: float = Field(..., gt=0)
    liabilities: float = Field(..., ge=0)
    quarter: int = Field(..., ge=1, le=4)
    year: int = Field(..., ge=2020, le=2030)

class AnnualPredictionRequest(BaseModel):
    """Request schema for annual predictions."""
    company_name: str = Field(..., min_length=1, max_length=255)
    revenue: float = Field(..., gt=0)
    expenses: float = Field(..., ge=0)
    assets: float = Field(..., gt=0)
    liabilities: float = Field(..., ge=0)
    year: int = Field(..., ge=2020, le=2030)

class UnifiedPredictionRequest(BaseModel):
    """Unified prediction request for both annual and quarterly."""
    company_name: str = Field(..., min_length=1, max_length=255)
    revenue: float = Field(..., gt=0)
    expenses: float = Field(..., ge=0)
    assets: float = Field(..., gt=0)
    liabilities: float = Field(..., ge=0)
    year: int = Field(..., ge=2020, le=2030)
    quarter: Optional[int] = Field(None, ge=1, le=4)

class CompanyWithPredictionsResponse(BaseModel):
    """Company with its predictions."""
    company: CompanyResponse
    annual_predictions: List[PredictionResponse] = []
    quarterly_predictions: List[PredictionResponse] = []

class BulkPredictionItem(BaseModel):
    """Single item in bulk prediction."""
    company_name: str
    revenue: float
    expenses: float
    assets: float
    liabilities: float
    year: int
    prediction_probability: Optional[float] = None
    prediction_class: Optional[str] = None
    status: str = "pending"
    error_message: Optional[str] = None

class BulkPredictionResponse(BaseModel):
    """Response for bulk predictions."""
    job_id: str
    status: str = "started"
    total_companies: int
    processed: int = 0
    successful: int = 0
    failed: int = 0
    items: List[BulkPredictionItem] = []

class QuarterlyBulkPredictionItem(BaseModel):
    """Single item in quarterly bulk prediction."""
    company_name: str
    revenue: float
    expenses: float
    assets: float
    liabilities: float
    quarter: int
    year: int
    prediction_probability: Optional[float] = None
    prediction_class: Optional[str] = None
    status: str = "pending"
    error_message: Optional[str] = None

class QuarterlyBulkPredictionResponse(BaseModel):
    """Response for quarterly bulk predictions."""
    job_id: str
    status: str = "started"
    total_companies: int
    processed: int = 0
    successful: int = 0
    failed: int = 0
    items: List[QuarterlyBulkPredictionItem] = []

class PredictionUpdateRequest(BaseModel):
    """Request to update prediction."""
    prediction_probability: Optional[float] = None
    prediction_class: Optional[str] = None
    notes: Optional[str] = None

class BulkJobResponse(BaseModel):
    """Job response for bulk operations."""
    job_id: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    total_items: int
    processed_items: int
    successful_items: int
    failed_items: int
    progress_percentage: float

class QuarterlyBulkJobResponse(BaseModel):
    """Job response for quarterly bulk operations."""
    job_id: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    total_items: int
    processed_items: int
    successful_items: int
    failed_items: int
    progress_percentage: float

class JobStatusResponse(BaseModel):
    """General job status response."""
    job_id: str
    status: str
    progress: float
    total: int
    completed: int
    errors: List[str] = []

# ========================================
# ERROR SCHEMAS
# ========================================

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    message: str
    errors: Optional[List[dict]] = None
