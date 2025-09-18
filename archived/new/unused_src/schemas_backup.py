from pydantic import BaseModel, Field, EmailStr, validator, root_validator
from typing import Optional, List, Literal, Any
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from enum import Enum

# ========================
# STANDARDIZED API RESPONSES
# ========================

class APIResponse(BaseModel):
    """Standardized API response format"""
    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[str] = None
    errors: Optional[List[dict]] = None

class ValidationError(BaseModel):
    field: str
    message: str

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    message: str
    field: Optional[str] = None
    details: Optional[str] = None

# ========================
# AUTHENTICATION RESPONSES
# ========================

class LoginResponse(BaseModel):
    success: bool
    message: str
    access_token: Optional[str] = None
    token_type: Optional[str] = "bearer"
    user: Optional[dict] = None

class LogoutResponse(BaseModel):
    success: bool
    message: str

# Enums for type safety
class GlobalRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin" 
    USER = "user"

class OrganizationRole(str, Enum):
    ADMIN = "admin"
    USER = "user"

class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class OrganizationMemberStatus(str, Enum):
    ACTIVE = "active"
    PENDING = "pending" 
    REJECTED = "rejected"

class PendingMemberStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

# ========================
# ORGANIZATION SCHEMAS
# ========================

class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    settings: Optional[dict] = {}

class OrganizationCreate(OrganizationBase):
    settings: Optional[dict] = {}

class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    settings: Optional[dict] = None

class Organization(OrganizationBase):
    id: UUID
    created_by: Optional[UUID]
    member_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class OrganizationResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    settings: Optional[dict] = {}
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    user_count: int = 0
    admin_count: int = 0

    class Config:
        from_attributes = True

# ========================
# INVITATION SCHEMAS  
# ========================

class InvitationBase(BaseModel):
    email: EmailStr
    organization_role: OrganizationRole = OrganizationRole.USER  # Default to user role

class InvitationCreate(InvitationBase):
    pass

class AcceptInvitationRequest(BaseModel):
    invitation_token: str
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = None
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class Invitation(InvitationBase):
    id: UUID
    organization_id: UUID
    invited_by: UUID
    status: InvitationStatus
    token: str
    expires_at: datetime
    created_at: datetime
    accepted_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class InvitationResponse(BaseModel):
    id: str
    organization_id: str
    organization_name: str
    email: str
    organization_role: str
    invited_by: str
    status: str
    created_at: datetime
    expires_at: datetime

    class Config:
        from_attributes = True

# ========================
# ORGANIZATION CODE SCHEMAS
# ========================

class OrganizationCodeResponse(BaseModel):
    organization_code: str
    code_enabled: bool
    code_created_at: datetime
    members_count: int
    pending_members_count: int
    share_instructions: str = "Share this code with team members during registration"

class RegenerateCodeResponse(BaseModel):
    new_code: str
    message: str
    code_enabled: bool

class JoinWithCodeRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=1, max_length=100)
    organization_code: str = Field(..., min_length=8, max_length=8)
    requested_role: OrganizationRole = OrganizationRole.USER

    @validator('organization_code')
    def validate_code(cls, v):
        return v.upper().strip()

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

# ========================
# PENDING MEMBER SCHEMAS
# ========================

class PendingMemberResponse(BaseModel):
    id: str
    email: str
    full_name: str
    requested_role: str
    organization_code_used: str
    status: str
    requested_at: datetime
    user_id: str

    class Config:
        from_attributes = True

class PendingMemberAction(BaseModel):
    action: Literal["approve", "reject"]
    role: Optional[OrganizationRole] = None  # Can change role during approval
    rejection_reason: Optional[str] = None

class PendingMemberActionResponse(BaseModel):
    success: bool
    message: str
    member_id: str
    action: str
    new_status: str

# ========================
# REGISTRATION WITH ORG CODE SCHEMAS
# ========================

class RegisterWithOrgCodeResponse(BaseModel):
    success: bool
    message: str
    access_token: str
    token_type: str = "bearer"
    user: dict
    organization_status: str  # "active", "pending"
    organization: Optional[dict] = None
    pending_approval: bool = False

