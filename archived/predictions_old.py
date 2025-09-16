from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from ..database import get_db, User, Company, AnnualPrediction, QuarterlyPrediction
from ..schemas import (
    PredictionRequest, PredictionResponse, BulkPredictionResponse, 
    BulkPredictionItem, BulkJobResponse, JobStatusResponse,
    PredictionUpdateRequest, DatabaseResetRequest, DatabaseResetResponse,
    QuarterlyPredictionRequest, AnnualPredictionRequest,
    UnifiedPredictionRequest, CompanyWithPredictionsResponse
)
from ..services import CompanyService, PredictionService, DatabaseService
from ..ml_service import ml_model
from ..quarterly_ml_service import quarterly_ml_model
from ..auth import get_current_verified_user, get_admin_user
from typing import Dict, List
from datetime import datetime
import pandas as pd
import io
import time
import os
import uuid
import base64
from pathlib import Path

router = APIRouter()


def serialize_datetime(dt):
    """Helper function to serialize datetime objects"""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    return dt


@router.post("/predict-annual", response_model=PredictionResponse)
async def predict_annual_default_rate(
    request: AnnualPredictionRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Create annual prediction for a company"""
    try:
        company_service = CompanyService(db)

        # Check if company already exists
        company = company_service.get_company_by_symbol(request.stock_symbol)
        
        if not company:
            # Create new company
            company = company_service.create_company(
                symbol=request.stock_symbol,
                name=request.company_name,
                market_cap=request.market_cap,
                sector=request.sector
            )

        # Check if annual prediction already exists for this reporting year
        existing_prediction = company_service.get_annual_prediction(
            company.id, request.reporting_year
        )
        
        if existing_prediction:
            raise HTTPException(
                status_code=400,
                detail=f"Annual prediction for {request.stock_symbol} in {request.reporting_year} already exists"
            )

        # Prepare data for ML model
        ratios = {
            "long_term_debt_to_total_capital": request.long_term_debt_to_total_capital,
            "total_debt_to_ebitda": request.total_debt_to_ebitda,
            "net_income_margin": request.net_income_margin,
            "ebit_to_interest_expense": request.ebit_to_interest_expense,
            "return_on_assets": request.return_on_assets
        }

        # Get ML prediction
        prediction_result = ml_model.predict_default_probability(ratios)

        if "error" in prediction_result:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Prediction failed",
                    "details": prediction_result["error"]
                }
            )

        # Create annual prediction
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
                "market_cap": float(company.market_cap) if company.market_cap else None,
                "sector": company.sector,
                "prediction": {
                    "id": str(annual_prediction.id),
                    "type": "annual",
                    "reporting_year": annual_prediction.reporting_year,
                    "ratios": {
                        "long_term_debt_to_total_capital": float(annual_prediction.long_term_debt_to_total_capital),
                        "total_debt_to_ebitda": float(annual_prediction.total_debt_to_ebitda),
                        "net_income_margin": float(annual_prediction.net_income_margin),
                        "ebit_to_interest_expense": float(annual_prediction.ebit_to_interest_expense),
                        "return_on_assets": float(annual_prediction.return_on_assets)
                    },
                    "probability": float(annual_prediction.probability),
                    "risk_level": annual_prediction.risk_level,
                    "confidence": float(annual_prediction.confidence),
                    "created_at": annual_prediction.created_at.isoformat(),
                    "model_info": {
                        "model_type": "Annual Logistic Regression",
                        "features": list(ratios.keys())
                    }
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Annual prediction error: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "Annual prediction failed",
                "details": str(e)
            }
        )


@router.post("/predict-quarterly", response_model=PredictionResponse)
async def predict_quarterly_default_rate(
    request: QuarterlyPredictionRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Create quarterly prediction for a company"""
    try:
        company_service = CompanyService(db)

        # Check if company already exists
        company = company_service.get_company_by_symbol(request.stock_symbol)
        
        if not company:
            # Create new company
            company = company_service.create_company(
                symbol=request.stock_symbol,
                name=request.company_name,
                market_cap=request.market_cap,
                sector=request.sector
            )

        # Check if quarterly prediction already exists for this reporting period
        existing_prediction = company_service.get_quarterly_prediction(
            company.id, request.reporting_year, request.reporting_quarter
        )
        
        if existing_prediction:
            raise HTTPException(
                status_code=400,
                detail=f"Quarterly prediction for {request.stock_symbol} in {request.reporting_quarter} {request.reporting_year} already exists"
            )

        # Prepare data for ML model
        ratios = {
            "total_debt_to_ebitda": request.total_debt_to_ebitda,
            "sga_margin": request.sga_margin,
            "long_term_debt_to_total_capital": request.long_term_debt_to_total_capital,
            "return_on_capital": request.return_on_capital
        }

        # Get ML prediction
        prediction_result = quarterly_ml_model.predict_quarterly_default_probability(ratios)

        if "error" in prediction_result:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Quarterly prediction failed",
                    "details": prediction_result["error"]
                }
            )

        # Create quarterly prediction
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
                    "ratios": {
                        "total_debt_to_ebitda": float(quarterly_prediction.total_debt_to_ebitda),
                        "sga_margin": float(quarterly_prediction.sga_margin),
                        "long_term_debt_to_total_capital": float(quarterly_prediction.long_term_debt_to_total_capital),
                        "return_on_capital": float(quarterly_prediction.return_on_capital)
                    },
                    "logistic_probability": float(quarterly_prediction.logistic_probability),
                    "gbm_probability": float(quarterly_prediction.gbm_probability),
                    "ensemble_probability": float(quarterly_prediction.ensemble_probability),
                    "risk_level": quarterly_prediction.risk_level,
                    "confidence": float(quarterly_prediction.confidence),
                    "created_at": quarterly_prediction.created_at.isoformat(),
                    "model_info": {
                        "model_type": "Quarterly Ensemble (Logistic + GBM)",
                        "features": list(ratios.keys())
                    }
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Quarterly prediction error: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "Quarterly prediction failed",
                "details": str(e)
            }
        )

