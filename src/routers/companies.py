from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas import (
    Company, CompanyCreate, 
    PaginatedResponse, ErrorResponse
)
from ..services import CompanyService
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
    db: Session = Depends(get_db)
):
    """Get paginated list of companies with filtering and sorting"""
    try:
        service = CompanyService(db)
        result = service.get_companies(page, limit, sector, search, sort_by, sort_order)
        
        companies_data = []
        for company in result["companies"]:
            # Serialize recent ratios (limit to last 3 for list view performance)
            recent_ratios = []
            if company.ratios:
                for ratio in company.ratios[-3:]:  # Reduced from 5 to 3
                    recent_ratios.append({
                        "id": ratio.id,
                        "debt_to_equity_ratio": float(ratio.debt_to_equity_ratio) if ratio.debt_to_equity_ratio else None,
                        "current_ratio": float(ratio.current_ratio) if ratio.current_ratio else None,
                        "quick_ratio": float(ratio.quick_ratio) if ratio.quick_ratio else None,
                        "return_on_equity": float(ratio.return_on_equity) if ratio.return_on_equity else None,
                        "return_on_assets": float(ratio.return_on_assets) if ratio.return_on_assets else None,
                        "profit_margin": float(ratio.profit_margin) if ratio.profit_margin else None,
                        "interest_coverage": float(ratio.interest_coverage) if ratio.interest_coverage else None,
                        "created_at": serialize_datetime(ratio.created_at)
                    })
            
            # Serialize recent predictions (limit to last 3 for list view performance)
            recent_predictions = []
            if company.predictions:
                for pred in company.predictions[-3:]:  # Reduced from 5 to 3
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
                "created_at": serialize_datetime(company.created_at),
                "updated_at": serialize_datetime(company.updated_at),
                "sector": company.sector,
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
async def get_company_by_id(company_id: int, db: Session = Depends(get_db)):
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
                "created_at": serialize_datetime(company.created_at),
                "updated_at": serialize_datetime(company.updated_at),
                "sector": company.sector,
                "ratios": [
                    {
                        "id": ratio.id,
                        "debt_to_equity_ratio": float(ratio.debt_to_equity_ratio) if ratio.debt_to_equity_ratio else None,
                        "current_ratio": float(ratio.current_ratio) if ratio.current_ratio else None,
                        "quick_ratio": float(ratio.quick_ratio) if ratio.quick_ratio else None,
                        "return_on_equity": float(ratio.return_on_equity) if ratio.return_on_equity else None,
                        "return_on_assets": float(ratio.return_on_assets) if ratio.return_on_assets else None,
                        "profit_margin": float(ratio.profit_margin) if ratio.profit_margin else None,
                        "interest_coverage": float(ratio.interest_coverage) if ratio.interest_coverage else None,
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