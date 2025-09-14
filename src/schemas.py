from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from uuid import UUID

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

class UserInDB(UserBase):
    id: UUID
    is_active: bool
    is_verified: bool
    is_superuser: bool
    role: str
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True

class User(UserInDB):
    pass

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None

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


class CompanyBase(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    name: str = Field(..., min_length=1, max_length=200)
    market_cap: float = Field(..., ge=0, description="Market capitalization in USD")
    sector: str = Field(..., min_length=1, max_length=100, description="Company sector/industry")
    reporting_year: Optional[str] = Field(None, description="Reporting year (e.g., '2024')")
    reporting_quarter: Optional[str] = Field(None, description="Reporting quarter (e.g., 'Q4')")
    
    long_term_debt_to_total_capital: float = Field(..., description="Long-term debt / total capital (%)")
    total_debt_to_ebitda: float = Field(..., description="Total debt / EBITDA")
    net_income_margin: float = Field(..., description="Net income margin (%)")
    ebit_to_interest_expense: float = Field(..., description="EBIT / interest expense")
    return_on_assets: float = Field(..., description="Return on assets (%)")
    
    risk_level: str = Field(..., description="Risk level (LOW, MEDIUM, HIGH)")
    confidence: float = Field(..., ge=0, le=1, description="Prediction confidence (0-1)")
    probability: Optional[float] = Field(None, ge=0, le=1, description="Default probability (0-1)")
    predicted_at: datetime = Field(..., description="When the prediction was made")


class CompanyCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    name: str = Field(..., min_length=1, max_length=200)
    market_cap: float = Field(..., ge=0, description="Market capitalization in USD")
    sector: str = Field(..., min_length=1, max_length=100, description="Company sector/industry")
    reporting_year: Optional[str] = Field(None, description="Reporting year (e.g., '2024')")
    reporting_quarter: Optional[str] = Field(None, description="Reporting quarter (e.g., 'Q4')")
    
    long_term_debt_to_total_capital: float = Field(..., description="Long-term debt / total capital (%)")
    total_debt_to_ebitda: float = Field(..., description="Total debt / EBITDA")
    net_income_margin: float = Field(..., description="Net income margin (%)")
    ebit_to_interest_expense: float = Field(..., description="EBIT / interest expense")
    return_on_assets: float = Field(..., description="Return on assets (%)")


class Company(CompanyBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PredictionRequest(BaseModel):
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
    company_name: Optional[str] = Field(None, min_length=1, max_length=200)
    market_cap: Optional[float] = Field(None, ge=0, description="Market capitalization in USD")
    sector: Optional[str] = Field(None, min_length=1, max_length=100, description="Company sector/industry")
    reporting_year: Optional[str] = Field(None, description="Reporting year (e.g., '2024')")
    reporting_quarter: Optional[str] = Field(None, description="Reporting quarter (e.g., 'Q4')")
    
    # Financial ratios (optional for update - if any provided, prediction will be recalculated)
    long_term_debt_to_total_capital: Optional[float] = Field(None, description="Long-term debt / total capital (%)")
    total_debt_to_ebitda: Optional[float] = Field(None, description="Total debt / EBITDA")
    net_income_margin: Optional[float] = Field(None, description="Net income margin (%)")
    ebit_to_interest_expense: Optional[float] = Field(None, description="EBIT / interest expense")
    return_on_assets: Optional[float] = Field(None, description="Return on assets (%)")


class DatabaseResetRequest(BaseModel):
    table_name: Optional[str] = Field(None, description="Specific table to reset: 'companies', 'users', 'otp_tokens', 'user_sessions' (if not provided, resets all tables)")
    confirm_reset: bool = Field(..., description="Confirmation flag to prevent accidental resets")


class DatabaseResetResponse(BaseModel):
    success: bool
    message: str
    tables_reset: List[str]
    affected_records: Optional[int] = None
