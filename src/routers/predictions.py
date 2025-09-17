from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..database import get_db, User, Company, AnnualPrediction, QuarterlyPrediction
from ..schemas import (
    QuarterlyPredictionRequest, AnnualPredictionRequest,
    UnifiedPredictionRequest, CompanyWithPredictionsResponse,
    BulkPredictionResponse, BulkPredictionItem, PredictionUpdateRequest,
    BulkJobResponse, JobStatusResponse,
    QuarterlyBulkPredictionResponse, QuarterlyBulkPredictionItem, QuarterlyBulkJobResponse
)
from ..services import CompanyService
from ..ml_service import ml_model
from ..quarterly_ml_service import quarterly_ml_model
from ..auth import get_current_verified_user
from typing import Dict, List
from datetime import datetime
import uuid
import pandas as pd
import io
import base64
import time
import pandas as pd
import io
import time
import uuid
import base64
import math

router = APIRouter()

def serialize_datetime(dt):
    """Helper function to serialize datetime objects"""
    if dt is None:
        return None
    return dt.isoformat()

def safe_float(value):
    """Convert value to float, handling None and NaN values"""
    if value is None:
        return None
    try:
        float_val = float(value)
        if math.isnan(float_val) or math.isinf(float_val):
            return None
        return float_val
    except (ValueError, TypeError):
        return None
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

        annual_prediction = company_service.create_annual_prediction(
            company=company,
            financial_data=ratios,
            prediction_results=prediction_result,
            reporting_year=request.reporting_year
        )

        return {
            "success": True,
            "message": "Annual prediction created successfully",
            "company": {
                "id": str(company.id),
                "symbol": company.symbol,
                "name": company.name,
                "market_cap": safe_float(company.market_cap),
                "sector": company.sector,
                "prediction": {
                    "id": str(annual_prediction.id),
                    "type": "annual",
                    "reporting_year": annual_prediction.reporting_year,
                    "reporting_quarter": annual_prediction.reporting_quarter,
                    "probability": safe_float(annual_prediction.probability),
                    "primary_probability": safe_float(annual_prediction.probability),
                    "risk_level": annual_prediction.risk_level,
                    "confidence": safe_float(annual_prediction.confidence),
                    "financial_ratios": {
                        "long_term_debt_to_total_capital": safe_float(annual_prediction.long_term_debt_to_total_capital),
                        "total_debt_to_ebitda": safe_float(annual_prediction.total_debt_to_ebitda),
                        "net_income_margin": safe_float(annual_prediction.net_income_margin),
                        "ebit_to_interest_expense": safe_float(annual_prediction.ebit_to_interest_expense),
                        "return_on_assets": safe_float(annual_prediction.return_on_assets)
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
                "market_cap": safe_float(company.market_cap),
                "sector": company.sector,
                "prediction": {
                    "id": str(quarterly_prediction.id),
                    "type": "quarterly",
                    "reporting_year": quarterly_prediction.reporting_year,
                    "reporting_quarter": quarterly_prediction.reporting_quarter,
                    "probabilities": {
                        "logistic": safe_float(quarterly_prediction.logistic_probability),
                        "gbm": safe_float(quarterly_prediction.gbm_probability),
                        "ensemble": safe_float(quarterly_prediction.ensemble_probability)
                    },
                    "primary_probability": safe_float(quarterly_prediction.ensemble_probability),
                    "risk_level": quarterly_prediction.risk_level,
                    "confidence": safe_float(quarterly_prediction.confidence),
                    "financial_ratios": {
                        "total_debt_to_ebitda": safe_float(quarterly_prediction.total_debt_to_ebitda),
                        "sga_margin": safe_float(quarterly_prediction.sga_margin),
                        "long_term_debt_to_total_capital": safe_float(quarterly_prediction.long_term_debt_to_total_capital),
                        "return_on_capital": safe_float(quarterly_prediction.return_on_capital)
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
                reporting_quarter=request.reporting_quarter,
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
                "market_cap": safe_float(company.market_cap) if company.market_cap else None,
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
                    "reporting_quarter": pred.reporting_quarter,
                    "probability": safe_float(pred.probability),
                    "risk_level": pred.risk_level,
                    "confidence": safe_float(pred.confidence),
                    "created_at": serialize_datetime(pred.created_at)
                })

            for pred in company.quarterly_predictions:
                company_data["quarterly_predictions"].append({
                    "id": str(pred.id),
                    "reporting_year": pred.reporting_year,
                    "reporting_quarter": pred.reporting_quarter,
                    "probabilities": {
                        "logistic": safe_float(pred.logistic_probability),
                        "gbm": safe_float(pred.gbm_probability),
                        "ensemble": safe_float(pred.ensemble_probability)
                    },
                    "primary_probability": safe_float(pred.ensemble_probability),
                    "risk_level": pred.risk_level,
                    "confidence": safe_float(pred.confidence),
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
            "market_cap": safe_float(company.market_cap) if company.market_cap else None,
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
                "reporting_quarter": pred.reporting_quarter,
                "probability": safe_float(pred.probability),
                "risk_level": pred.risk_level,
                "confidence": safe_float(pred.confidence),
                "financial_ratios": {
                    "long_term_debt_to_total_capital": safe_float(pred.long_term_debt_to_total_capital),
                    "total_debt_to_ebitda": safe_float(pred.total_debt_to_ebitda),
                    "net_income_margin": safe_float(pred.net_income_margin),
                    "ebit_to_interest_expense": safe_float(pred.ebit_to_interest_expense),
                    "return_on_assets": safe_float(pred.return_on_assets)
                },
                "created_at": serialize_datetime(pred.created_at)
            })

        for pred in company.quarterly_predictions:
            company_data["quarterly_predictions"].append({
                "id": str(pred.id),
                "reporting_year": pred.reporting_year,
                "reporting_quarter": pred.reporting_quarter,
                "probabilities": {
                    "logistic": safe_float(pred.logistic_probability),
                    "gbm": safe_float(pred.gbm_probability),
                    "ensemble": safe_float(pred.ensemble_probability)
                },
                "primary_probability": safe_float(pred.ensemble_probability),
                "risk_level": pred.risk_level,
                "confidence": safe_float(pred.confidence),
                "financial_ratios": {
                    "total_debt_to_ebitda": safe_float(pred.total_debt_to_ebitda),
                    "sga_margin": safe_float(pred.sga_margin),
                    "long_term_debt_to_total_capital": safe_float(pred.long_term_debt_to_total_capital),
                    "return_on_capital": safe_float(pred.return_on_capital)
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
            "companies": "/api/predictions/companies",
            "bulk_upload": "/api/predictions/bulk-predict",
            "update": "/api/predictions/update/{company_id}",
            "delete": "/api/predictions/delete/{company_id}",
            "summary": "/api/predictions/summary"
        }
    }

@router.get("/summary")
async def get_summary_stats(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Get optimized summary statistics without fetching full company data"""
    try:
        company_service = CompanyService(db)
        
        total_companies = db.query(Company).count()
        
        high_risk_annual = db.query(AnnualPrediction).filter(
            AnnualPrediction.risk_level.in_(['High', 'Critical'])
        ).count()
        
        high_risk_quarterly = db.query(QuarterlyPrediction).filter(
            QuarterlyPrediction.risk_level.in_(['High', 'Critical'])
        ).count()
        
        high_risk_company_ids = set()
        
        annual_high_risk_ids = db.query(AnnualPrediction.company_id).filter(
            AnnualPrediction.risk_level.in_(['High', 'Critical'])
        ).all()
        high_risk_company_ids.update([id[0] for id in annual_high_risk_ids])
        
        quarterly_high_risk_ids = db.query(QuarterlyPrediction.company_id).filter(
            QuarterlyPrediction.risk_level.in_(['High', 'Critical'])
        ).all()
        high_risk_company_ids.update([id[0] for id in quarterly_high_risk_ids])
        
        high_risk_companies = len(high_risk_company_ids)

        annual_avg = db.query(func.avg(AnnualPrediction.probability)).scalar() or 0
        
        quarterly_avg = db.query(func.avg(QuarterlyPrediction.ensemble_probability)).scalar() or 0
        
        annual_count = db.query(AnnualPrediction).count()
        quarterly_count = db.query(QuarterlyPrediction).count()
        total_predictions = annual_count + quarterly_count
        
        if total_predictions > 0:
            average_default_rate = (
                (annual_avg * annual_count + quarterly_avg * quarterly_count) / total_predictions
            ) * 100  
        else:
            average_default_rate = 0
        
        sectors_covered = db.query(func.count(func.distinct(Company.sector))).scalar() or 0
        
        return {
            "success": True,
            "data": {
                "total_companies": total_companies,
                "average_default_rate": round(safe_float(average_default_rate), 2),
                "high_risk_companies": high_risk_companies,
                "sectors_covered": sectors_covered,
                "prediction_breakdown": {
                    "annual_predictions": annual_count,
                    "quarterly_predictions": quarterly_count,
                    "total_predictions": total_predictions
                },
                "last_updated": datetime.utcnow().isoformat(),
                "model_version": "1.0.0"
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to fetch summary statistics",
                "details": str(e)
            }
        )


@router.post("/bulk-predict", response_model=BulkPredictionResponse)
async def bulk_predict_from_file(
    file: UploadFile = File(...),
    prediction_type: str = "annual",
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Bulk prediction endpoint that accepts CSV/Excel files with company data.
    
    Supports 1000-5000 companies at once.
    
    Expected columns for Annual predictions:
    - stock_symbol, company_name, market_cap, sector, reporting_year
    - long_term_debt_to_total_capital, total_debt_to_ebitda, net_income_margin
    - ebit_to_interest_expense, return_on_assets
    
    Expected columns for Quarterly predictions:
    - stock_symbol, company_name, market_cap, sector, reporting_year, reporting_quarter
    - total_debt_to_ebitda, sga_margin, long_term_debt_to_total_capital, return_on_capital
    """
    start_time = time.time()
    
    try:
        if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
            raise HTTPException(
                status_code=400,
                detail="File must be CSV (.csv) or Excel (.xlsx, .xls)"
            )
        
        content = await file.read()
        
        try:
            if file.filename.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(content))
            else:
                df = pd.read_excel(io.BytesIO(content))
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error reading file: {str(e)}"
            )
        
        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="File contains no data"
            )
        
        if len(df) > 5000:
            raise HTTPException(
                status_code=400,
                detail=f"File contains {len(df)} rows. Maximum allowed is 5000 companies."
            )
        
        if prediction_type == "annual":
            required_columns = [
                'stock_symbol', 'company_name', 'long_term_debt_to_total_capital',
                'total_debt_to_ebitda', 'net_income_margin', 'ebit_to_interest_expense', 'return_on_assets'
            ]
        elif prediction_type == "quarterly":
            required_columns = [
                'stock_symbol', 'company_name', 'reporting_year', 'reporting_quarter',
                'total_debt_to_ebitda', 'sga_margin', 'long_term_debt_to_total_capital', 'return_on_capital'
            ]
        else:
            raise HTTPException(
                status_code=400,
                detail="prediction_type must be 'annual' or 'quarterly'"
            )
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {missing_columns}"
            )
        
        company_service = CompanyService(db)
        results = []
        successful_predictions = 0
        failed_predictions = 0
        
        for index, row in df.iterrows():
            try:
                company = company_service.create_company(
                    symbol=str(row['stock_symbol']).strip().upper(),
                    name=str(row['company_name']).strip(),
                    market_cap=safe_float(row.get('market_cap', 1000000000)),
                    sector=str(row.get('sector', 'Unknown')).strip()
                )
                
                if prediction_type == "annual":
                    financial_data = {
                        "long_term_debt_to_total_capital": safe_float(row['long_term_debt_to_total_capital']),
                        "total_debt_to_ebitda": safe_float(row['total_debt_to_ebitda']),
                        "net_income_margin": safe_float(row['net_income_margin']),
                        "ebit_to_interest_expense": safe_float(row['ebit_to_interest_expense']),
                        "return_on_assets": safe_float(row['return_on_assets'])
                    }
                    
                    prediction_result = ml_model.predict_default_probability(financial_data)
                    
                    if "error" in prediction_result:
                        raise Exception(prediction_result["error"])
                    
                    prediction = company_service.create_annual_prediction(
                        company=company,
                        financial_data=financial_data,
                        prediction_results=prediction_result,
                        reporting_year=str(row.get('reporting_year', '2024')),
                        reporting_quarter=str(row['reporting_quarter'])
                    )
                    
                    result_item = BulkPredictionItem(
                        stock_symbol=company.symbol,
                        company_name=company.name,
                        sector=company.sector,
                        market_cap=safe_float(company.market_cap) if company.market_cap else None,
                        prediction={
                            "id": str(prediction.id),
                            "type": "annual",
                            "probability": safe_float(prediction.probability),
                            "primary_probability": safe_float(prediction.probability),
                            "risk_level": prediction.risk_level,
                            "confidence": safe_float(prediction.confidence)
                        },
                        status="success"
                    )
                    
                elif prediction_type == "quarterly":
                    financial_data = {
                        "total_debt_to_ebitda": safe_float(row['total_debt_to_ebitda']),
                        "sga_margin": safe_float(row['sga_margin']),
                        "long_term_debt_to_total_capital": safe_float(row['long_term_debt_to_total_capital']),
                        "return_on_capital": safe_float(row['return_on_capital'])
                    }
                    
                    prediction_result = quarterly_ml_model.predict_default_probability(financial_data)
                    
                    if "error" in prediction_result:
                        raise Exception(prediction_result["error"])
                    
                    prediction = company_service.create_quarterly_prediction(
                        company=company,
                        financial_data=financial_data,
                        prediction_results=prediction_result,
                        reporting_year=str(row['reporting_year']),
                        reporting_quarter=str(row['reporting_quarter'])
                    )
                    
                    result_item = BulkPredictionItem(
                        stock_symbol=company.symbol,
                        company_name=company.name,
                        sector=company.sector,
                        market_cap=safe_float(company.market_cap) if company.market_cap else None,
                        prediction={
                            "id": str(prediction.id),
                            "type": "quarterly",
                            "probabilities": {
                                "logistic": safe_float(prediction.logistic_probability),
                                "gbm": safe_float(prediction.gbm_probability),
                                "ensemble": safe_float(prediction.ensemble_probability)
                            },
                            "primary_probability": safe_float(prediction.ensemble_probability),
                            "risk_level": prediction.risk_level,
                            "confidence": safe_float(prediction.confidence)
                        },
                        status="success"
                    )
                
                successful_predictions += 1
                
            except Exception as e:
                result_item = BulkPredictionItem(
                    stock_symbol=str(row.get('stock_symbol', 'UNKNOWN')),
                    company_name=str(row.get('company_name', 'Unknown Company')),
                    sector=str(row.get('sector', 'Unknown')),
                    market_cap=safe_float(row.get('market_cap', 0)) if row.get('market_cap') else None,
                    prediction={},
                    status="failed",
                    error_message=str(e)
                )
                failed_predictions += 1
            
            results.append(result_item)
        
        processing_time = time.time() - start_time
        
        return BulkPredictionResponse(
            success=True,
            message=f"Bulk prediction completed. {successful_predictions} successful, {failed_predictions} failed.",
            total_companies=len(df),
            successful_predictions=successful_predictions,
            failed_predictions=failed_predictions,
            results=results,
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Bulk prediction failed",
                "details": str(e)
            }
        )

@router.post("/bulk-predict-async", response_model=BulkJobResponse)
async def bulk_predict_async(
    file: UploadFile = File(...),
    prediction_type: str = "annual",
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Submit a bulk prediction job that runs in the background.
    Returns a job ID that can be used to check status and retrieve results.
    
    This endpoint is recommended for very large files (>1000 companies) to avoid timeouts.
    For smaller files, use the synchronous /bulk-predict endpoint.
    
    Supports CSV and Excel files with 1000-50000 companies.
    """
    
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(
            status_code=400,
            detail="File must be Excel (.xlsx, .xls) or CSV (.csv) format"
        )
    
    if prediction_type not in ["annual", "quarterly"]:
        raise HTTPException(
            status_code=400,
            detail="prediction_type must be 'annual' or 'quarterly'"
        )
    
    try:
        contents = await file.read()
        
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(contents))
        
        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="File is empty"
            )
        
        company_count = len(df)
        
        base_required = ['stock_symbol', 'company_name']
        
        if prediction_type == "annual":
            required_columns = base_required + [
                'long_term_debt_to_total_capital', 'total_debt_to_ebitda', 
                'net_income_margin', 'ebit_to_interest_expense', 'return_on_assets'
            ]
        else:  # quarterly
            required_columns = base_required + [
                'reporting_year', 'reporting_quarter', 'total_debt_to_ebitda', 
                'sga_margin', 'long_term_debt_to_total_capital', 'return_on_capital'
            ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        file_content_b64 = base64.b64encode(contents).decode('utf-8')
        
        from ..tasks import process_bulk_normalized_task
        task = process_bulk_normalized_task.delay(file_content_b64, file.filename, prediction_type)
        
        if company_count <= 100:
            estimated_time = f"{company_count * 2:.0f}-{company_count * 4:.0f} seconds"
        elif company_count <= 1000:
            estimated_time = f"{company_count * 1.5 / 60:.1f}-{company_count * 3 / 60:.1f} minutes"
        else:
            estimated_time = f"{company_count * 1 / 60:.1f}-{company_count * 2 / 60:.1f} minutes"
        
        return BulkJobResponse(
            success=True,
            message=f"Bulk {prediction_type} prediction job submitted successfully. Processing {company_count} companies in background.",
            job_id=task.id,
            status="PENDING",
            filename=file.filename,
            estimated_processing_time=estimated_time
        )
        
    except pd.errors.EmptyDataError:
        raise HTTPException(
            status_code=400,
            detail="File is empty or contains no data"
        )
    except pd.errors.ParserError as e:
        raise HTTPException(
            status_code=400,
            detail=f"File parsing error: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to submit bulk prediction job",
                "details": str(e)
            }
        )


@router.get("/job-status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_verified_user)
):
    """
    Check the status of a bulk prediction job.
    
    Status values:
    - PENDING: Job is waiting to be processed
    - PROGRESS: Job is currently being processed
    - SUCCESS: Job completed successfully
    - FAILURE: Job failed
    """
    try:
        from ..celery_app import celery_app
        
        task_result = celery_app.AsyncResult(job_id)
        
        if task_result.state == "PENDING":
            return JobStatusResponse(
                success=True,
                job_id=job_id,
                status="PENDING",
                message="Job is waiting to be processed...",
                progress=None,
                result=None
            )
        
        elif task_result.state == "PROGRESS":
            progress_info = task_result.info or {}
            return JobStatusResponse(
                success=True,
                job_id=job_id,
                status="PROGRESS",
                message=progress_info.get("status", "Processing..."),
                progress={
                    "current": progress_info.get("current", 0),
                    "total": progress_info.get("total", 0),
                    "filename": progress_info.get("filename", ""),
                    "successful": progress_info.get("successful", 0),
                    "failed": progress_info.get("failed", 0),
                    "prediction_type": progress_info.get("prediction_type", "unknown")
                },
                result=None
            )
        
        elif task_result.state == "SUCCESS":
            result_data = task_result.result
            return JobStatusResponse(
                success=True,
                job_id=job_id,
                status="SUCCESS",
                message="Job completed successfully",
                progress=None,
                result=result_data
            )
        
        elif task_result.state == "FAILURE":
            error_info = task_result.info or {}
            return JobStatusResponse(
                success=False,
                job_id=job_id,
                status="FAILURE",
                message="Job failed",
                progress=None,
                result=None,
                error=error_info.get("error", str(task_result.info))
            )
        
        else:
            return JobStatusResponse(
                success=True,
                job_id=job_id,
                status=task_result.state,
                message=f"Job status: {task_result.state}",
                progress=None,
                result=None
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to get job status",
                "details": str(e)
            }
        )


@router.get("/job-result/{job_id}")
async def get_job_result(
    job_id: str,
    current_user: User = Depends(get_current_verified_user)
):
    """
    Get the complete result of a completed bulk prediction job.
    Only returns results for successfully completed jobs.
    """
    try:
        from ..celery_app import celery_app
        
        task_result = celery_app.AsyncResult(job_id)
        
        if task_result.state == "SUCCESS":
            return task_result.result
        elif task_result.state == "PENDING":
            raise HTTPException(
                status_code=202,
                detail="Job is still pending. Please check job status."
            )
        elif task_result.state == "PROGRESS":
            raise HTTPException(
                status_code=202,
                detail="Job is still in progress. Please check job status."
            )
        elif task_result.state == "FAILURE":
            raise HTTPException(
                status_code=400,
                detail="Job failed. Check job status for error details."
            )
        else:
            raise HTTPException(
                status_code=404,
                detail="Job not found or in unknown state"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to get job result",
                "details": str(e)
            }
        )


@router.put("/update/{company_id}")
async def update_company_prediction(
    company_id: str,
    request: PredictionUpdateRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Update company data and recalculate predictions if financial ratios change"""
    try:
        try:
            uuid.UUID(company_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid company ID format. Must be a valid UUID."
            )

        company_service = CompanyService(db)
        company = company_service.get_company_by_id(company_id)
        
        if not company:
            raise HTTPException(
                status_code=404,
                detail="Company not found"
            )

        if request.company_name:
            company.name = request.company_name
        if request.market_cap is not None:
            company.market_cap = request.market_cap
        if request.sector:
            company.sector = request.sector
        
        company.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(company)
        
        response_data = {
            "success": True,
            "message": "Company updated successfully",
            "company": {
                "id": str(company.id),
                "symbol": company.symbol,
                "name": company.name,
                "market_cap": safe_float(company.market_cap) if company.market_cap else None,
                "sector": company.sector,
                "updated_at": serialize_datetime(company.updated_at)
            }
        }
        
        updated_prediction = None
        if request.prediction_type and request.reporting_year:
            
            if request.prediction_type == "annual":
                if not all([
                    request.long_term_debt_to_total_capital is not None,
                    request.total_debt_to_ebitda is not None,
                    request.net_income_margin is not None,
                    request.ebit_to_interest_expense is not None,
                    request.return_on_assets is not None
                ]):
                    raise HTTPException(
                        status_code=400,
                        detail="All annual prediction fields are required for annual prediction update"
                    )
                
                existing_prediction = company_service.get_annual_prediction(
                    company.id, request.reporting_year
                )
                
                if existing_prediction:
                    db.delete(existing_prediction)
                    db.flush() 
                
                financial_data = {
                    "long_term_debt_to_total_capital": request.long_term_debt_to_total_capital,
                    "total_debt_to_ebitda": request.total_debt_to_ebitda,
                    "net_income_margin": request.net_income_margin,
                    "ebit_to_interest_expense": request.ebit_to_interest_expense,
                    "return_on_assets": request.return_on_assets
                }
                
                prediction_result = ml_model.predict_default_probability(financial_data)
                
                if "error" in prediction_result:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Annual prediction failed: {prediction_result['error']}"
                    )
                
                updated_prediction = company_service.create_annual_prediction(
                    company=company,
                    financial_data=financial_data,
                    prediction_results=prediction_result,
                    reporting_year=request.reporting_year,
                    reporting_quarter=request.reporting_quarter
                )
                
                response_data["updated_prediction"] = {
                    "type": "annual",
                    "id": str(updated_prediction.id),
                    "reporting_year": updated_prediction.reporting_year,
                    "reporting_quarter": updated_prediction.reporting_quarter,
                    "probability": safe_float(updated_prediction.probability),
                    "primary_probability": safe_float(updated_prediction.probability),
                    "risk_level": updated_prediction.risk_level,
                    "confidence": safe_float(updated_prediction.confidence),
                    "action": "replaced" if existing_prediction else "created",
                    "financial_ratios": {
                        "long_term_debt_to_total_capital": safe_float(updated_prediction.long_term_debt_to_total_capital),
                        "total_debt_to_ebitda": safe_float(updated_prediction.total_debt_to_ebitda),
                        "net_income_margin": safe_float(updated_prediction.net_income_margin),
                        "ebit_to_interest_expense": safe_float(updated_prediction.ebit_to_interest_expense),
                        "return_on_assets": safe_float(updated_prediction.return_on_assets)
                    }
                }
                
            elif request.prediction_type == "quarterly":
                if not all([
                    request.total_debt_to_ebitda is not None,
                    request.sga_margin is not None,
                    request.long_term_debt_to_total_capital is not None,
                    request.return_on_capital is not None,
                    request.reporting_quarter is not None
                ]):
                    raise HTTPException(
                        status_code=400,
                        detail="All quarterly prediction fields are required for quarterly prediction update"
                    )
                
                existing_prediction = company_service.get_quarterly_prediction(
                    company.id, request.reporting_year, request.reporting_quarter
                )
                
                if existing_prediction:
                    db.delete(existing_prediction)
                    db.flush()  
                
                financial_data = {
                    "total_debt_to_ebitda": request.total_debt_to_ebitda,
                    "sga_margin": request.sga_margin,
                    "long_term_debt_to_total_capital": request.long_term_debt_to_total_capital,
                    "return_on_capital": request.return_on_capital
                }
                
                prediction_result = quarterly_ml_model.predict_default_probability(financial_data)
                
                if "error" in prediction_result:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Quarterly prediction failed: {prediction_result['error']}"
                    )
                
                updated_prediction = company_service.create_quarterly_prediction(
                    company=company,
                    financial_data=financial_data,
                    prediction_results=prediction_result,
                    reporting_year=request.reporting_year,
                    reporting_quarter=request.reporting_quarter
                )
                
                response_data["updated_prediction"] = {
                    "type": "quarterly",
                    "id": str(updated_prediction.id),
                    "reporting_year": updated_prediction.reporting_year,
                    "reporting_quarter": updated_prediction.reporting_quarter,
                    "probabilities": {
                        "logistic": safe_float(updated_prediction.logistic_probability),
                        "gbm": safe_float(updated_prediction.gbm_probability),
                        "ensemble": safe_float(updated_prediction.ensemble_probability)
                    },
                    "primary_probability": safe_float(updated_prediction.ensemble_probability),
                    "risk_level": updated_prediction.risk_level,
                    "confidence": safe_float(updated_prediction.confidence),
                    "action": "replaced" if existing_prediction else "created",
                    "financial_ratios": {
                        "total_debt_to_ebitda": safe_float(updated_prediction.total_debt_to_ebitda),
                        "sga_margin": safe_float(updated_prediction.sga_margin),
                        "long_term_debt_to_total_capital": safe_float(updated_prediction.long_term_debt_to_total_capital),
                        "return_on_capital": safe_float(updated_prediction.return_on_capital)
                    }
                }
            
            else:
                raise HTTPException(
                    status_code=400,
                    detail="prediction_type must be 'annual' or 'quarterly'"
                )
        
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to update company",
                "details": str(e)
            }
        )


