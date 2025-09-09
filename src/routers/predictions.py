from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from ..database import get_db
from ..schemas import PredictionRequest, PredictionResponse, BulkPredictionResponse, BulkPredictionItem
from ..services import CompanyService, PredictionService
from ..ml_service import ml_service
from typing import Dict, List
from datetime import datetime
import pandas as pd
import io
import time

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
            from ..schemas import CompanyCreate
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
                    "id": company.id,
                    "symbol": company.symbol,
                    "name": company.name,
                    "sector": company.sector
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
            "id": company.id,
            "company": {
                "symbol": company.symbol,
                "name": company.name,
                "sector": company.sector
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


@router.post("/bulk-predict", response_model=BulkPredictionResponse)
async def bulk_predict_from_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Bulk prediction endpoint that accepts Excel files with company data.
    
    Expected Excel columns:
    - stock_symbol: Company stock symbol (required)
    - company_name: Company name (required)
    - market_cap: Market capitalization (optional)
    - sector: Company sector (optional)
    - debt_to_equity_ratio: Debt to equity ratio (required for prediction)
    - current_ratio: Current ratio (required for prediction)
    - quick_ratio: Quick ratio (required for prediction)
    - return_on_equity: Return on equity (required for prediction)
    - return_on_assets: Return on assets (required for prediction)
    - profit_margin: Profit margin (required for prediction)
    - interest_coverage: Interest coverage ratio (required for prediction)
    - fixed_asset_turnover: Fixed asset turnover (required for prediction)
    - total_debt_ebitda: Total debt to EBITDA ratio (required for prediction)
    """
    start_time = time.time()
    
    # Validate file type
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="File must be an Excel file (.xlsx or .xls)"
        )
    
    try:
        # Read Excel file
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        
        # Validate required columns
        required_columns = [
            'stock_symbol', 'company_name', 'debt_to_equity_ratio', 
            'current_ratio', 'quick_ratio', 'return_on_equity', 
            'return_on_assets', 'profit_margin', 'interest_coverage', 
            'fixed_asset_turnover', 'total_debt_ebitda'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        # Initialize services
        company_service = CompanyService(db)
        prediction_service = PredictionService(db)
        
        results = []
        successful_predictions = 0
        failed_predictions = 0
        
        # Process each company
        for index, row in df.iterrows():
            try:
                # Extract company data
                stock_symbol = str(row['stock_symbol']).strip()
                company_name = str(row['company_name']).strip()
                
                if not stock_symbol or not company_name:
                    raise ValueError("Stock symbol and company name are required")
                
                # Check if company exists
                company = company_service.get_company_by_symbol(stock_symbol)
                
                if not company:
                    # Create new company
                    from ..schemas import CompanyCreate
                    company_data = CompanyCreate(
                        symbol=stock_symbol,
                        name=company_name,
                        market_cap=float(row.get('market_cap', 0)) if pd.notna(row.get('market_cap')) else None,
                        sector=str(row.get('sector', '')).strip() if pd.notna(row.get('sector')) else None
                    )
                    company = company_service.create_company(company_data)
                
                # Prepare financial ratios
                ratios = {}
                ratio_columns = [
                    'debt_to_equity_ratio', 'current_ratio', 'quick_ratio',
                    'return_on_equity', 'return_on_assets', 'profit_margin',
                    'interest_coverage', 'fixed_asset_turnover', 'total_debt_ebitda'
                ]
                
                for col in ratio_columns:
                    value = row.get(col)
                    if pd.notna(value):
                        ratios[col] = float(value)
                    else:
                        raise ValueError(f"Missing value for {col}")
                
                # Make prediction
                prediction_result = ml_service.predict_default_probability(ratios)
                
                # Save prediction and ratios
                saved_prediction = prediction_service.save_prediction(
                    company.id, 
                    prediction_result, 
                    ratios
                )
                prediction_service.save_financial_ratios(company.id, ratios)
                
                # Create result item
                result_item = BulkPredictionItem(
                    stock_symbol=stock_symbol,
                    company_name=company_name,
                    sector=company.sector,
                    market_cap=company.market_cap,
                    prediction={
                        "risk_level": prediction_result["risk_level"],
                        "confidence": prediction_result["confidence"],
                        "probability": prediction_result["probability"],
                        "predicted_at": serialize_datetime(saved_prediction.predicted_at)
                    },
                    status="success"
                )
                
                results.append(result_item)
                successful_predictions += 1
                
            except Exception as e:
                # Handle individual company errors
                result_item = BulkPredictionItem(
                    stock_symbol=str(row.get('stock_symbol', f'Row {index + 1}')),
                    company_name=str(row.get('company_name', 'Unknown')),
                    sector=str(row.get('sector', '')) if pd.notna(row.get('sector')) else None,
                    market_cap=float(row.get('market_cap', 0)) if pd.notna(row.get('market_cap')) else None,
                    prediction={},
                    status="error",
                    error_message=str(e)
                )
                
                results.append(result_item)
                failed_predictions += 1
                print(f"Error processing row {index + 1}: {e}")
        
        # Commit all successful transactions
        prediction_service.commit_transaction()
        
        processing_time = time.time() - start_time
        
        return BulkPredictionResponse(
            success=True,
            message=f"Processed {len(df)} companies successfully",
            total_companies=len(df),
            successful_predictions=successful_predictions,
            failed_predictions=failed_predictions,
            results=results,
            processing_time=round(processing_time, 2)
        )
        
    except pd.errors.EmptyDataError:
        raise HTTPException(
            status_code=400,
            detail="Excel file is empty or contains no data"
        )
    except Exception as e:
        # Rollback on major error
        db.rollback()
        print(f"Bulk prediction error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Bulk prediction failed",
                "details": str(e)
            }
        )