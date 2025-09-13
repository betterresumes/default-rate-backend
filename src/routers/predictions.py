from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from ..database import get_db, User, Company
from ..schemas import (
    PredictionRequest, PredictionResponse, BulkPredictionResponse, 
    BulkPredictionItem, BulkJobResponse, JobStatusResponse,
    PredictionUpdateRequest, PredictionUpdateResponse, PredictionDeleteResponse
)
from ..services import CompanyService, PredictionService
from ..ml_service import ml_model
from ..auth import get_current_verified_user
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


@router.post("/predict-default-rate", response_model=PredictionResponse)
async def predict_default_rate(
    request: PredictionRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Predict default rate for a company using new ML model"""
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
                sector=request.sector,
                reporting_year=request.reporting_year,
                reporting_quarter=request.reporting_quarter
            )
            company = company_service.create_company(company_data)  # Removed user reference

        # Prepare financial ratios for new ML model
        ratios = {
            "long_term_debt_to_total_capital": request.long_term_debt_to_total_capital,
            "total_debt_to_ebitda": request.total_debt_to_ebitda,
            "net_income_margin": request.net_income_margin,
            "ebit_to_interest_expense": request.ebit_to_interest_expense,
            "return_on_assets": request.return_on_assets
        }

        # Make prediction using new ML model
        prediction_result = ml_model.predict_default_probability(ratios)

        if "error" in prediction_result:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Prediction failed",
                    "details": prediction_result["error"]
                }
            )

        # Save prediction and ratios
        saved_prediction = prediction_service.save_prediction(
            company.id, 
            prediction_result, 
            ratios,
            request.reporting_year,
            request.reporting_quarter
        )
        
        # Single commit for both operations
        prediction_service.commit_transaction()

        return {
            "success": True,
            "message": "Prediction generated using new ML model",
            "company": {
                "id": company.id,
                "symbol": company.symbol,
                "name": company.name,
                "market_cap": float(company.market_cap) if company.market_cap else None,
                "sector": company.sector,
                "reporting_year": request.reporting_year or company.reporting_year,
                "reporting_quarter": request.reporting_quarter or company.reporting_quarter
            },
            "ratios": {
                "long_term_debt_to_total_capital": request.long_term_debt_to_total_capital,
                "total_debt_to_ebitda": request.total_debt_to_ebitda,
                "net_income_margin": request.net_income_margin,
                "ebit_to_interest_expense": request.ebit_to_interest_expense,
                "return_on_assets": request.return_on_assets
            },
            "prediction": {
                "probability": prediction_result["probability"],
                "risk_level": prediction_result["risk_level"],
                "confidence": prediction_result["confidence"],
                "predicted_at": prediction_result["predicted_at"],
                "model_features": prediction_result.get("model_features", {}),
                "raw_inputs": prediction_result.get("raw_inputs", {}),
                "model_info": {
                    "model_type": "New Logistic Regression Model",
                    "features": [
                        "Long-term debt / total capital (%)",
                        "Total debt / EBITDA", 
                        "Net income margin (%)",
                        "EBIT / interest expense",
                        "Return on assets (%)"
                    ]
                }
            }
        }

    except HTTPException:
        raise
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
    - reporting_year: Reporting year (optional, e.g., '2024')
    - reporting_quarter: Reporting quarter (optional, e.g., 'Q4')
    - long_term_debt_to_total_capital: Long-term debt / total capital (%) (required)
    - total_debt_to_ebitda: Total debt / EBITDA (required)
    - net_income_margin: Net income margin (%) (required)
    - ebit_to_interest_expense: EBIT / interest expense (required)
    - return_on_assets: Return on assets (%) (required)
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
                        sector=str(row.get('sector', '')).strip() if pd.notna(row.get('sector')) else None,
                        reporting_year=str(row.get('reporting_year', '')).strip() if pd.notna(row.get('reporting_year')) else None,
                        reporting_quarter=str(row.get('reporting_quarter', '')).strip() if pd.notna(row.get('reporting_quarter')) else None
                    )
                    company = company_service.create_company(company_data)
                
                # Prepare financial ratios (only the 5 required ones)
                ratios = {}
                ratio_columns = [
                    'long_term_debt_to_total_capital', 'total_debt_to_ebitda', 
                    'net_income_margin', 'ebit_to_interest_expense', 'return_on_assets'
                ]
                
                for col in ratio_columns:
                    value = row.get(col)
                    if pd.notna(value):
                        ratios[col] = float(value)
                    else:
                        raise ValueError(f"Missing value for {col}")
                
                # Make prediction using new ML service
                prediction_result = ml_model.predict_default_probability(ratios)
                # Check for prediction errors
                if "error" in prediction_result:
                    raise ValueError(f"Prediction failed: {prediction_result['error']}")
                
                # Save prediction and ratios
                saved_prediction = prediction_service.save_prediction(
                    company.id, 
                    prediction_result, 
                    ratios
                )
                
                # Get reporting info from Excel or use defaults
                reporting_year = str(row.get('reporting_year', '')).strip() if pd.notna(row.get('reporting_year')) else None
                reporting_quarter = str(row.get('reporting_quarter', '')).strip() if pd.notna(row.get('reporting_quarter')) else None
                
                prediction_service.save_financial_ratios(company.id, ratios, reporting_year, reporting_quarter)
                
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
        # Read file content
        contents = await file.read()
        
        # Quick validation of file content
        try:
            df = pd.read_excel(io.BytesIO(contents))
            company_count = len(df)
            
            # Validate required columns (5 required ratios) - standardized names
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
                
        except pd.errors.EmptyDataError:
            raise HTTPException(
                status_code=400,
                detail="Excel file is empty or contains no data"
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid Excel file: {str(e)}"
            )
        
        # Encode file content to base64 for passing to Celery task
        file_content_b64 = base64.b64encode(contents).decode('utf-8')
        
        # Submit background task
        from ..tasks import process_bulk_excel_task
        task = process_bulk_excel_task.delay(file_content_b64, file.filename)
        
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


@router.put("/{company_id}", response_model=PredictionUpdateResponse)
async def update_prediction(
    company_id: str,
    request: PredictionUpdateRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Update prediction for a company - flexible updates for any field"""
    try:
        prediction_service = PredictionService(db)

        # Convert request to dict, excluding None values
        update_data = request.dict(exclude_unset=True)
        
        # Check if any data is provided for update
        if not update_data:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "No update data provided",
                    "details": "At least one field must be provided for update"
                }
            )

        # Update prediction and company information
        updated_prediction, updated_company = prediction_service.update_prediction(
            company_id,
            update_data
        )
        
        # Commit the transaction
        prediction_service.commit_transaction()

        # Get current financial ratios
        current_ratios = {}
        if updated_prediction and updated_prediction.financial_ratio:
            financial_ratio = updated_prediction.financial_ratio
            current_ratios = {
                "long_term_debt_to_total_capital": float(financial_ratio.long_term_debt_to_total_capital),
                "total_debt_to_ebitda": float(financial_ratio.total_debt_to_ebitda),
                "net_income_margin": float(financial_ratio.net_income_margin),
                "ebit_to_interest_expense": float(financial_ratio.ebit_to_interest_expense),
                "return_on_assets": float(financial_ratio.return_on_assets),
                "reporting_year": financial_ratio.reporting_year,
                "reporting_quarter": financial_ratio.reporting_quarter
            }

        # Prepare response
        response_data = {
            "success": True,
            "message": "Prediction updated successfully",
            "company": {
                "id": str(updated_company.id),
                "symbol": updated_company.symbol,
                "name": updated_company.name,
                "market_cap": float(updated_company.market_cap) if updated_company.market_cap else None,
                "sector": updated_company.sector,
                "reporting_year": updated_company.reporting_year,
                "reporting_quarter": updated_company.reporting_quarter
            },
            "ratios": current_ratios,
            "prediction": {
                "id": str(updated_prediction.id) if updated_prediction else None,
                "probability": float(updated_prediction.probability) if updated_prediction and updated_prediction.probability else None,
                "risk_level": updated_prediction.risk_level if updated_prediction else None,
                "confidence": float(updated_prediction.confidence) if updated_prediction else None,
                "predicted_at": serialize_datetime(updated_prediction.predicted_at) if updated_prediction else None,
                "updated_at": serialize_datetime(updated_prediction.updated_at) if updated_prediction else None
            }
        }

        return response_data

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Not found",
                "details": str(e)
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Update prediction error: {e}")
        # Rollback on error
        db.rollback()
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "Update prediction failed",
                "details": str(e)
            }
        )