@router.delete("/delete/{company_id}")
async def delete_company_and_predictions(
    company_id: str,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Delete a company and all its predictions (annual and quarterly)"""
    try:
        try:
            uuid.UUID(company_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid company ID format. Must be a valid UUID."
            )

        company_service = CompanyService(db)
        company = company_service.get_company_by_id(company_id)
        
        if not company:
            raise HTTPException(
                status_code=404,
                detail="Company not found"
            )

        company_symbol = company.symbol
        company_name = company.name
        annual_predictions_count = len(company.annual_predictions)
        quarterly_predictions_count = len(company.quarterly_predictions)

        db.delete(company)
        db.commit()
        
        return {
            "success": True,
            "message": f"Company '{company_name}' ({company_symbol}) and all predictions deleted successfully",
            "deleted_company": {
                "id": company_id,
                "symbol": company_symbol,
                "name": company_name,
                "annual_predictions_deleted": annual_predictions_count,
                "quarterly_predictions_deleted": quarterly_predictions_count
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to delete company",
                "details": str(e)
            }
        )

@router.delete("/predictions/annual/{prediction_id}")
async def delete_annual_prediction(
    prediction_id: str,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Delete a specific annual prediction"""
    try:
        try:
            uuid.UUID(prediction_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid prediction ID format. Must be a valid UUID."
            )

        prediction = db.query(AnnualPrediction).filter(AnnualPrediction.id == prediction_id).first()
        
        if not prediction:
            raise HTTPException(
                status_code=404,
                detail="Annual prediction not found"
            )

        db.delete(prediction)
        db.commit()
        
        return {
            "success": True,
            "message": "Annual prediction deleted successfully",
            "deleted_prediction": {
                "id": prediction_id,
                "type": "annual"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to delete annual prediction",
                "details": str(e)
            }
        )

@router.delete("/predictions/quarterly/{prediction_id}")
async def delete_quarterly_prediction(
    prediction_id: str,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Delete a specific quarterly prediction"""
    try:
        try:
            uuid.UUID(prediction_id)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid prediction ID format. Must be a valid UUID."
            )

        prediction = db.query(QuarterlyPrediction).filter(QuarterlyPrediction.id == prediction_id).first()
        
        if not prediction:
            raise HTTPException(
                status_code=404,
                detail="Quarterly prediction not found"
            )

        db.delete(prediction)
        db.commit()
        
        return {
            "success": True,
            "message": "Quarterly prediction deleted successfully",
            "deleted_prediction": {
                "id": prediction_id,
                "type": "quarterly"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to delete quarterly prediction",
                "details": str(e)
            }
        )

@router.post("/predict-default-rate")
async def predict_default_rate_legacy(
    request: AnnualPredictionRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    return await predict_annual_default_rate(request, current_user, db)

@router.post("/quarterly-bulk-predict", response_model=QuarterlyBulkPredictionResponse)
async def quarterly_bulk_predict_from_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Dedicated quarterly bulk prediction endpoint.
    
    Supports 1000-5000 companies at once for quarterly predictions.
    
    Expected columns:
    - stock_symbol, company_name, reporting_year, reporting_quarter
    - total_debt_to_ebitda, sga_margin, long_term_debt_to_total_capital, return_on_capital
    - Optional: market_cap, sector
    """
    start_time = time.time()
    
    try:
        if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
            raise HTTPException(
                status_code=400,
                detail="File must be CSV (.csv) or Excel (.xlsx, .xls)"
            )
        
        content = await file.read()
        
        try:
            if file.filename.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(content))
            else:
                df = pd.read_excel(io.BytesIO(content))
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error reading file: {str(e)}"
            )
        
        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="File contains no data"
            )
        
        if len(df) > 5000:
            raise HTTPException(
                status_code=400,
                detail="File too large. Maximum 5000 companies per upload."
            )
        
        if len(df) < 1:
            raise HTTPException(
                status_code=400,
                detail="File must contain at least 1 company"
            )
        
        # Validate required columns for quarterly predictions
        required_columns = [
            'stock_symbol', 'company_name', 'reporting_year', 'reporting_quarter',
            'total_debt_to_ebitda', 'sga_margin', 'long_term_debt_to_total_capital', 'return_on_capital'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        company_service = CompanyService(db)
        results = []
        processed_count = 0
        error_count = 0
        skipped_count = 0
        
        # Process each row
        for index, row in df.iterrows():
            try:
                # Validate required fields
                stock_symbol = str(row['stock_symbol']).strip()
                company_name = str(row['company_name']).strip()
                reporting_year = str(row['reporting_year']).strip()
                reporting_quarter = str(row['reporting_quarter']).strip()
                
                if not all([stock_symbol, company_name, reporting_year, reporting_quarter]):
                    results.append(QuarterlyBulkPredictionItem(
                        stock_symbol=stock_symbol,
                        company_name=company_name,
                        reporting_year=reporting_year,
                        reporting_quarter=reporting_quarter,
                        success=False,
                        error="Missing required fields"
                    ))
                    error_count += 1
                    continue
                
                # Get or create company
                company = company_service.get_company_by_symbol(stock_symbol)
                if not company:
                    market_cap = safe_float(row.get('market_cap'))
                    sector = str(row.get('sector', '')).strip() or None
                    
                    company = company_service.create_company(
                        symbol=stock_symbol,
                        name=company_name,
                        market_cap=market_cap,
                        sector=sector
                    )
                
                # Check if prediction already exists
                existing_prediction = company_service.get_quarterly_prediction(
                    company.id, reporting_year, reporting_quarter
                )
                
                if existing_prediction:
                    results.append(QuarterlyBulkPredictionItem(
                        stock_symbol=stock_symbol,
                        company_name=company_name,
                        reporting_year=reporting_year,
                        reporting_quarter=reporting_quarter,
                        success=False,
                        error=f"Quarterly prediction for {stock_symbol} Q{reporting_quarter} {reporting_year} already exists"
                    ))
                    skipped_count += 1
                    continue
                
                # Prepare financial ratios for quarterly prediction
                financial_ratios = {
                    "total_debt_to_ebitda": safe_float(row['total_debt_to_ebitda']),
                    "sga_margin": safe_float(row['sga_margin']),
                    "long_term_debt_to_total_capital": safe_float(row['long_term_debt_to_total_capital']),
                    "return_on_capital": safe_float(row['return_on_capital'])
                }
                
                # Validate financial ratios
                missing_ratios = [k for k, v in financial_ratios.items() if v is None]
                if missing_ratios:
                    results.append(QuarterlyBulkPredictionItem(
                        stock_symbol=stock_symbol,
                        company_name=company_name,
                        reporting_year=reporting_year,
                        reporting_quarter=reporting_quarter,
                        success=False,
                        error=f"Missing financial ratios: {', '.join(missing_ratios)}"
                    ))
                    error_count += 1
                    continue
                
                # Get prediction from quarterly ML model
                prediction_result = quarterly_ml_model.predict_default_probability(financial_ratios)
                
                if "error" in prediction_result:
                    results.append(QuarterlyBulkPredictionItem(
                        stock_symbol=stock_symbol,
                        company_name=company_name,
                        reporting_year=reporting_year,
                        reporting_quarter=reporting_quarter,
                        success=False,
                        error=f"Quarterly prediction failed: {prediction_result['error']}"
                    ))
                    error_count += 1
                    continue
                
                # Save quarterly prediction to database
                prediction = company_service.create_quarterly_prediction(
                    company=company,
                    financial_data=financial_ratios,
                    prediction_results=prediction_result,
                    reporting_year=reporting_year,
                    reporting_quarter=reporting_quarter
                )
                
                results.append(QuarterlyBulkPredictionItem(
                    stock_symbol=stock_symbol,
                    company_name=company_name,
                    reporting_year=reporting_year,
                    reporting_quarter=reporting_quarter,
                    success=True,
                    prediction_id=str(prediction.id),
                    default_probability=prediction_result["ensemble_probability"],
                    risk_level=prediction_result["risk_level"],
                    confidence=prediction_result["confidence"],
                    financial_ratios=financial_ratios
                ))
                processed_count += 1
                
            except Exception as e:
                results.append(QuarterlyBulkPredictionItem(
                    stock_symbol=row.get('stock_symbol', 'Unknown'),
                    company_name=row.get('company_name', 'Unknown'),
                    reporting_year=row.get('reporting_year', 'Unknown'),
                    reporting_quarter=row.get('reporting_quarter', 'Unknown'),
                    success=False,
                    error=f"Processing error: {str(e)}"
                ))
                error_count += 1
        
        end_time = time.time()
        processing_time = round(end_time - start_time, 2)
        
        return QuarterlyBulkPredictionResponse(
            success=True,
            message=f"Quarterly bulk prediction completed. Processed: {processed_count}, Errors: {error_count}, Skipped: {skipped_count}",
            total_records=len(df),
            processed_records=processed_count,
            error_records=error_count,
            skipped_records=skipped_count,
            processing_time_seconds=processing_time,
            results=results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Quarterly bulk prediction failed",
                "details": str(e)
            }
        )

