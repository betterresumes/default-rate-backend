from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from uuid import UUID

# ========================================
# ORGANIZATION SCHEMAS (NEW)
# ========================================

class OrganizationBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100)
    domain: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    logo_url: Optional[str] = None
    max_users: Optional[int] = Field(None, ge=1, le=1000)

class OrganizationInDB(OrganizationBase):
    id: UUID
    logo_url: Optional[str] = None
    is_active: bool
    max_users: int
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ========================================
# UPDATED USER SCHEMAS
# ========================================

class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)
    confirm_password: str = Field(..., min_length=8, max_length=100)
    
    @validator('confirm_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserInDB(UserBase):
    id: UUID
    organization_id: Optional[UUID] = None
    organization_role: str
    global_role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserWithOrganization(UserInDB):
    organization: Optional[OrganizationInDB] = None

# ========================================
# AUTH RESPONSE SCHEMAS
# ========================================

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserInDB

class AuthResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None

class TokenData(BaseModel):
    user_id: Optional[str] = None

# ========================================
# UPDATED COMPANY SCHEMAS
# ========================================

class CompanyBase(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=255)
    market_cap: Decimal = Field(..., gt=0)
    sector: str = Field(..., min_length=1, max_length=100)

class CompanyCreate(CompanyBase):
    is_global: bool = False

class CompanyInDB(CompanyBase):
    id: UUID
    organization_id: Optional[UUID] = None
    is_global: bool
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ========================================
# PREDICTION SCHEMAS (ENHANCED)
# ========================================

class AnnualPredictionBase(BaseModel):
    reporting_year: Optional[str] = Field(None, max_length=4)
    reporting_quarter: Optional[str] = Field(None, max_length=2)
    long_term_debt_to_total_capital: Optional[Decimal] = None
    total_debt_to_ebitda: Optional[Decimal] = None
    net_income_margin: Optional[Decimal] = None
    ebit_to_interest_expense: Optional[Decimal] = None
    return_on_assets: Optional[Decimal] = None

class AnnualPredictionRequest(CompanyBase, AnnualPredictionBase):
    pass

class AnnualPredictionInDB(AnnualPredictionBase):
    id: UUID
    company_id: UUID
    organization_id: Optional[UUID] = None
    probability: Decimal
    risk_level: str
    confidence: Decimal
    predicted_at: datetime
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class QuarterlyPredictionBase(BaseModel):
    reporting_year: str = Field(..., max_length=4)
    reporting_quarter: str = Field(..., max_length=2)
    total_debt_to_ebitda: Decimal
    sga_margin: Decimal
    long_term_debt_to_total_capital: Decimal
    return_on_capital: Decimal

class QuarterlyPredictionRequest(CompanyBase, QuarterlyPredictionBase):
    pass

class QuarterlyPredictionInDB(QuarterlyPredictionBase):
    id: UUID
    company_id: UUID
    organization_id: Optional[UUID] = None
    logistic_probability: Decimal
    gbm_probability: Decimal
    ensemble_probability: Decimal
    risk_level: str
    confidence: Decimal
    predicted_at: datetime
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ========================================
# UNIFIED PREDICTION SCHEMAS
# ========================================

class UnifiedPredictionRequest(BaseModel):
    prediction_type: str = Field(..., regex="^(annual|quarterly)$")
    stock_symbol: str = Field(..., min_length=1, max_length=20)
    company_name: str = Field(..., min_length=1, max_length=255)
    market_cap: Decimal = Field(..., gt=0)
    sector: str = Field(..., min_length=1, max_length=100)
    reporting_year: str = Field(..., max_length=4)
    reporting_quarter: Optional[str] = Field(None, max_length=2)
    
    # Annual fields
    long_term_debt_to_total_capital: Optional[Decimal] = None
    total_debt_to_ebitda: Optional[Decimal] = None
    net_income_margin: Optional[Decimal] = None
    ebit_to_interest_expense: Optional[Decimal] = None
    return_on_assets: Optional[Decimal] = None
    
    # Quarterly fields
    sga_margin: Optional[Decimal] = None
    return_on_capital: Optional[Decimal] = None

# ========================================
# RESPONSE SCHEMAS
# ========================================

class CompanyWithPredictionsResponse(BaseModel):
    company: CompanyInDB
    annual_predictions: List[AnnualPredictionInDB] = []
    quarterly_predictions: List[QuarterlyPredictionInDB] = []

class PaginatedResponse(BaseModel):
    success: bool
    data: dict
    pagination: dict

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[str] = None

# ========================================
# OTP SCHEMAS (SIMPLIFIED)
# ========================================

class OTPRequest(BaseModel):
    email: EmailStr

class OTPVerification(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)

# ========================================
# BULK PREDICTION SCHEMAS
# ========================================

class BulkPredictionItem(BaseModel):
    company: CompanyInDB
    prediction: dict
    status: str

class BulkPredictionResponse(BaseModel):
    success: bool
    message: str
    total_processed: int
    successful: int
    failed: int
    results: List[BulkPredictionItem] = []

class BulkJobResponse(BaseModel):
    success: bool
    job_id: str
    message: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    total: int
    completed_at: Optional[datetime] = None

# ========================================
# UPDATE SCHEMAS
# ========================================

class PredictionUpdateRequest(BaseModel):
    reporting_year: Optional[str] = None
    reporting_quarter: Optional[str] = None
    # Add other fields that can be updated

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    username: Optional[str] = None
    # Organization changes handled separately

# For quarterly bulk predictions
QuarterlyBulkPredictionItem = BulkPredictionItem
QuarterlyBulkPredictionResponse = BulkPredictionResponse
QuarterlyBulkJobResponse = BulkJobResponse