@router.post("/unified-predict", response_model=PredictionResponse)
async def unified_predict(
    request: UnifiedPredictionRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Unified endpoint for both annual and quarterly predictions"""
    try:
        if request.prediction_type == "annual":
            # Convert to annual request
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
            if not request.reporting_quarter:
                raise HTTPException(
                    status_code=400,
                    detail="reporting_quarter is required for quarterly predictions"
                )
            
            # Convert to quarterly request
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
                detail="prediction_type must be either 'annual' or 'quarterly'"
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Unified prediction error: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "Unified prediction failed",
                "details": str(e)
            }
        )


@router.get("/companies")
async def get_companies(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
    page: int = 1,
    limit: int = 100
):
    """Get all companies with their predictions"""
    try:
        company_service = CompanyService(db)
        result = company_service.get_companies_with_predictions(page=page, limit=limit)
        companies = result["companies"]
        pagination = result["pagination"]
        
        return {
            "success": True,
            "message": f"Retrieved {len(companies)} companies",
            "pagination": pagination,
            "companies": [
                {
                    "id": str(company.id),
                    "symbol": company.symbol,
                    "name": company.name,
                    "market_cap": float(company.market_cap) if company.market_cap else None,
                    "sector": company.sector,
                    "created_at": company.created_at.isoformat(),
                    "updated_at": company.updated_at.isoformat(),
                    "annual_predictions": [
                        {
                            "id": str(pred.id),
                            "reporting_year": pred.reporting_year,
                            "probability": float(pred.probability),
                            "risk_level": pred.risk_level,
                            "confidence": float(pred.confidence),
                            "created_at": pred.created_at.isoformat()
                        } for pred in company.annual_predictions
                    ],
                    "quarterly_predictions": [
                        {
                            "id": str(pred.id),
                            "reporting_year": pred.reporting_year,
                            "reporting_quarter": pred.reporting_quarter,
                            "ensemble_probability": float(pred.ensemble_probability),
                            "risk_level": pred.risk_level,
                            "confidence": float(pred.confidence),
                            "created_at": pred.created_at.isoformat()
                        } for pred in company.quarterly_predictions
                    ]
                } for company in companies
            ]
        }

    except Exception as e:
        print(f"Get companies error: {e}")
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
    """Get a specific company with all its predictions"""
    try:
        company_service = CompanyService(db)
        company = company_service.get_company_with_predictions(company_id)
        
        if not company:
            raise HTTPException(
                status_code=404,
                detail=f"Company with ID {company_id} not found"
            )
        
        return {
            "success": True,
            "message": "Company retrieved successfully",
            "company": {
                "id": str(company.id),
                "symbol": company.symbol,
                "name": company.name,
                "market_cap": float(company.market_cap) if company.market_cap else None,
                "sector": company.sector,
                "created_at": company.created_at.isoformat(),
                "updated_at": company.updated_at.isoformat(),
                "annual_predictions": [
                    {
                        "id": str(pred.id),
                        "reporting_year": pred.reporting_year,
                        "ratios": {
                            "long_term_debt_to_total_capital": float(pred.long_term_debt_to_total_capital),
                            "total_debt_to_ebitda": float(pred.total_debt_to_ebitda),
                            "net_income_margin": float(pred.net_income_margin),
                            "ebit_to_interest_expense": float(pred.ebit_to_interest_expense),
                            "return_on_assets": float(pred.return_on_assets)
                        },
                        "probability": float(pred.probability),
                        "risk_level": pred.risk_level,
                        "confidence": float(pred.confidence),
                        "created_at": pred.created_at.isoformat(),
                        "updated_at": pred.updated_at.isoformat()
                    } for pred in company.annual_predictions
                ],
                "quarterly_predictions": [
                    {
                        "id": str(pred.id),
                        "reporting_year": pred.reporting_year,
                        "reporting_quarter": pred.reporting_quarter,
                        "ratios": {
                            "total_debt_to_ebitda": float(pred.total_debt_to_ebitda),
                            "sga_margin": float(pred.sga_margin),
                            "long_term_debt_to_total_capital": float(pred.long_term_debt_to_total_capital),
                            "return_on_capital": float(pred.return_on_capital)
                        },
                        "logistic_probability": float(pred.logistic_probability),
                        "gbm_probability": float(pred.gbm_probability),
                        "ensemble_probability": float(pred.ensemble_probability),
                        "risk_level": pred.risk_level,
                        "confidence": float(pred.confidence),
                        "created_at": pred.created_at.isoformat(),
                        "updated_at": pred.updated_at.isoformat()
                    } for pred in company.quarterly_predictions
                ]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Get company by ID error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to retrieve company",
                "details": str(e)
            }
        )


# Legacy endpoint for backward compatibility
@router.post("/predict-default-rate", response_model=PredictionResponse)
async def predict_default_rate(
    request: PredictionRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Legacy endpoint - defaults to annual prediction for backward compatibility"""
    try:
        # Convert legacy request to annual request
        annual_request = AnnualPredictionRequest(
            stock_symbol=request.stock_symbol,
            company_name=request.company_name,
            market_cap=request.market_cap,
            sector=request.sector,
            reporting_year=request.reporting_year or "2024",  # Default year if not provided
            long_term_debt_to_total_capital=request.long_term_debt_to_total_capital,
            total_debt_to_ebitda=request.total_debt_to_ebitda,
            net_income_margin=request.net_income_margin,
            ebit_to_interest_expense=request.ebit_to_interest_expense,
            return_on_assets=request.return_on_assets
        )
        
        return await predict_annual_default_rate(annual_request, current_user, db)

    except HTTPException:
        raise
    except Exception as e:
        print(f"Legacy prediction error: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "Legacy prediction failed",
                "details": str(e)
            }
        )


