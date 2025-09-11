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

router = APIRouter()

def serialize_datetime(dt):
    """Helper function to serialize datetime objects"""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    return dt


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
        result = service.get_companies(page, limit, sector, search, sort_by, sort_order)
        
        companies_data = []
        for company in result["companies"]:
            # Serialize recent ratios with only the 5 required fields
            recent_ratios = []
            if company.ratios:
                for ratio in company.ratios[-3:]:
                    recent_ratios.append({
                        "id": ratio.id,
                        "long_term_debt_to_total_capital": float(ratio.long_term_debt_to_total_capital),
                        "total_debt_to_ebitda": float(ratio.total_debt_to_ebitda),
                        "net_income_margin": float(ratio.net_income_margin),
                        "ebit_to_interest_expense": float(ratio.ebit_to_interest_expense),
                        "return_on_assets": float(ratio.return_on_assets),
                        "reporting_year": ratio.reporting_year,
                        "reporting_quarter": ratio.reporting_quarter,
                        "created_at": serialize_datetime(ratio.created_at)
                    })
            
            # Serialize recent predictions
            recent_predictions = []
            if company.predictions:
                for pred in company.predictions[-3:]:
                    recent_predictions.append({
                        "id": pred.id,
                        "risk_level": pred.risk_level,
                        "confidence": float(pred.confidence),
                        "probability": float(pred.probability) if pred.probability else None,
                        "predicted_at": serialize_datetime(pred.predicted_at)
                    })

            company_dict = {
                "id": company.id,
                "symbol": company.symbol,
                "name": company.name,
                "market_cap": float(company.market_cap) if company.market_cap else None,
                "sector": company.sector,
                "reporting_year": company.reporting_year,
                "reporting_quarter": company.reporting_quarter,
                "created_at": serialize_datetime(company.created_at),
                "updated_at": serialize_datetime(company.updated_at),
                "recent_ratios": recent_ratios,
                "recent_predictions": recent_predictions
            }
            companies_data.append(company_dict)
        
        return PaginatedResponse(
            success=True,
            data={"companies": companies_data},
            pagination=result["pagination"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch companies: {str(e)}")

@router.get("/{company_id}", response_model=dict)
async def get_company_by_id(
    company_id: int, 
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
                "id": company.id,
                "symbol": company.symbol,
                "name": company.name,
                "market_cap": float(company.market_cap) if company.market_cap else None,
                "sector": company.sector,
                "reporting_year": company.reporting_year,
                "reporting_quarter": company.reporting_quarter,
                "created_at": serialize_datetime(company.created_at),
                "updated_at": serialize_datetime(company.updated_at),
                "ratios": [
                    {
                        "id": ratio.id,
                        "long_term_debt_to_total_capital": float(ratio.long_term_debt_to_total_capital),
                        "total_debt_to_ebitda": float(ratio.total_debt_to_ebitda),
                        "net_income_margin": float(ratio.net_income_margin),
                        "ebit_to_interest_expense": float(ratio.ebit_to_interest_expense),
                        "return_on_assets": float(ratio.return_on_assets),
                        "reporting_year": ratio.reporting_year,
                        "reporting_quarter": ratio.reporting_quarter,
                        "created_at": serialize_datetime(ratio.created_at),
                        "updated_at": serialize_datetime(ratio.updated_at)
                    } for ratio in company.ratios[-10:]
                ],
                "predictions": [
                    {
                        "id": pred.id,
                        "risk_level": pred.risk_level,
                        "confidence": float(pred.confidence),
                        "probability": float(pred.probability) if pred.probability else None,
                        "long_term_debt_to_total_capital": float(pred.long_term_debt_to_total_capital),
                        "total_debt_to_ebitda": float(pred.total_debt_to_ebitda),
                        "net_income_margin": float(pred.net_income_margin),
                        "ebit_to_interest_expense": float(pred.ebit_to_interest_expense),
                        "return_on_assets": float(pred.return_on_assets),
                        "predicted_at": serialize_datetime(pred.predicted_at),
                        "created_at": serialize_datetime(pred.created_at)
                    } for pred in company.predictions[-10:]
                ]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch company: {str(e)}")

# Company creation removed - companies are only created through prediction API
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create company: {str(e)}")