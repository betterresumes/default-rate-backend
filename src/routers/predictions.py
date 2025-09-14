from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from ..database import get_db, User, Company
from ..schemas import (
    PredictionRequest, PredictionResponse, BulkPredictionResponse, 
    BulkPredictionItem, BulkJobResponse, JobStatusResponse,
    PredictionUpdateRequest, DatabaseResetRequest, DatabaseResetResponse,
    CompanyCreate
)
from ..services import CompanyService, PredictionService, DatabaseService
from ..ml_service import ml_model
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


@router.post("/predict-default-rate", response_model=PredictionResponse)
async def predict_default_rate(
    request: PredictionRequest,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Predict default rate for a company using Annual ML model"""
    try:
        company_service = CompanyService(db)

        company = company_service.get_company_by_symbol(request.stock_symbol)

        if company:
            raise HTTPException(
                status_code=400,
                detail=f"Company with symbol '{request.stock_symbol}' already exists. Use update endpoint to modify."
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
                    "error": "Prediction failed",
                    "details": prediction_result["error"]
                }
            )

        from ..schemas import CompanyCreate
        company_data = CompanyCreate(
            symbol=request.stock_symbol,
            name=request.company_name,
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
        
        company = company_service.create_company(company_data, prediction_result)

        return {
            "success": True,
            "message": "Prediction generated using Annual ML model",
            "company": {
                "id": str(company.id),
                "symbol": company.symbol,
                "name": company.name,
                "market_cap": float(company.market_cap) if company.market_cap else None,
                "sector": company.sector,
                "reporting_year": company.reporting_year,
                "reporting_quarter": company.reporting_quarter,
                "ratios": {
                    "long_term_debt_to_total_capital": float(company.long_term_debt_to_total_capital),
                    "total_debt_to_ebitda": float(company.total_debt_to_ebitda),
                    "net_income_margin": float(company.net_income_margin),
                    "ebit_to_interest_expense": float(company.ebit_to_interest_expense),
                    "return_on_assets": float(company.return_on_assets)
                },
                "prediction": {
                    "probability": float(company.probability) if company.probability else None,
                    "risk_level": company.risk_level,
                    "confidence": float(company.confidence),
                    "predicted_at": company.predicted_at.isoformat(),
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
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Prediction error: {e}")
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