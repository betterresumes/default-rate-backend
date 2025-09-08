from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from schemas import PredictionRequest, PredictionResponse
from services import CompanyService, PredictionService
from ml_service import ml_service
from typing import Dict
from datetime import datetime

router = APIRouter()


def serialize_datetime(dt):
    """Helper function to serialize datetime objects"""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    return dt


@router.post("/predict-default-rate", response_model=dict)
async def predict_default_rate(
    request: PredictionRequest,
    db: Session = Depends(get_db)
):
    """Predict default rate for a company using ML model"""
    try:
        company_service = CompanyService(db)
        prediction_service = PredictionService(db)

        # Check if company exists (lightweight query)
        company = company_service.get_company_by_symbol(request.stock_symbol)

        if not company:
            # Create new company
            from schemas import CompanyCreate
            company_data = CompanyCreate(
                symbol=request.stock_symbol,
                name=request.company_name,
                market_cap=request.market_cap,
                sector=request.sector
            )
            company = company_service.create_company(company_data)

        # Check for recent prediction (within 24 hours)
        recent_prediction = prediction_service.get_recent_prediction(company.id, 24)
        
        if recent_prediction:
            return {
                "success": True,
                "message": "Using cached prediction",
                "company": {
                    "symbol": company.symbol,
                    "name": company.name,
                    "sector": company.sector.name if company.sector else None
                },
                "prediction": {
                    "risk_level": recent_prediction.risk_level,
                    "confidence": float(recent_prediction.confidence),
                    "probability": float(recent_prediction.probability) if recent_prediction.probability else None,
                    "predicted_at": serialize_datetime(recent_prediction.predicted_at)
                }
            }

        # Prepare financial ratios for prediction
        ratios = {
            "debt_to_equity_ratio": request.debt_to_equity_ratio,
            "current_ratio": request.current_ratio,
            "quick_ratio": request.quick_ratio,
            "return_on_equity": request.return_on_equity,
            "return_on_assets": request.return_on_assets,
            "profit_margin": request.profit_margin,
            "interest_coverage": request.interest_coverage,
            "fixed_asset_turnover": request.fixed_asset_turnover,
            "total_debt_ebitda": request.total_debt_ebitda
        }

        # Make prediction using ML model (optimized)
        prediction_result = ml_service.predict_default_probability(ratios)

        # Batch database operations - save both prediction and ratios, then commit once
        saved_prediction = prediction_service.save_prediction(
            company.id, 
            prediction_result, 
            ratios
        )
        
        prediction_service.save_financial_ratios(company.id, ratios)
        
        # Single commit for both operations
        prediction_service.commit_transaction()

        return {
            "success": True,
            "message": "New prediction generated",
            "company": {
                "symbol": company.symbol,
                "name": company.name,
                "sector": company.sector.name if company.sector else None
            },
            "prediction": {
                "risk_level": prediction_result["risk_level"],
                "confidence": prediction_result["confidence"],
                "probability": prediction_result["probability"],
                "predicted_at": serialize_datetime(saved_prediction.predicted_at),
                "model_features": prediction_result.get("model_features", {}),
                "model_info": {
                    "model_type": "Logistic Regression"
                }
            }
        }

    except Exception as e:
        print(f"Prediction error: {e}")
        # Rollback on error
        db.rollback()
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "Prediction failed",
                "details": str(e)
            }
        )