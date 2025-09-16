from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db, User
from ..schemas import (
    Company, CompanyCreate, 
    PaginatedResponse, ErrorResponse
)
from ..services import CompanyService
from ..auth import get_current_verified_user
from typing import Optional
from datetime import datetime
import math

router = APIRouter()

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
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Get paginated list of companies with filtering and sorting"""
    try:
        service = CompanyService(db)
        result = service.get_companies_with_predictions(
            page=page,
            limit=limit,
            sector=sector,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch companies: {str(e)}")


@router.get("/{company_id}", response_model=dict)
async def get_company_by_id(
    company_id: str, 
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Get company by ID with full details"""
    try:
        service = CompanyService(db)
        company = service.get_company_by_id(company_id)
        
        if not company:
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
                        "created_at": serialize_datetime(pred.created_at)
                    } for pred in company.annual_predictions
                ],
                "quarterly_predictions": [
                    {
                        "id": str(pred.id),
                        "reporting_year": pred.reporting_year,
                        "reporting_quarter": pred.reporting_quarter,
                        "risk_level": pred.risk_level,
                        "confidence": float(pred.confidence),
                        "ensemble_probability": float(pred.ensemble_probability),
                        "logistic_probability": float(pred.logistic_probability),
                        "gbm_probability": float(pred.gbm_probability),
                        "created_at": serialize_datetime(pred.created_at)
                    } for pred in company.quarterly_predictions
                ]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch company: {str(e)}")