from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from ..database import get_db, User
from ..schemas import (
    PredictionRequest, PredictionResponse, BulkPredictionResponse, 
    BulkPredictionItem, BulkJobResponse, JobStatusResponse
)
from ..services import CompanyService, PredictionService
from ..ml_service import ml_service
from ..auth import get_current_verified_user
from typing import Dict, List
from datetime import datetime
import pandas as pd
import io
import time
import os
import uuid
from pathlib import Path

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
    current_user: User = Depends(get_current_verified_user),
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
            company = company_service.create_company(company_data, created_by_id=current_user.id)

        # Check for recent prediction (within 24 hours)
        recent_prediction = prediction_service.get_recent_prediction(company.id, 24)
        
        if recent_prediction:
            # For cached predictions, still run through ML service to get enhanced features
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
            
            # Get enhanced features from ML service
            prediction_result = ml_service.predict_default_probability(ratios)
            
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
                    "predicted_at": serialize_datetime(recent_prediction.predicted_at),
                    "model_features": prediction_result.get("model_features", {}),
                    "raw_inputs": prediction_result.get("raw_inputs", {}),
                    "historical_benchmarks": prediction_result.get("historical_benchmarks", {}),
                    "model_info": {
                        "model_type": "Logistic Regression"
                    }
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
                "raw_inputs": prediction_result.get("raw_inputs", {}),
                "historical_benchmarks": prediction_result.get("historical_benchmarks", {}),
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
    # Validate file type
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="File must be an Excel file (.xlsx or .xls)"
        )
    
    try:
        # Create upload directory if it doesn't exist
        upload_dir = Path("/tmp/bulk_uploads")
        upload_dir.mkdir(exist_ok=True)
        
        # Generate unique filename
        job_id = str(uuid.uuid4())
        file_extension = Path(file.filename).suffix
        temp_filename = f"{job_id}{file_extension}"
        temp_file_path = upload_dir / temp_filename
        
        # Save uploaded file
        contents = await file.read()
        with open(temp_file_path, "wb") as f:
            f.write(contents)
        
        # Quick validation of file content
        try:
            df = pd.read_excel(temp_file_path)
            company_count = len(df)
            
            # Validate required columns
            required_columns = [
                'stock_symbol', 'company_name', 'debt_to_equity_ratio', 
                'current_ratio', 'quick_ratio', 'return_on_equity', 
                'return_on_assets', 'profit_margin', 'interest_coverage', 
                'fixed_asset_turnover', 'total_debt_ebitda'
            ]
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                # Cleanup file before raising error
                os.remove(temp_file_path)
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required columns: {', '.join(missing_columns)}"
                )
                
        except pd.errors.EmptyDataError:
            os.remove(temp_file_path)
            raise HTTPException(
                status_code=400,
                detail="Excel file is empty or contains no data"
            )
        except Exception as e:
            os.remove(temp_file_path)
            raise HTTPException(
                status_code=400,
                detail=f"Invalid Excel file: {str(e)}"
            )
        
        # Submit background task
        from ..tasks import process_bulk_excel_task
        task = process_bulk_excel_task.delay(str(temp_file_path), file.filename)
        
        # Estimate processing time (roughly 1-2 seconds per company)
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
        
    except HTTPException:
        raise
    except Exception as e:
        # Cleanup file if it exists
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        
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