@router.post("/bulk-predict", response_model=BulkPredictionResponse)
async def bulk_predict_from_excel(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Bulk prediction endpoint that accepts Excel files with company data.

    Expected Excel columns:
    - stock_symbol: Company stock symbol (required)
    - company_name: Company name (required)
    - market_cap: Market capitalization (optional)
    - sector: Company sector (optional)
    - reporting_year: Reporting year (optional, e.g., '2024')
    - reporting_quarter: Reporting quarter (optional, e.g., 'Q4')
    - long_term_debt_to_total_capital: Long-term debt / total capital (%) (required)
    - total_debt_to_ebitda: Total debt / EBITDA (required)
    - net_income_margin: Net income margin (%) (required)
    - ebit_to_interest_expense: EBIT / interest expense (required)
    - return_on_assets: Return on assets (%) (required)
    """
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="File must be an Excel file (.xlsx or .xls)"
        )
    
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="Excel file is empty"
            )
        
        # Required columns for the new single table schema
        required_columns = [
            'stock_symbol', 'company_name',
            'long_term_debt_to_total_capital', 'total_debt_to_ebitda', 
            'net_income_margin', 'ebit_to_interest_expense', 'return_on_assets'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        # Optional columns with defaults
        optional_columns = {
            'market_cap': 1000000000,  # Default 1B
            'sector': 'Unknown',
            'reporting_year': None,
            'reporting_quarter': None
        }
        
        # Add missing optional columns with defaults
        for col, default_value in optional_columns.items():
            if col not in df.columns:
                df[col] = default_value
        
        start_time = time.time()
        results = []
        successful_predictions = 0
        failed_predictions = 0
        
        company_service = CompanyService(db)
        
        for index, row in df.iterrows():
            try:
                # Validate required data
                stock_symbol = str(row['stock_symbol']).strip()
                company_name = str(row['company_name']).strip()
                
                if not stock_symbol or not company_name or stock_symbol.lower() == 'nan' or company_name.lower() == 'nan':
                    raise ValueError("Stock symbol and company name are required")
                
                # Convert financial data
                ratios = {
                    'long_term_debt_to_total_capital': float(row['long_term_debt_to_total_capital']),
                    'total_debt_to_ebitda': float(row['total_debt_to_ebitda']),
                    'net_income_margin': float(row['net_income_margin']),
                    'ebit_to_interest_expense': float(row['ebit_to_interest_expense']),
                    'return_on_assets': float(row['return_on_assets'])
                }
                
                # Handle optional fields
                market_cap = row.get('market_cap', 1000000000)
                if pd.isna(market_cap) or market_cap == 'nan':
                    market_cap = 1000000000
                else:
                    market_cap = float(market_cap)
                
                sector = row.get('sector', 'Unknown')
                if pd.isna(sector) or str(sector).lower() == 'nan':
                    sector = 'Unknown'
                else:
                    sector = str(sector).strip()
                
                reporting_year = row.get('reporting_year')
                if pd.isna(reporting_year) or str(reporting_year).lower() == 'nan':
                    reporting_year = None
                else:
                    reporting_year = str(reporting_year).strip()
                
                reporting_quarter = row.get('reporting_quarter')
                if pd.isna(reporting_quarter) or str(reporting_quarter).lower() == 'nan':
                    reporting_quarter = None
                else:
                    reporting_quarter = str(reporting_quarter).strip()
                
                # Generate prediction
                ratios_for_prediction = {
                    'long_term_debt_to_total_capital': ratios['long_term_debt_to_total_capital'],
                    'total_debt_to_ebitda': ratios['total_debt_to_ebitda'],
                    'net_income_margin': ratios['net_income_margin'],
                    'ebit_to_interest_expense': ratios['ebit_to_interest_expense'],
                    'return_on_assets': ratios['return_on_assets']
                }
                
                prediction_result = ml_model.predict_default_probability(ratios_for_prediction)
                
                # Create company data for single table
                company_data = CompanyCreate(
                    symbol=stock_symbol,
                    name=company_name,
                    market_cap=market_cap,
                    sector=sector,
                    reporting_year=reporting_year,
                    reporting_quarter=reporting_quarter,
                    long_term_debt_to_total_capital=ratios['long_term_debt_to_total_capital'],
                    total_debt_to_ebitda=ratios['total_debt_to_ebitda'],
                    net_income_margin=ratios['net_income_margin'],
                    ebit_to_interest_expense=ratios['ebit_to_interest_expense'],
                    return_on_assets=ratios['return_on_assets']
                )
                
                # Save to database using single table structure with upsert
                company = company_service.upsert_company(company_data, prediction_result)
                
                # Build successful response
                result_item = BulkPredictionItem(
                    stock_symbol=stock_symbol,
                    company_name=company_name,
                    sector=sector,
                    market_cap=market_cap,
                    prediction={
                        "id": str(company.id),
                        "probability": float(company.probability) if company.probability else None,
                        "risk_level": company.risk_level,
                        "confidence": float(company.confidence),
                        "predicted_at": company.predicted_at.isoformat(),
                        "financial_ratios": {
                            "long_term_debt_to_total_capital": float(company.long_term_debt_to_total_capital),
                            "total_debt_to_ebitda": float(company.total_debt_to_ebitda),
                            "net_income_margin": float(company.net_income_margin),
                            "ebit_to_interest_expense": float(company.ebit_to_interest_expense),
                            "return_on_assets": float(company.return_on_assets)
                        }
                    },
                    status="success",
                    error_message=None
                )
                
                successful_predictions += 1
                
            except Exception as e:
                # Handle individual company prediction failure
                result_item = BulkPredictionItem(
                    stock_symbol=str(row.get('stock_symbol', 'Unknown')),
                    company_name=str(row.get('company_name', 'Unknown')),
                    sector=str(row.get('sector', 'Unknown')),
                    market_cap=None,
                    prediction={},
                    status="failed",
                    error_message=str(e)
                )
                
                failed_predictions += 1
                print(f"Error processing row {index + 1}: {e}")
            
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
        
    except pd.errors.EmptyDataError:
        raise HTTPException(
            status_code=400,
            detail="Excel file is empty or contains no data"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process Excel file: {str(e)}"
        )

@router.post("/bulk-predict-async", response_model=BulkJobResponse)
async def bulk_predict_async(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Submit a bulk prediction job that runs in the background.
    Returns a job ID that can be used to check status and retrieve results.
    
    This endpoint is recommended for large Excel files (>100 companies) to avoid timeouts.
    """
    
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="File must be an Excel file (.xlsx or .xls)"
        )
    
    try:
        contents = await file.read()
        
        # Validate Excel file and columns
        df = pd.read_excel(io.BytesIO(contents))
        company_count = len(df)
        
        required_columns = [
            'stock_symbol', 'company_name',
            'long_term_debt_to_total_capital', 'total_debt_to_ebitda', 
            'net_income_margin', 'ebit_to_interest_expense', 'return_on_assets'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        # Submit background task
        file_content_b64 = base64.b64encode(contents).decode('utf-8')
        
        from ..tasks import process_bulk_excel_task
        task = process_bulk_excel_task.delay(file_content_b64, file.filename)
        
        estimated_time = f"{company_count * 1.5:.0f}-{company_count * 3:.0f} seconds"
        if company_count > 100:
            estimated_time = f"{company_count * 1.5 / 60:.1f}-{company_count * 3 / 60:.1f} minutes"
        
        return BulkJobResponse(
            success=True,
            message=f"Bulk prediction job submitted successfully. Processing {company_count} companies.",
            job_id=task.id,
            status="PENDING",
            filename=file.filename,
            estimated_processing_time=estimated_time
        )
                
    except pd.errors.EmptyDataError:
        raise HTTPException(
            status_code=400,
            detail="Excel file is empty or contains no data"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit bulk prediction job: {str(e)}"
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
        
        # Get task result
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
                    "failed": progress_info.get("failed", 0)
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
                result=result_data,
                completed_at=result_data.get("completed_at")
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


@router.put("/update/{company_id}", response_model=PredictionResponse)
async def update_prediction(
    company_id: str,
    request: PredictionUpdateRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Update company data and recalculate prediction if financial ratios are changed"""
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

        company_update_data = {}
        if request.company_name is not None:
            company_update_data['name'] = request.company_name
        if request.market_cap is not None:
            company_update_data['market_cap'] = request.market_cap
        if request.sector is not None:
            company_update_data['sector'] = request.sector
        if request.reporting_year is not None:
            company_update_data['reporting_year'] = request.reporting_year
        if request.reporting_quarter is not None:
            company_update_data['reporting_quarter'] = request.reporting_quarter

        ratios_update = {}
        ratios_provided = False
        
        ratios_update = {
            "long_term_debt_to_total_capital": request.long_term_debt_to_total_capital if request.long_term_debt_to_total_capital is not None else float(company.long_term_debt_to_total_capital),
            "total_debt_to_ebitda": request.total_debt_to_ebitda if request.total_debt_to_ebitda is not None else float(company.total_debt_to_ebitda),
            "net_income_margin": request.net_income_margin if request.net_income_margin is not None else float(company.net_income_margin),
            "ebit_to_interest_expense": request.ebit_to_interest_expense if request.ebit_to_interest_expense is not None else float(company.ebit_to_interest_expense),
            "return_on_assets": request.return_on_assets if request.return_on_assets is not None else float(company.return_on_assets)
        }

        if any([
            request.long_term_debt_to_total_capital is not None,
            request.total_debt_to_ebitda is not None,
            request.net_income_margin is not None,
            request.ebit_to_interest_expense is not None,
            request.return_on_assets is not None
        ]):
            ratios_provided = True

        prediction_result = None
        
        if ratios_provided:
            prediction_result = ml_model.predict_default_probability(ratios_update)
            
            if "error" in prediction_result:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Prediction calculation failed",
                        "details": prediction_result["error"]
                    }
                )

            company_update_data.update(ratios_update)

        updated_company = company_service.update_company(
            company_id, 
            company_update_data, 
            prediction_result
        )

        return {
            "success": True,
            "message": "Company data updated successfully" + (" with new prediction" if ratios_provided else ""),
            "company": {
                "id": str(updated_company.id),
                "symbol": updated_company.symbol,
                "name": updated_company.name,
                "market_cap": float(updated_company.market_cap) if updated_company.market_cap else None,
                "sector": updated_company.sector,
                "reporting_year": updated_company.reporting_year,
                "reporting_quarter": updated_company.reporting_quarter,
                "ratios": {
                    "long_term_debt_to_total_capital": float(updated_company.long_term_debt_to_total_capital),
                    "total_debt_to_ebitda": float(updated_company.total_debt_to_ebitda),
                    "net_income_margin": float(updated_company.net_income_margin),
                    "ebit_to_interest_expense": float(updated_company.ebit_to_interest_expense),
                    "return_on_assets": float(updated_company.return_on_assets)
                },
                "prediction": {
                    "probability": float(updated_company.probability) if updated_company.probability else None,
                    "risk_level": updated_company.risk_level,
                    "confidence": float(updated_company.confidence),
                    "predicted_at": updated_company.predicted_at.isoformat(),
                    "model_info": {
                        "model_type": "Updated Logistic Regression Model" if ratios_provided else "Existing Prediction",
                        "note": "Financial ratios were updated and prediction recalculated" if ratios_provided else "No financial ratio changes"
                    }
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Update prediction error: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to update prediction",
                "details": str(e)
            }
        )


@router.delete("/delete/{company_id}")
async def delete_company_prediction(
    company_id: str,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Delete all data for a company (company, financial ratios, and predictions)"""
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

        success = company_service.delete_company_data(company_id)
        
        if success:
            return {
                "success": True,
                "message": f"All data for company '{company_name}' ({company_symbol}) has been deleted successfully",
                "deleted_company": {
                    "id": company_id,
                    "symbol": company_symbol,
                    "name": company_name
                }
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete company data"
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Delete company error: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to delete company data",
                "details": str(e)
            }
        )


@router.post("/admin/reset-database", response_model=DatabaseResetResponse)
async def reset_database(
    request: DatabaseResetRequest,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Reset database (Admin only) - Reset complete database or specific table"""
    try:
        if not request.confirm_reset:
            raise HTTPException(
                status_code=400,
                detail="Reset confirmation required. Set 'confirm_reset' to true."
            )

        database_service = DatabaseService(db)
        
        result = database_service.reset_table(request.table_name)
        
        if request.table_name:
            message = f"Table '{request.table_name}' has been reset successfully. {result['affected_records']} records deleted."
        else:
            message = f"Complete database has been reset successfully. {result['affected_records']} total records deleted."

        return {
            "success": True,
            "message": message,
            "tables_reset": result["tables_reset"],
            "affected_records": result["affected_records"]
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Database reset error: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to reset database",
                "details": str(e)
            }
        )


# ===============================================
# QUARTERLY PREDICTION ENDPOINTS
# ===============================================

@router.post("/quarterly/predict-default-rate", response_model=PredictionResponse)
async def predict_quarterly_default_rate(
    request: QuarterlyPredictionRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Predict default rate for a company using Quarterly ML models (Logistic + GBM ensemble)"""
    try:
        company_service = CompanyService(db)

        # Check if company already exists with quarterly prediction
        existing_company = company_service.get_company_by_symbol_and_type(
            request.stock_symbol, "quarterly"
        )

        if existing_company:
            raise HTTPException(
                status_code=400,
                detail=f"Company with symbol '{request.stock_symbol}' already has quarterly prediction. Use update endpoint to modify."
            )

        # Prepare ratios for quarterly model (4 features)
        ratios = {
            "total_debt_to_ebitda": request.total_debt_to_ebitda,
            "sga_margin": request.sga_margin,
            "long_term_debt_to_total_capital": request.long_term_debt_to_total_capital,
            "return_on_capital": request.return_on_capital
        }

        # Get prediction from quarterly ML service
        prediction_result = quarterly_ml_model.predict_quarterly_default_probability(ratios)

        if "error" in prediction_result:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Quarterly prediction failed",
                    "details": prediction_result["error"]
                }
            )

        # Create CompanyCreate with quarterly data
        company_data = CompanyCreate(
            symbol=request.stock_symbol,
            name=request.company_name,
            market_cap=request.market_cap,
            sector=request.sector,
            reporting_year=request.reporting_year,
            reporting_quarter=request.reporting_quarter,
            prediction_type="quarterly",
            # Quarterly features
            total_debt_to_ebitda=request.total_debt_to_ebitda,
            sga_margin=request.sga_margin,
            long_term_debt_to_total_capital=request.long_term_debt_to_total_capital,
            return_on_capital=request.return_on_capital,
            # Annual features set to None
            net_income_margin=None,
            ebit_to_interest_expense=None,
            return_on_assets=None
        )
        
        company = company_service.create_quarterly_company(company_data, prediction_result)

        return {
            "success": True,
            "message": "Quarterly prediction generated using ensemble of Logistic Regression + Light GBM models",
            "company": {
                "id": str(company.id),
                "symbol": company.symbol,
                "name": company.name,
                "market_cap": float(company.market_cap) if company.market_cap else None,
                "sector": company.sector,
                "reporting_year": company.reporting_year,
                "reporting_quarter": company.reporting_quarter,
                "prediction_type": "quarterly",
                "ratios": {
                    "total_debt_to_ebitda": float(company.total_debt_to_ebitda),
                    "sga_margin": float(company.sga_margin),
                    "long_term_debt_to_total_capital": float(company.long_term_debt_to_total_capital),
                    "return_on_capital": float(company.return_on_capital)
                },
                "prediction": {
                    "logistic_probability": float(company.logistic_probability) if company.logistic_probability else None,
                    "gbm_probability": float(company.gbm_probability) if company.gbm_probability else None,
                    "ensemble_probability": float(company.probability) if company.probability else None,
                    "risk_level": company.risk_level,
                    "confidence": float(company.confidence),
                    "predicted_at": company.predicted_at.isoformat(),
                    "model_features": prediction_result.get("model_features", {}),
                    "model_info": {
                        "model_type": "Quarterly Ensemble (Logistic + Light GBM)",
                        "features": [
                            "Total debt / EBITDA",
                            "SG&A margin (%)", 
                            "Long-term debt / total capital (%)",
                            "Return on capital (%)"
                        ],
                        "ensemble_method": "Simple average of logistic and GBM predictions"
                    }
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Quarterly prediction error: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "Quarterly prediction failed",
                "details": str(e)
            }
        )

@router.put("/quarterly/update/{company_id}", response_model=PredictionResponse)
async def update_quarterly_prediction(
    company_id: str,
    request: QuarterlyPredictionRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Update quarterly company data and recalculate prediction"""
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

        if company.prediction_type != "quarterly":
            raise HTTPException(
                status_code=400,
                detail="Company is not a quarterly prediction type. Use annual update endpoint."
            )

        # Prepare update data
        company_update_data = {
            'name': request.company_name,
            'market_cap': request.market_cap,
            'sector': request.sector,
            'reporting_year': request.reporting_year,
            'reporting_quarter': request.reporting_quarter
        }

        # Prepare quarterly ratios
        ratios_update = {
            "total_debt_to_ebitda": request.total_debt_to_ebitda,
            "sga_margin": request.sga_margin,
            "long_term_debt_to_total_capital": request.long_term_debt_to_total_capital,
            "return_on_capital": request.return_on_capital
        }

        # Get new prediction
        prediction_result = quarterly_ml_model.predict_quarterly_default_probability(ratios_update)
        
        if "error" in prediction_result:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Quarterly prediction calculation failed",
                    "details": prediction_result["error"]
                }
            )

        # Update quarterly fields
        company_update_data.update({
            'total_debt_to_ebitda': request.total_debt_to_ebitda,
            'sga_margin': request.sga_margin,
            'long_term_debt_to_total_capital': request.long_term_debt_to_total_capital,
            'return_on_capital': request.return_on_capital
        })

        updated_company = company_service.update_quarterly_company(
            company_id, 
            company_update_data, 
            prediction_result
        )

        return {
            "success": True,
            "message": "Quarterly company data updated successfully with new prediction",
            "company": {
                "id": str(updated_company.id),
                "symbol": updated_company.symbol,
                "name": updated_company.name,
                "market_cap": float(updated_company.market_cap) if updated_company.market_cap else None,
                "sector": updated_company.sector,
                "reporting_year": updated_company.reporting_year,
                "reporting_quarter": updated_company.reporting_quarter,
                "prediction_type": "quarterly",
                "ratios": {
                    "total_debt_to_ebitda": float(updated_company.total_debt_to_ebitda),
                    "sga_margin": float(updated_company.sga_margin),
                    "long_term_debt_to_total_capital": float(updated_company.long_term_debt_to_total_capital),
                    "return_on_capital": float(updated_company.return_on_capital)
                },
                "prediction": {
                    "logistic_probability": float(updated_company.logistic_probability) if updated_company.logistic_probability else None,
                    "gbm_probability": float(updated_company.gbm_probability) if updated_company.gbm_probability else None,
                    "ensemble_probability": float(updated_company.probability) if updated_company.probability else None,
                    "risk_level": updated_company.risk_level,
                    "confidence": float(updated_company.confidence),
                    "predicted_at": updated_company.predicted_at.isoformat(),
                    "model_info": {
                        "model_type": "Updated Quarterly Ensemble (Logistic + Light GBM)",
                        "note": "Quarterly financial ratios updated and prediction recalculated"
                    }
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Update quarterly prediction error: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to update quarterly prediction",
                "details": str(e)
            }
        )

# ===============================================
# END QUARTERLY PREDICTION ENDPOINTS  
# ===============================================

# ===============================================
# UNIFIED PREDICTION ENDPOINT (RECOMMENDED)
# ===============================================

@router.post("/unified-predict", response_model=PredictionResponse)
async def unified_predict_default_rate(
    request: UnifiedPredictionRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """
    Unified prediction endpoint that handles both annual and quarterly predictions
    Based on prediction_type field, routes to appropriate ML model
    
    For annual: requires 5 fields (long_term_debt_to_total_capital, total_debt_to_ebitda, 
                                   net_income_margin, ebit_to_interest_expense, return_on_assets)
    For quarterly: requires 4 fields (total_debt_to_ebitda, sga_margin, 
                                     long_term_debt_to_total_capital, return_on_capital)
    """
    try:
        company_service = CompanyService(db)

        # Check if company already exists with this prediction type
        existing_company = company_service.get_company_by_symbol_and_type(
            request.stock_symbol, request.prediction_type
        )

        if existing_company:
            raise HTTPException(
                status_code=400,
                detail=f"Company '{request.stock_symbol}' already has {request.prediction_type} prediction. Use update endpoint to modify."
            )

        # Route to appropriate model based on prediction_type
        if request.prediction_type == "annual":
            # Validate annual fields are provided
            if not all([
                request.long_term_debt_to_total_capital is not None,
                request.total_debt_to_ebitda is not None,
                request.net_income_margin is not None,
                request.ebit_to_interest_expense is not None,
                request.return_on_assets is not None
            ]):
                raise HTTPException(
                    status_code=400,
                    detail="For annual predictions, all 5 annual financial ratios are required"
                )

            # Use annual ML model
            ratios = {
                "long_term_debt_to_total_capital": request.long_term_debt_to_total_capital,
                "total_debt_to_ebitda": request.total_debt_to_ebitda,
                "net_income_margin": request.net_income_margin,
                "ebit_to_interest_expense": request.ebit_to_interest_expense,
                "return_on_assets": request.return_on_assets
            }
            
            prediction_result = ml_model.predict_default_probability(ratios)
            model_info = {
                "model_type": "Annual Logistic Regression",
                "features": [
                    "Long-term debt / total capital (%)",
                    "Total debt / EBITDA", 
                    "Net income margin (%)",
                    "EBIT / interest expense",
                    "Return on assets (%)"
                ]
            }

        elif request.prediction_type == "quarterly":
            # Validate quarterly fields are provided
            if not all([
                request.total_debt_to_ebitda is not None,
                request.sga_margin is not None,
                request.long_term_debt_to_total_capital is not None,
                request.return_on_capital is not None
            ]):
                raise HTTPException(
                    status_code=400,
                    detail="For quarterly predictions, all 4 quarterly financial ratios are required"
                )

            # Use quarterly ML model
            ratios = {
                "total_debt_to_ebitda": request.total_debt_to_ebitda,
                "sga_margin": request.sga_margin,
                "long_term_debt_to_total_capital": request.long_term_debt_to_total_capital,
                "return_on_capital": request.return_on_capital
            }
            
            prediction_result = quarterly_ml_model.predict_quarterly_default_probability(ratios)
            model_info = {
                "model_type": "Quarterly Ensemble (Logistic + Light GBM)",
                "features": [
                    "Total debt / EBITDA",
                    "SG&A margin (%)", 
                    "Long-term debt / total capital (%)",
                    "Return on capital (%)"
                ],
                "ensemble_method": "Simple average of logistic and GBM predictions"
            }

        if "error" in prediction_result:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"{request.prediction_type.title()} prediction failed",
                    "details": prediction_result["error"]
                }
            )

        # Create company data based on prediction type
        company_data = CompanyCreate(
            symbol=request.stock_symbol,
            name=request.company_name,
            market_cap=request.market_cap,
            sector=request.sector,
            reporting_year=request.reporting_year,
            reporting_quarter=request.reporting_quarter,
            prediction_type=request.prediction_type,
            # Annual fields
            long_term_debt_to_total_capital=request.long_term_debt_to_total_capital,
            total_debt_to_ebitda=request.total_debt_to_ebitda,
            net_income_margin=request.net_income_margin,
            ebit_to_interest_expense=request.ebit_to_interest_expense,
            return_on_assets=request.return_on_assets,
            # Quarterly fields
            sga_margin=request.sga_margin,
            return_on_capital=request.return_on_capital
        )

        # Create company using appropriate method and structure response
        if request.prediction_type == "annual":
            company = company_service.create_company(company_data, prediction_result)
            
            response_ratios = {
                "long_term_debt_to_total_capital": float(company.long_term_debt_to_total_capital),
                "total_debt_to_ebitda": float(company.total_debt_to_ebitda),
                "net_income_margin": float(company.net_income_margin),
                "ebit_to_interest_expense": float(company.ebit_to_interest_expense),
                "return_on_assets": float(company.return_on_assets)
            }
            
            # Annual prediction response - single probability
            response_prediction = {
                "prediction_type": "annual",
                "probability": float(company.probability) if company.probability else None,
                "risk_level": company.risk_level,
                "confidence": float(company.confidence),
                "predicted_at": company.predicted_at.isoformat(),
                "model_features": prediction_result.get("model_features", {}),
                "model_info": model_info,
                "explanation": "Single probability from logistic regression model"
            }
            
        else:  # quarterly
            company = company_service.create_quarterly_company(company_data, prediction_result)
            
            response_ratios = {
                "total_debt_to_ebitda": float(company.total_debt_to_ebitda),
                "sga_margin": float(company.sga_margin),
                "long_term_debt_to_total_capital": float(company.long_term_debt_to_total_capital),
                "return_on_capital": float(company.return_on_capital)
            }
            
            # Quarterly prediction response - multiple probabilities
            response_prediction = {
                "prediction_type": "quarterly",
                "probabilities": {
                    "logistic": float(company.logistic_probability) if company.logistic_probability else None,
                    "gbm": float(company.gbm_probability) if company.gbm_probability else None,
                    "ensemble": float(company.probability) if company.probability else None
                },
                "primary_probability": float(company.probability) if company.probability else None,  # Ensemble is primary
                "risk_level": company.risk_level,
                "confidence": float(company.confidence),
                "predicted_at": company.predicted_at.isoformat(),
                "model_features": prediction_result.get("model_features", {}),
                "model_info": model_info,
                "explanation": "Ensemble combines logistic regression and Light GBM predictions"
            }

        return {
            "success": True,
            "message": f"{request.prediction_type.title()} prediction generated successfully",
            "company": {
                "id": str(company.id),
                "symbol": company.symbol,
                "name": company.name,
                "market_cap": float(company.market_cap) if company.market_cap else None,
                "sector": company.sector,
                "reporting_year": company.reporting_year,
                "reporting_quarter": company.reporting_quarter,
                "prediction_type": request.prediction_type,
                "ratios": response_ratios,
                "prediction": response_prediction
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Unified prediction error: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "Unified prediction failed",
                "details": str(e)
            }
        )


@router.post("/test-unified-predict", response_model=PredictionResponse)
async def test_unified_predict_default_rate(
    request: UnifiedPredictionRequest,
    db: Session = Depends(get_db)
):
    """
    TEST ENDPOINT (NO AUTH) - Unified prediction endpoint that handles both annual and quarterly predictions
    Based on prediction_type field, routes to appropriate ML model
    
    For annual: requires 5 fields (long_term_debt_to_total_capital, total_debt_to_ebitda, 
                                   net_income_margin, ebit_to_interest_expense, return_on_assets)
    For quarterly: requires 4 fields (total_debt_to_ebitda, sga_margin, 
                                     long_term_debt_to_total_capital, return_on_capital)
    """
    try:
        company_service = CompanyService(db)

        # Check if company already exists with this prediction type
        existing_company = company_service.get_company_by_symbol_and_type(
            request.stock_symbol, request.prediction_type
        )

        if existing_company:
            raise HTTPException(
                status_code=400,
                detail=f"Company '{request.stock_symbol}' already has {request.prediction_type} prediction. Use update endpoint to modify."
            )

        # Route to appropriate model based on prediction_type
        if request.prediction_type == "annual":
            # Validate annual fields are provided
            if not all([
                request.long_term_debt_to_total_capital is not None,
                request.total_debt_to_ebitda is not None,
                request.net_income_margin is not None,
                request.ebit_to_interest_expense is not None,
                request.return_on_assets is not None
            ]):
                raise HTTPException(
                    status_code=400,
                    detail="For annual predictions, all 5 annual financial ratios are required"
                )

            # Use annual ML model
            ratios = {
                "long_term_debt_to_total_capital": request.long_term_debt_to_total_capital,
                "total_debt_to_ebitda": request.total_debt_to_ebitda,
                "net_income_margin": request.net_income_margin,
                "ebit_to_interest_expense": request.ebit_to_interest_expense,
                "return_on_assets": request.return_on_assets
            }
            
            prediction_result = ml_model.predict_default_probability(ratios)
            
            # Create annual company record
            company_data = CompanyCreate(
                symbol=request.stock_symbol,
                name=request.company_name,
                market_cap=request.market_cap,
                sector=request.sector,
                reporting_year=request.reporting_year,
                reporting_quarter=request.reporting_quarter,
                prediction_type="annual",
                # Annual fields
                long_term_debt_to_total_capital=request.long_term_debt_to_total_capital,
                total_debt_to_ebitda=request.total_debt_to_ebitda,
                net_income_margin=request.net_income_margin,
                ebit_to_interest_expense=request.ebit_to_interest_expense,
                return_on_assets=request.return_on_assets,
                # Results
                risk_level=prediction_result["risk_level"],
                confidence=prediction_result["confidence"],
                probability=prediction_result["probability"]
            )
            
            company = company_service.create_company(company_data)
            
            return PredictionResponse(
                company_id=company.id,
                stock_symbol=company.symbol,
                company_name=company.name,
                prediction_type="annual",
                probability=prediction_result["probability"],
                risk_level=prediction_result["risk_level"],
                confidence=prediction_result["confidence"],
                model_features=ratios,
                predicted_at=serialize_datetime(company.predicted_at),
                created_at=serialize_datetime(company.created_at)
            )

        elif request.prediction_type == "quarterly":
            # Validate quarterly fields are provided
            if not all([
                request.total_debt_to_ebitda is not None,
                request.long_term_debt_to_total_capital is not None,
                request.sga_margin is not None,
                request.return_on_capital is not None
            ]):
                raise HTTPException(
                    status_code=400,
                    detail="For quarterly predictions, all 4 quarterly financial ratios are required"
                )

            # Use quarterly ML model
            ratios = {
                "total_debt_to_ebitda": request.total_debt_to_ebitda,
                "long_term_debt_to_total_capital": request.long_term_debt_to_total_capital,
                "sga_margin": request.sga_margin,
                "return_on_capital": request.return_on_capital
            }
            
            prediction_result = quarterly_ml_model.predict_quarterly_default_probability(ratios)
            
            # Create quarterly company record
            company_data = CompanyCreate(
                symbol=request.stock_symbol,
                name=request.company_name,
                market_cap=request.market_cap,
                sector=request.sector,
                reporting_year=request.reporting_year,
                reporting_quarter=request.reporting_quarter,
                prediction_type="quarterly",
                # Quarterly fields (shared with annual)
                total_debt_to_ebitda=request.total_debt_to_ebitda,
                long_term_debt_to_total_capital=request.long_term_debt_to_total_capital,
                # Quarterly specific fields
                sga_margin=request.sga_margin,
                return_on_capital=request.return_on_capital,
                # Results
                risk_level=prediction_result["risk_level"],
                confidence=prediction_result["confidence"],
                probability=prediction_result["ensemble_probability"],
                logistic_probability=prediction_result["logistic_probability"],
                gbm_probability=prediction_result["gbm_probability"]
            )
            
            company = company_service.create_quarterly_company(company_data)
            
            return PredictionResponse(
                company_id=company.id,
                stock_symbol=company.symbol,
                company_name=company.name,
                prediction_type="quarterly",
                probability=prediction_result["ensemble_probability"],
                risk_level=prediction_result["risk_level"],
                confidence=prediction_result["confidence"],
                model_features=ratios,
                additional_predictions={
                    "logistic_probability": prediction_result["logistic_probability"],
                    "gbm_probability": prediction_result["gbm_probability"],
                    "ensemble_probability": prediction_result["ensemble_probability"]
                },
                predicted_at=serialize_datetime(company.predicted_at),
                created_at=serialize_datetime(company.created_at)
            )
        
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid prediction_type. Must be 'annual' or 'quarterly'"
            )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Test unified prediction error: {e}")
        db.rollback()
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "Test unified prediction failed",
                "details": str(e)
            }
        )


@router.get("/test-companies", response_model=List[Dict])
async def test_get_companies(db: Session = Depends(get_db)):
    """TEST ENDPOINT (NO AUTH) - Get all companies for testing"""
    try:
        company_service = CompanyService(db)
        companies = company_service.get_all_companies()
        
        result = []
        for company in companies:
            result.append({
                "id": str(company.id),
                "symbol": company.symbol,
                "name": company.name,
                "prediction_type": company.prediction_type,
                "risk_level": company.risk_level,
                "probability": float(company.probability) if company.probability else None,
                "created_at": serialize_datetime(company.created_at)
            })
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve companies: {str(e)}"
        )