@router.post("/quarterly-bulk-predict-async", response_model=QuarterlyBulkJobResponse)
async def quarterly_bulk_predict_async(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Submit a quarterly bulk prediction job that runs in the background.
    Returns a job ID that can be used to check status and retrieve results.
    
    This endpoint is recommended for very large files (>1000 companies) to avoid timeouts.
    For smaller files, use the synchronous /quarterly-bulk-predict endpoint.
    
    Expected columns:
    - stock_symbol, company_name, reporting_year, reporting_quarter
    - total_debt_to_ebitda, sga_margin, long_term_debt_to_total_capital, return_on_capital
    - Optional: market_cap, sector
    """
    
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(
            status_code=400,
            detail="File must be Excel (.xlsx, .xls) or CSV (.csv) format"
        )
    
    try:
        contents = await file.read()
        
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(contents))
        
        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="File is empty"
            )
        
        company_count = len(df)
        
        # Validate required columns for quarterly predictions
        required_columns = [
            'stock_symbol', 'company_name', 'reporting_year', 'reporting_quarter',
            'total_debt_to_ebitda', 'sga_margin', 'long_term_debt_to_total_capital', 'return_on_capital'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        file_content_b64 = base64.b64encode(contents).decode('utf-8')
        
        # Use quarterly task
        from ..tasks import process_quarterly_bulk_task
        task = process_quarterly_bulk_task.delay(file_content_b64, file.filename)
        
        if company_count <= 100:
            estimated_time = f"{company_count * 2:.0f}-{company_count * 4:.0f} seconds"
        elif company_count <= 1000:
            estimated_time = f"{company_count * 1.5 / 60:.1f}-{company_count * 3 / 60:.1f} minutes"
        else:
            estimated_time = f"{company_count * 1 / 60:.1f}-{company_count * 2 / 60:.1f} minutes"
        
        return QuarterlyBulkJobResponse(
            success=True,
            message=f"Quarterly bulk prediction job submitted successfully. Processing {company_count} companies in background.",
            job_id=task.id,
            status="PENDING",
            filename=file.filename,
            estimated_processing_time=estimated_time
        )
        
    except pd.errors.EmptyDataError:
        raise HTTPException(
            status_code=400,
            detail="File is empty or contains no data"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Quarterly bulk prediction job failed",
                "details": str(e)
            }
        )
