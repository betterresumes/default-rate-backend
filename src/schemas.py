from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

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
    id: int
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
    user_id: Optional[int] = None

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

class FinancialRatioBase(BaseModel):
    debt_to_equity_ratio: Optional[float] = None
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    return_on_equity: Optional[float] = None
    return_on_assets: Optional[float] = None
    profit_margin: Optional[float] = None
    interest_coverage: Optional[float] = None
    fixed_asset_turnover: Optional[float] = None
    total_debt_ebitda: Optional[float] = None


class FinancialRatio(FinancialRatioBase):
    id: int
    company_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DefaultRatePredictionBase(BaseModel):
    risk_level: str
    confidence: float
    probability: Optional[float] = None
    debt_to_equity_ratio: Optional[float] = None
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    return_on_equity: Optional[float] = None
    return_on_assets: Optional[float] = None
    profit_margin: Optional[float] = None
    interest_coverage: Optional[float] = None
    fixed_asset_turnover: Optional[float] = None
    total_debt_ebitda: Optional[float] = None


class DefaultRatePrediction(DefaultRatePredictionBase):
    id: int
    company_id: int
    predicted_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CompanyBase(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    name: str = Field(..., min_length=1, max_length=200)
    market_cap: Optional[float] = None
    sector: Optional[str] = None


class CompanyCreate(CompanyBase):
    pass


class Company(CompanyBase):
    id: int
    created_at: datetime
    updated_at: datetime
    ratios: List[FinancialRatio] = []
    predictions: List[DefaultRatePrediction] = []

    class Config:
        from_attributes = True


class PredictionRequest(BaseModel):
    stock_symbol: str = Field(..., min_length=1, max_length=10)
    company_name: str = Field(..., min_length=1, max_length=200)
    market_cap: Optional[float] = None
    sector: Optional[str] = None
    debt_to_equity_ratio: Optional[float] = None
    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    return_on_equity: Optional[float] = None
    return_on_assets: Optional[float] = None
    profit_margin: Optional[float] = None
    interest_coverage: Optional[float] = None
    fixed_asset_turnover: Optional[float] = None
    total_debt_ebitda: Optional[float] = None


class PredictionResponse(BaseModel):
    success: bool
    message: str
    company: dict
    prediction: dict


class PaginatedResponse(BaseModel):
    success: bool
    data: dict
    pagination: Optional[dict] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    details: Optional[str] = None


class BulkPredictionItem(BaseModel):
    """Schema for individual company prediction result in bulk upload"""
    stock_symbol: str
    company_name: str
    sector: Optional[str] = None
    market_cap: Optional[float] = None
    prediction: dict
    status: str 
    error_message: Optional[str] = None


class BulkPredictionResponse(BaseModel):
    """Schema for bulk upload response"""
    success: bool
    message: str
    total_companies: int
    successful_predictions: int
    failed_predictions: int
    results: List[BulkPredictionItem]
    processing_time: float


class BulkJobResponse(BaseModel):
    """Schema for bulk job submission response"""
    success: bool
    message: str
    job_id: str
    status: str
    filename: str
    estimated_processing_time: Optional[str] = None


class JobStatusResponse(BaseModel):
    """Schema for job status response"""
    success: bool
    job_id: str
    status: str 
    message: str
    progress: Optional[dict] = None
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: Optional[float] = None
    completed_at: Optional[float] = None