# ========================
# ORGANIZATION SCHEMAS
# ========================

class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    settings: Optional[dict] = {}

class OrganizationCreate(OrganizationBase):
    settings: Optional[dict] = {}

class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    settings: Optional[dict] = None

class Organization(OrganizationBase):
    id: UUID
    created_by: Optional[UUID]
    member_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class OrganizationResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    settings: Optional[dict] = {}
    created_by: Optional[str]
    created_at: datetime
    updated_at: datetime
    user_count: int = 0
    admin_count: int = 0

    class Config:
        from_attributes = True

# ========================
# INVITATION SCHEMAS  
# ========================

class InvitationBase(BaseModel):
    email: EmailStr
    organization_role: OrganizationRole = OrganizationRole.USER  # Default to user role

class InvitationCreate(InvitationBase):
    pass

class AcceptInvitationRequest(BaseModel):
    invitation_token: str
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = None
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class Invitation(InvitationBase):
    id: UUID
    organization_id: UUID
    invited_by: UUID
    status: InvitationStatus
    token: str
    expires_at: datetime
    created_at: datetime
    accepted_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class InvitationResponse(BaseModel):
    id: str
    organization_id: str
    organization_name: str
    email: str
    organization_role: str
    invited_by: str
    status: str
    created_at: datetime
    expires_at: datetime

    class Config:
        from_attributes = True

# ========================
# USER SCHEMAS
# ========================

class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)
    confirm_password: str = Field(..., min_length=8, max_length=100)
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

