from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db, User, Company, AnnualPrediction, QuarterlyPrediction
from ..schemas import (
    QuarterlyPredictionRequest, AnnualPredictionRequest,
    UnifiedPredictionRequest, CompanyWithPredictionsResponse
)
from ..services import CompanyService
from ..ml_service import ml_model
from ..quarterly_ml_service import quarterly_ml_model
from ..auth import get_current_verified_user
from typing import Dict, List
from datetime import datetime

router = APIRouter()

def serialize_datetime(dt):
    """Helper function to serialize datetime objects"""
    if dt is None:
        return None
    return dt.isoformat()

@router.post("/predict-annual")
async def predict_annual_default_rate(
    request: AnnualPredictionRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Create annual default rate prediction using machine learning"""
    try:
        company_service = CompanyService(db)

        company = company_service.get_company_by_symbol(request.stock_symbol)
        
        if not company:
            company = company_service.create_company(
                symbol=request.stock_symbol,
                name=request.company_name,
                market_cap=request.market_cap,
                sector=request.sector
            )

        existing_prediction = company_service.get_annual_prediction(
            company.id, request.reporting_year
        )
        
        if existing_prediction:
            raise HTTPException(
                status_code=400,
                detail=f"Annual prediction for {request.stock_symbol} in {request.reporting_year} already exists"
            )

        ratios = {
            "long_term_debt_to_total_capital": request.long_term_debt_to_total_capital,
            "total_debt_to_ebitda": request.total_debt_to_ebitda,
            "net_income_margin": request.net_income_margin,
            "ebit_to_interest_expense": request.ebit_to_interest_expense,
            "return_on_assets": request.return_on_assets
        }

        prediction_result = ml_model.predict_default_probability(ratios)

        if "error" in prediction_result:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Annual prediction failed",
                    "details": prediction_result["error"]
                }
            )

        return {
            "success": True,
            "message": "Annual prediction created successfully",
            "company": {
                "id": str(company.id),
                "symbol": company.symbol,
                "name": company.name,
                "market_cap": float(company.market_cap) if company.market_cap else None,
        )

        return {
            "success": True,
            "message": "Annual prediction created successfully",
            "company": {
                "id": str(company.id),
                "symbol": company.symbol,
                "name": company.name,
                "market_cap": float(company.market_cap) if company.market_cap else None,
                "sector": company.sector,
                "prediction": {
                    "id": str(annual_prediction.id),
                    "type": "annual",
                    "reporting_year": annual_prediction.reporting_year,
                    "probability": float(annual_prediction.probability),
                    "risk_level": annual_prediction.risk_level,
                    "confidence": float(annual_prediction.confidence),
                    "financial_ratios": {
                        "long_term_debt_to_total_capital": float(annual_prediction.long_term_debt_to_total_capital),
                        "total_debt_to_ebitda": float(annual_prediction.total_debt_to_ebitda),
                        "net_income_margin": float(annual_prediction.net_income_margin),
                        "ebit_to_interest_expense": float(annual_prediction.ebit_to_interest_expense),
                        "return_on_assets": float(annual_prediction.return_on_assets)
                    },
                    "created_at": serialize_datetime(annual_prediction.created_at)
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Annual prediction failed",
                "details": str(e)
            }
        )

@router.post("/predict-quarterly")
async def predict_quarterly_default_rate(
    request: QuarterlyPredictionRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Create quarterly default rate prediction using machine learning"""
    try:
        company_service = CompanyService(db)

        company = company_service.get_company_by_symbol(request.stock_symbol)
        
        if not company:
            company = company_service.create_company(
                symbol=request.stock_symbol,
                name=request.company_name,
                market_cap=request.market_cap,
                sector=request.sector
            )

        existing_prediction = company_service.get_quarterly_prediction(
            company.id, request.reporting_year, request.reporting_quarter
        )
        
        if existing_prediction:
            raise HTTPException(
                status_code=400,
                detail=f"Quarterly prediction for {request.stock_symbol} in {request.reporting_quarter} {request.reporting_year} already exists"
            )

        ratios = {
            "total_debt_to_ebitda": request.total_debt_to_ebitda,
            "sga_margin": request.sga_margin,
            "long_term_debt_to_total_capital": request.long_term_debt_to_total_capital,
            "return_on_capital": request.return_on_capital
        }

        prediction_result = quarterly_ml_model.predict_default_probability(ratios)

        if "error" in prediction_result:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Quarterly prediction failed",
                    "details": prediction_result["error"]
                }
            )

        quarterly_prediction = company_service.create_quarterly_prediction(
            company=company,
            financial_data=ratios,
            prediction_results=prediction_result,
            reporting_year=request.reporting_year,
            reporting_quarter=request.reporting_quarter
        )

        return {
            "success": True,
            "message": "Quarterly prediction created successfully",
            "company": {
                "id": str(company.id),
                "symbol": company.symbol,
                "name": company.name,
                "market_cap": float(company.market_cap) if company.market_cap else None,
                "sector": company.sector,
                "prediction": {
                    "id": str(quarterly_prediction.id),
                    "type": "quarterly",
                    "reporting_year": quarterly_prediction.reporting_year,
                    "reporting_quarter": quarterly_prediction.reporting_quarter,
                    "probabilities": {
                        "logistic": float(quarterly_prediction.logistic_probability),
                        "gbm": float(quarterly_prediction.gbm_probability),
                        "ensemble": float(quarterly_prediction.ensemble_probability)
                    },
                    "primary_probability": float(quarterly_prediction.ensemble_probability),
                    "risk_level": quarterly_prediction.risk_level,
                    "confidence": float(quarterly_prediction.confidence),
                    "financial_ratios": {
                        "total_debt_to_ebitda": float(quarterly_prediction.total_debt_to_ebitda),
                        "sga_margin": float(quarterly_prediction.sga_margin),
                        "long_term_debt_to_total_capital": float(quarterly_prediction.long_term_debt_to_total_capital),
                        "return_on_capital": float(quarterly_prediction.return_on_capital)
                    },
                    "created_at": serialize_datetime(quarterly_prediction.created_at)
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Quarterly prediction failed",
                "details": str(e)
            }
        )

@router.post("/unified-predict")
async def unified_predict(
    request: UnifiedPredictionRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Unified endpoint for both annual and quarterly predictions"""
    try:
        if request.prediction_type == "annual":
            annual_request = AnnualPredictionRequest(
                stock_symbol=request.stock_symbol,
                company_name=request.company_name,
                market_cap=request.market_cap,
                sector=request.sector,
                reporting_year=request.reporting_year,
                long_term_debt_to_total_capital=request.long_term_debt_to_total_capital,
                total_debt_to_ebitda=request.total_debt_to_ebitda,
                net_income_margin=request.net_income_margin,
                ebit_to_interest_expense=request.ebit_to_interest_expense,
                return_on_assets=request.return_on_assets
            )
            return await predict_annual_default_rate(annual_request, current_user, db)
            
        elif request.prediction_type == "quarterly":
            quarterly_request = QuarterlyPredictionRequest(
                stock_symbol=request.stock_symbol,
                company_name=request.company_name,
                market_cap=request.market_cap,
                sector=request.sector,
                reporting_year=request.reporting_year,
                reporting_quarter=request.reporting_quarter,
                total_debt_to_ebitda=request.total_debt_to_ebitda,
                sga_margin=request.sga_margin,
                long_term_debt_to_total_capital=request.long_term_debt_to_total_capital,
                return_on_capital=request.return_on_capital
            )
            return await predict_quarterly_default_rate(quarterly_request, current_user, db)
        
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid prediction_type. Must be 'annual' or 'quarterly'"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"{request.prediction_type.title()} prediction failed",
                "details": str(e)
            }
        )

@router.get("/companies", response_model=Dict)
async def get_companies_with_predictions(
    page: int = 1,
    limit: int = 10,
    sector: str = None,
    search: str = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Get paginated list of companies with their predictions"""
    try:
        company_service = CompanyService(db)
        result = company_service.get_companies_with_predictions(
            page=page,
            limit=limit,
            sector=sector,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order
        )

        formatted_companies = []
        for company in result["companies"]:
            company_data = {
                "id": str(company.id),
                "symbol": company.symbol,
                "name": company.name,
                "market_cap": float(company.market_cap) if company.market_cap else None,
                "sector": company.sector,
                "created_at": serialize_datetime(company.created_at),
                "updated_at": serialize_datetime(company.updated_at),
                "annual_predictions": [],
                "quarterly_predictions": []
            }

            for pred in company.annual_predictions:
                company_data["annual_predictions"].append({
                    "id": str(pred.id),
                    "reporting_year": pred.reporting_year,
                    "probability": float(pred.probability),
                    "risk_level": pred.risk_level,
                    "confidence": float(pred.confidence),
                    "created_at": serialize_datetime(pred.created_at)
                })

            for pred in company.quarterly_predictions:
                company_data["quarterly_predictions"].append({
                    "id": str(pred.id),
                    "reporting_year": pred.reporting_year,
                    "reporting_quarter": pred.reporting_quarter,
                    "probabilities": {
                        "logistic": float(pred.logistic_probability),
                        "gbm": float(pred.gbm_probability),
                        "ensemble": float(pred.ensemble_probability)
                    },
                    "primary_probability": float(pred.ensemble_probability),
                    "risk_level": pred.risk_level,
                    "confidence": float(pred.confidence),
                    "created_at": serialize_datetime(pred.created_at)
                })

            formatted_companies.append(company_data)

        return {
            "success": True,
            "companies": formatted_companies,
            "pagination": result["pagination"]
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to retrieve companies",
                "details": str(e)
            }
        )

@router.get("/companies/{company_id}")
async def get_company_by_id(
    company_id: str,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Get specific company by ID with all predictions"""
    try:
        company_service = CompanyService(db)
        company = company_service.get_company_by_id(company_id)
        
        if not company:
            raise HTTPException(
                status_code=404,
                detail=f"Company with ID {company_id} not found"
            )

        company_data = {
            "id": str(company.id),
            "symbol": company.symbol,
            "name": company.name,
            "market_cap": float(company.market_cap) if company.market_cap else None,
            "sector": company.sector,
            "created_at": serialize_datetime(company.created_at),
            "updated_at": serialize_datetime(company.updated_at),
            "annual_predictions": [],
            "quarterly_predictions": []
        }

        for pred in company.annual_predictions:
            company_data["annual_predictions"].append({
                "id": str(pred.id),
                "reporting_year": pred.reporting_year,
                "probability": float(pred.probability),
                "risk_level": pred.risk_level,
                "confidence": float(pred.confidence),
                "financial_ratios": {
                    "long_term_debt_to_total_capital": float(pred.long_term_debt_to_total_capital),
                    "total_debt_to_ebitda": float(pred.total_debt_to_ebitda),
                    "net_income_margin": float(pred.net_income_margin),
                    "ebit_to_interest_expense": float(pred.ebit_to_interest_expense),
                    "return_on_assets": float(pred.return_on_assets)
                },
                "created_at": serialize_datetime(pred.created_at)
            })

        for pred in company.quarterly_predictions:
            company_data["quarterly_predictions"].append({
                "id": str(pred.id),
                "reporting_year": pred.reporting_year,
                "reporting_quarter": pred.reporting_quarter,
                "probabilities": {
                    "logistic": float(pred.logistic_probability),
                    "gbm": float(pred.gbm_probability),
                    "ensemble": float(pred.ensemble_probability)
                },
                "primary_probability": float(pred.ensemble_probability),
                "risk_level": pred.risk_level,
                "confidence": float(pred.confidence),
                "financial_ratios": {
                    "total_debt_to_ebitda": float(pred.total_debt_to_ebitda),
                    "sga_margin": float(pred.sga_margin),
                    "long_term_debt_to_total_capital": float(pred.long_term_debt_to_total_capital),
                    "return_on_capital": float(pred.return_on_capital)
                },
                "created_at": serialize_datetime(pred.created_at)
            })

        return {
            "success": True,
            "company": company_data
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to retrieve company",
                "details": str(e)
            }
        )

@router.post("/predict-default-rate")
async def predict_default_rate_legacy(
    request: AnnualPredictionRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Legacy annual prediction endpoint for backward compatibility"""
    return await predict_annual_default_rate(request, current_user, db)


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Prediction API is running",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "annual": "/api/predictions/predict-annual",
            "quarterly": "/api/predictions/predict-quarterly", 
            "unified": "/api/predictions/unified-predict",
            "companies": "/api/predictions/companies"
        }
    }