@router.delete("/{company_id}", response_model=PredictionDeleteResponse)
async def delete_prediction(
    company_id: str,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Delete prediction for a company"""
    try:
        prediction_service = PredictionService(db)

        # Delete prediction
        company = prediction_service.delete_prediction(company_id)
        
        # Commit the transaction
        prediction_service.commit_transaction()

        return {
            "success": True,
            "message": "Prediction deleted successfully",
            "company": {
                "id": str(company.id),
                "symbol": company.symbol,
                "name": company.name,
                "market_cap": float(company.market_cap) if company.market_cap else None,
                "sector": company.sector
            }
        }

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Not found",
                "details": str(e)
            }
        )
    except Exception as e:
        print(f"Delete prediction error: {e}")
        # Rollback on error
        db.rollback()
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "Delete prediction failed",
                "details": str(e)
            }
        )


@router.get("/{company_id}")
async def get_prediction(
    company_id: str,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Get prediction for a specific company"""
    try:
        prediction_service = PredictionService(db)
        company_service = CompanyService(db)

        # Get company details
        company = company_service.get_company_by_id(company_id)
        if not company:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Company not found",
                    "details": f"Company with ID {company_id} does not exist"
                }
            )

        # Get prediction
        prediction = prediction_service.get_prediction_by_company_id(company_id)
        if not prediction:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Prediction not found",
                    "details": f"No prediction found for company {company_id}"
                }
            )

        # Get financial ratios
        financial_ratio = prediction.financial_ratio

        return {
            "success": True,
            "company": {
                "id": str(company.id),
                "symbol": company.symbol,
                "name": company.name,
                "market_cap": float(company.market_cap) if company.market_cap else None,
                "sector": company.sector,
                "reporting_year": company.reporting_year,
                "reporting_quarter": company.reporting_quarter
            },
            "ratios": {
                "long_term_debt_to_total_capital": float(financial_ratio.long_term_debt_to_total_capital),
                "total_debt_to_ebitda": float(financial_ratio.total_debt_to_ebitda),
                "net_income_margin": float(financial_ratio.net_income_margin),
                "ebit_to_interest_expense": float(financial_ratio.ebit_to_interest_expense),
                "return_on_assets": float(financial_ratio.return_on_assets),
                "reporting_year": financial_ratio.reporting_year,
                "reporting_quarter": financial_ratio.reporting_quarter
            },
            "prediction": {
                "id": str(prediction.id),
                "probability": float(prediction.probability) if prediction.probability else None,
                "risk_level": prediction.risk_level,
                "confidence": float(prediction.confidence),
                "predicted_at": serialize_datetime(prediction.predicted_at),
                "created_at": serialize_datetime(prediction.created_at),
                "updated_at": serialize_datetime(prediction.updated_at)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Get prediction error: {e}")
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "Failed to get prediction",
                "details": str(e)
            }
        )