from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class SectorBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None


class SectorCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class Sector(SectorBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


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
    sector_id: Optional[int] = None


class CompanyCreate(CompanyBase):
    sector: Optional[str] = None  # Sector name, will be resolved to sector_id


class Company(CompanyBase):
    id: int
    created_at: datetime
    updated_at: datetime
    sector: Optional[Sector] = None
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