# FastAPI-Users compatible schemas
class UserRead(UserBase):
    id: UUID
    organization_id: Optional[UUID] = None
    organization_role: OrganizationRole = OrganizationRole.USER
    global_role: GlobalRole = GlobalRole.USER
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserCreateFastAPIUsers(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = None
    password: str = Field(..., min_length=8, max_length=100)
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    is_verified: Optional[bool] = False

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = None

class UserInDB(UserBase):
    id: UUID
    organization_id: Optional[UUID]
    organization_role: OrganizationRole
    global_role: GlobalRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserWithOrganization(UserInDB):
    organization: Optional[Organization] = None

    class Config:
        from_attributes = True

class UserInOrganization(BaseModel):
    id: str
    email: str
    username: str
    full_name: Optional[str]
    organization_role: Optional[str]
    global_role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

# ========================
# AUTH & TOKEN SCHEMAS
# ========================

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: UserInDB

class TokenData(BaseModel):
    user_id: Optional[UUID] = None

class OTPVerification(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)

class OTPRequest(BaseModel):
    email: EmailStr

class PasswordReset(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8, max_length=100)
    confirm_password: str = Field(..., min_length=8, max_length=100)
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v

class AuthResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None


# ========================
# COMPANY SCHEMAS
# ========================

class CompanyBase(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    name: str = Field(..., min_length=1, max_length=200)
    market_cap: float = Field(..., ge=0, description="Market capitalization in USD")
    sector: str = Field(..., min_length=1, max_length=100, description="Company sector/industry")

class CompanyCreate(CompanyBase):
    """Schema for creating a new company"""
    is_global: bool = Field(False, description="Whether this company is globally accessible")
    # Optional fields for bulk upload with predictions
    reporting_year: Optional[str] = Field(None, description="Reporting year (e.g., '2024')")
    reporting_quarter: Optional[str] = Field(None, description="Reporting quarter (e.g., 'Q4')")
    long_term_debt_to_total_capital: Optional[float] = Field(None, description="Long-term debt / total capital (%)")
    total_debt_to_ebitda: Optional[float] = Field(None, description="Total debt / EBITDA")
    net_income_margin: Optional[float] = Field(None, description="Net income margin (%)")
    ebit_to_interest_expense: Optional[float] = Field(None, description="EBIT / interest expense")
    return_on_assets: Optional[float] = Field(None, description="Return on assets (%)")

class CompanyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    market_cap: Optional[float] = Field(None, ge=0)
    sector: Optional[str] = Field(None, min_length=1, max_length=100)

class Company(CompanyBase):
    id: UUID
    organization_id: Optional[UUID]
    is_global: bool
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ========================
# PREDICTION SCHEMAS
# ========================

class AnnualPredictionBase(BaseModel):
    reporting_year: str = Field(..., description="Reporting year (e.g., '2024')")
    long_term_debt_to_total_capital: float = Field(..., description="Long-term debt / total capital (%)")
    total_debt_to_ebitda: float = Field(..., description="Total debt / EBITDA")
    net_income_margin: float = Field(..., description="Net income margin (%)")
    ebit_to_interest_expense: float = Field(..., description="EBIT / interest expense")
    return_on_assets: float = Field(..., description="Return on assets (%)")
    risk_level: str = Field(..., description="Risk level (LOW, MEDIUM, HIGH)")
    confidence: float = Field(..., ge=0, le=1, description="Prediction confidence (0-1)")
    probability: float = Field(..., ge=0, le=1, description="Default probability (0-1)")

class AnnualPredictionCreate(AnnualPredictionBase):
    company_id: UUID

class AnnualPrediction(AnnualPredictionBase):
    id: UUID
    company_id: UUID
    organization_id: Optional[UUID]
    created_by: Optional[UUID]
    predicted_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class QuarterlyPredictionBase(BaseModel):
    reporting_year: str = Field(..., description="Reporting year (e.g., '2024')")
    reporting_quarter: str = Field(..., description="Reporting quarter (e.g., 'Q4')")
    total_debt_to_ebitda: float = Field(..., description="Total debt / EBITDA")
    sga_margin: float = Field(..., description="SG&A margin (%)")
    long_term_debt_to_total_capital: float = Field(..., description="Long-term debt / total capital (%)")
    return_on_capital: float = Field(..., description="Return on capital (%)")
    risk_level: str = Field(..., description="Risk level (LOW, MEDIUM, HIGH)")
    confidence: float = Field(..., ge=0, le=1, description="Prediction confidence (0-1)")

class QuarterlyPredictionCreate(QuarterlyPredictionBase):
    company_id: UUID
    logistic_probability: float = Field(..., ge=0, le=1, description="Logistic model probability")
    gbm_probability: float = Field(..., ge=0, le=1, description="GBM model probability")
    ensemble_probability: float = Field(..., ge=0, le=1, description="Ensemble probability")

class QuarterlyPrediction(QuarterlyPredictionBase):
    id: UUID
    company_id: UUID
    organization_id: Optional[UUID]
    created_by: Optional[UUID]
    logistic_probability: float
    gbm_probability: float
    ensemble_probability: float
    predicted_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ========================
# REQUEST/RESPONSE SCHEMAS
# ========================


# Request schemas for creating predictions
class AnnualPredictionRequest(BaseModel):
    stock_symbol: str = Field(..., min_length=1, max_length=10)
    company_name: str = Field(..., min_length=1, max_length=200)
    market_cap: float = Field(..., ge=0, description="Market capitalization in USD")
    sector: str = Field(..., min_length=1, max_length=100, description="Company sector/industry")
    reporting_year: str = Field(..., description="Reporting year (e.g., '2024')")
    
    # Annual model features (all required)
    long_term_debt_to_total_capital: float = Field(..., description="Long-term debt / total capital (%)")
    total_debt_to_ebitda: float = Field(..., description="Total debt / EBITDA")
    net_income_margin: float = Field(..., description="Net income margin (%)")
    ebit_to_interest_expense: float = Field(..., description="EBIT / interest expense")
    return_on_assets: float = Field(..., description="Return on assets (%)")

class QuarterlyPredictionRequest(BaseModel):
    stock_symbol: str = Field(..., min_length=1, max_length=10)
    company_name: str = Field(..., min_length=1, max_length=200)
    market_cap: float = Field(..., ge=0, description="Market capitalization in USD")
    sector: str = Field(..., min_length=1, max_length=100, description="Company sector/industry")
    reporting_year: str = Field(..., description="Reporting year (e.g., '2024')")
    reporting_quarter: str = Field(..., description="Reporting quarter (e.g., 'Q4')")
    
    # Quarterly model features (all required)
    total_debt_to_ebitda: float = Field(..., description="Total debt / EBITDA")
    sga_margin: float = Field(..., description="SG&A margin (%)")
    long_term_debt_to_total_capital: float = Field(..., description="Long-term debt / total capital (%)")
    return_on_capital: float = Field(..., description="Return on capital (%)")

# Response schemas with company and prediction data
class CompanyWithPredictionsResponse(BaseModel):
    company: Company
    annual_predictions: List[AnnualPrediction] = []
    quarterly_predictions: List[QuarterlyPrediction] = []


# Unified prediction request that handles both annual and quarterly
class UnifiedPredictionRequest(BaseModel):
    """Unified prediction request for both annual and quarterly models"""
    stock_symbol: str = Field(..., min_length=1, max_length=10)
    company_name: str = Field(..., min_length=1, max_length=200)
    market_cap: float = Field(..., ge=0, description="Market capitalization in USD")
    sector: str = Field(..., min_length=1, max_length=100, description="Company sector/industry")
    reporting_year: str = Field(..., description="Reporting year (e.g., '2024')")
    reporting_quarter: Optional[str] = Field(None, description="Reporting quarter (e.g., 'Q4')")
    
    # Prediction type - determines which model to use
    prediction_type: str = Field(..., pattern="^(annual|quarterly)$", description="Type of prediction: 'annual' or 'quarterly'")
    
    # Annual model features (required when prediction_type='annual')
    long_term_debt_to_total_capital: Optional[float] = Field(None, description="Long-term debt / total capital (%)")
    total_debt_to_ebitda: Optional[float] = Field(None, description="Total debt / EBITDA")
    net_income_margin: Optional[float] = Field(None, description="Net income margin (%)")
    ebit_to_interest_expense: Optional[float] = Field(None, description="EBIT / interest expense")
    return_on_assets: Optional[float] = Field(None, description="Return on assets (%)")
    
    # Quarterly model features (required when prediction_type='quarterly')
    sga_margin: Optional[float] = Field(None, description="SG&A margin (%)")
    return_on_capital: Optional[float] = Field(None, description="Return on capital (%)")
    
    @root_validator(skip_on_failure=True)
    def validate_required_fields(cls, values):
        """Validate that required fields are provided based on prediction_type"""
        prediction_type = values.get('prediction_type')
        
        if prediction_type == 'annual':
            required_fields = ['long_term_debt_to_total_capital', 'total_debt_to_ebitda', 
                             'net_income_margin', 'ebit_to_interest_expense', 'return_on_assets']
            for field in required_fields:
                if values.get(field) is None:
                    raise ValueError(f'{field} is required for annual predictions')
        
        elif prediction_type == 'quarterly':
            quarterly_fields = ['total_debt_to_ebitda', 'sga_margin', 
                              'long_term_debt_to_total_capital', 'return_on_capital']
            for field in quarterly_fields:
                if values.get(field) is None:
                    raise ValueError(f'{field} is required for quarterly predictions')
        
        return values


class PredictionResponse(BaseModel):
    success: bool
    message: str
    company: dict


class PaginatedResponse(BaseModel):
    success: bool
    data: dict
    pagination: Optional[dict] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[str] = None


class BulkPredictionItem(BaseModel):
    stock_symbol: str
    company_name: str
    sector: Optional[str] = None
    market_cap: Optional[float] = None
    prediction: dict
    status: str 
    error_message: Optional[str] = None


class BulkPredictionResponse(BaseModel):
    success: bool
    message: str
    total_companies: int
    successful_predictions: int
    failed_predictions: int
    results: List[BulkPredictionItem]
    processing_time: float


class BulkJobResponse(BaseModel):
    success: bool
    message: str
    job_id: str
    status: str
    filename: str
    estimated_processing_time: Optional[str] = None


class JobStatusResponse(BaseModel):
    success: bool
    job_id: str
    status: str 
    message: str
    progress: Optional[dict] = None
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: Optional[float] = None
    completed_at: Optional[float] = None


class PredictionUpdateRequest(BaseModel):
    # Company basic info
    company_name: Optional[str] = Field(None, min_length=1, max_length=200)
    market_cap: Optional[float] = Field(None, ge=0, description="Market capitalization in USD")
    sector: Optional[str] = Field(None, min_length=1, max_length=100, description="Company sector/industry")
    
    # Prediction update fields
    prediction_type: Optional[str] = Field(None, description="Type of prediction to update: 'annual' or 'quarterly'")
    reporting_year: Optional[str] = Field(None, description="Reporting year (e.g., '2024')")
    reporting_quarter: Optional[str] = Field(None, description="Reporting quarter (e.g., 'Q1') - required for quarterly predictions")
    
    # Annual prediction financial ratios
    long_term_debt_to_total_capital: Optional[float] = Field(None, description="Long-term debt / total capital")
    total_debt_to_ebitda: Optional[float] = Field(None, description="Total debt / EBITDA")
    net_income_margin: Optional[float] = Field(None, description="Net income margin")
    ebit_to_interest_expense: Optional[float] = Field(None, description="EBIT / interest expense")
    return_on_assets: Optional[float] = Field(None, description="Return on assets")
    
    # Quarterly prediction financial ratios
    sga_margin: Optional[float] = Field(None, description="SG&A margin")
    return_on_capital: Optional[float] = Field(None, description="Return on capital")

class DatabaseResetRequest(BaseModel):
    table_name: Optional[str] = Field(None, description="Specific table to reset: 'companies', 'annual_predictions', 'quarterly_predictions', 'users', 'otp_tokens', 'user_sessions' (if not provided, resets all tables)")
    confirm_reset: bool = Field(..., description="Confirmation flag to prevent accidental resets")


class DatabaseResetResponse(BaseModel):
    success: bool
    message: str
    tables_reset: List[str]
    affected_records: Optional[int] = None

# Legacy prediction request for backward compatibility
class PredictionRequest(BaseModel):
    """Legacy schema for backward compatibility - defaults to annual prediction"""
    stock_symbol: str = Field(..., min_length=1, max_length=10)
    company_name: str = Field(..., min_length=1, max_length=200)
    market_cap: float = Field(..., ge=0, description="Market capitalization in USD")
    sector: str = Field(..., min_length=1, max_length=100, description="Company sector/industry")
    reporting_year: Optional[str] = Field(None, description="Reporting year (e.g., '2024')")
    reporting_quarter: Optional[str] = Field(None, description="Reporting quarter (e.g., 'Q4')")
    
    long_term_debt_to_total_capital: float = Field(..., description="Long-term debt / total capital (%)")
    total_debt_to_ebitda: float = Field(..., description="Total debt / EBITDA")
    net_income_margin: float = Field(..., description="Net income margin (%)")
    ebit_to_interest_expense: float = Field(..., description="EBIT / interest expense")
    return_on_assets: float = Field(..., description="Return on assets (%)")

# Quarterly-specific bulk schemas
class QuarterlyBulkPredictionItem(BaseModel):
    stock_symbol: str
    company_name: str
    reporting_year: str
    reporting_quarter: str
    sector: Optional[str] = None
    market_cap: Optional[float] = None
    success: bool
    prediction_id: Optional[str] = None
    default_probability: Optional[float] = None
    risk_level: Optional[str] = None
    confidence: Optional[float] = None
    error: Optional[str] = None
    financial_ratios: Optional[dict] = None

class QuarterlyBulkPredictionResponse(BaseModel):
    success: bool
    message: str
    total_records: int
    processed_records: int
    error_records: int
    skipped_records: int
    processing_time_seconds: float
    results: List[QuarterlyBulkPredictionItem]

class QuarterlyBulkJobResponse(BaseModel):
    success: bool
    message: str
    job_id: str
    status: str
    filename: str
    estimated_processing_time: str
