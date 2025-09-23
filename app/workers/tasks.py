import os
import sys
import pandas as pd
import time
import traceback
import io
import base64
import math
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from celery import current_task

# macOS fork safety fix
if sys.platform == "darwin":
    os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")

from ..workers.celery_app import celery_app
from ..core.database import get_session_local, BulkUploadJob, Company, AnnualPrediction, QuarterlyPrediction, User, Organization
from ..services.ml_service import ml_model
from ..services.quarterly_ml_service import quarterly_ml_model
import logging

logger = logging.getLogger(__name__)


def safe_float(value):
    """Convert value to float, handling None and NaN values"""
    if value is None:
        return 0
    try:
        float_val = float(value)
        if math.isnan(float_val) or math.isinf(float_val):
            return 0
        return float_val
    except (ValueError, TypeError):
        return 0


def update_job_status(
    job_id: str,
    status: str,
    processed_rows: Optional[int] = None,
    successful_rows: Optional[int] = None,
    failed_rows: Optional[int] = None,
    error_message: Optional[str] = None,
    error_details: Optional[Dict] = None
):
    """Update job status in database"""
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    try:
        job = db.query(BulkUploadJob).filter(BulkUploadJob.id == job_id).first()
        if not job:
            return
        
        job.status = status
        
        if processed_rows is not None:
            job.processed_rows = processed_rows
        if successful_rows is not None:
            job.successful_rows = successful_rows
        if failed_rows is not None:
            job.failed_rows = failed_rows
        if error_message is not None:
            job.error_message = error_message
        if error_details is not None:
            import json
            job.error_details = json.dumps(error_details)
        
        if status == 'processing' and job.started_at is None:
            job.started_at = datetime.utcnow()
        elif status in ['completed', 'failed']:
            job.completed_at = datetime.utcnow()
        
        db.commit()
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating job status: {str(e)}")
    finally:
        db.close()


def create_or_get_company(db, symbol: str, name: str, market_cap: float, sector: str, organization_id: Optional[str], user_id: str) -> Company:
    """Create or get company with organization scoping"""
    # Check for existing company in organization scope
    if organization_id:
        company = db.query(Company).filter(
            Company.symbol == symbol.upper(),
            Company.organization_id == organization_id
        ).first()
    else:
        # Global scope
        company = db.query(Company).filter(
            Company.symbol == symbol.upper(),
            Company.organization_id.is_(None)
        ).first()
    
    if not company:
        # Check if user can create global companies
        is_global = False
        if organization_id is None:
            user = db.query(User).filter(User.id == user_id).first()
            if user and user.role == "super_admin":
                is_global = True
            else:
                raise Exception("Only super admin can create global companies")
        
        company = Company(
            symbol=symbol.upper(),
            name=name,
            market_cap=safe_float(market_cap) * 1_000_000,  # Convert to actual value
            sector=sector,
            organization_id=organization_id,
            created_by=user_id,
            is_global=is_global
        )
        db.add(company)
        db.flush()  # Get the ID without committing
    else:
        # Update existing company
        company.name = name
        company.market_cap = safe_float(market_cap) * 1_000_000
        company.sector = sector
    
    return company


@celery_app.task(bind=True, name="app.workers.tasks.process_annual_bulk_upload_task")
def process_annual_bulk_upload_task(
    self, 
    job_id: str, 
    data: List[Dict[str, Any]], 
    user_id: str, 
    organization_id: Optional[str]
) -> Dict[str, Any]:
    """
    Celery task to process annual predictions bulk upload
    
    Args:
        job_id: Bulk upload job ID
        data: List of row data from Excel/CSV
        user_id: ID of user who initiated upload
        organization_id: Organization ID (None for super admin global uploads)
        
    Returns:
        Dictionary with processing results
    """
    task_id = self.request.id
    start_time = time.time()
    
    # Update job status to processing
    update_job_status(job_id, 'processing')
    
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    successful_rows = 0
    failed_rows = 0
    error_details = []
    total_rows = len(data)
    
    try:
        self.update_state(
            state="PROGRESS",
            meta={
                "status": "Processing annual predictions...",
                "current": 0,
                "total": total_rows,
                "job_id": job_id
            }
        )
        
        for i, row in enumerate(data):
            try:
                # Create or get company
                company = create_or_get_company(
                    db=db,
                    symbol=row['company_symbol'],
                    name=row['company_name'],
                    market_cap=safe_float(row['market_cap']),
                    sector=row['sector'],
                    organization_id=organization_id,
                    user_id=user_id
                )
                
                # Check if prediction already exists
                existing_query = db.query(AnnualPrediction).filter(
                    AnnualPrediction.company_id == company.id,
                    AnnualPrediction.reporting_year == str(row['reporting_year'])
                )
                
                if row.get('reporting_quarter'):
                    existing_query = existing_query.filter(
                        AnnualPrediction.reporting_quarter == row['reporting_quarter']
                    )
                else:
                    existing_query = existing_query.filter(
                        AnnualPrediction.reporting_quarter.is_(None)
                    )
                
                existing_prediction = existing_query.first()
                if existing_prediction:
                    failed_rows += 1
                    error_details.append({
                        'row': i + 1,
                        'error': f"Prediction already exists for {row['company_symbol']} {row['reporting_year']}"
                    })
                    continue
                
                # Prepare financial data for ML model
                financial_data = {
                    'long_term_debt_to_total_capital': safe_float(row['long_term_debt_to_total_capital']),
                    'total_debt_to_ebitda': safe_float(row['total_debt_to_ebitda']),
                    'net_income_margin': safe_float(row['net_income_margin']),
                    'ebit_to_interest_expense': safe_float(row['ebit_to_interest_expense']),
                    'return_on_assets': safe_float(row['return_on_assets'])
                }
                
                # Get ML prediction (direct call in Celery task)
                ml_result = ml_model.predict_default_probability(financial_data)
                
                # Create prediction
                prediction = AnnualPrediction(
                    id=uuid.uuid4(),
                    company_id=company.id,
                    organization_id=organization_id,
                    reporting_year=str(row['reporting_year']),
                    reporting_quarter=row.get('reporting_quarter') if row.get('reporting_quarter') else None,
                    long_term_debt_to_total_capital=safe_float(row['long_term_debt_to_total_capital']),
                    total_debt_to_ebitda=safe_float(row['total_debt_to_ebitda']),
                    net_income_margin=safe_float(row['net_income_margin']),
                    ebit_to_interest_expense=safe_float(row['ebit_to_interest_expense']),
                    return_on_assets=safe_float(row['return_on_assets']),
                    probability=safe_float(ml_result['probability']),
                    risk_level=ml_result['risk_level'],
                    confidence=safe_float(ml_result['confidence']),
                    predicted_at=datetime.utcnow(),
                    created_by=user_id
                )
                
                db.add(prediction)
                successful_rows += 1
                
                # Commit every 50 rows and update progress
                if (i + 1) % 50 == 0:
                    db.commit()
                    update_job_status(
                        job_id, 
                        'processing',
                        processed_rows=i + 1,
                        successful_rows=successful_rows,
                        failed_rows=failed_rows
                    )
                    
                    self.update_state(
                        state="PROGRESS",
                        meta={
                            "status": f"Processed {i + 1}/{total_rows} rows",
                            "current": i + 1,
                            "total": total_rows,
                            "successful": successful_rows,
                            "failed": failed_rows,
                            "job_id": job_id
                        }
                    )
            
            except Exception as e:
                failed_rows += 1
                error_details.append({
                    'row': i + 1,
                    'data': {k: str(v) for k, v in row.items()},  # Convert to string for JSON serialization
                    'error': str(e)
                })
                logger.error(f"Error processing row {i + 1}: {str(e)}")
                db.rollback()
                continue
        
        # Final commit
        db.commit()
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Update job as completed
        update_job_status(
            job_id,
            'completed',
            processed_rows=total_rows,
            successful_rows=successful_rows,
            failed_rows=failed_rows,
            error_details={'errors': error_details[:100]}  # Limit to first 100 errors
        )
        
        result = {
            "status": "completed",
            "job_id": job_id,
            "total_rows": total_rows,
            "successful_rows": successful_rows,
            "failed_rows": failed_rows,
            "processing_time_seconds": round(processing_time, 2),
            "errors": error_details[:10]  # Return first 10 errors
        }
        
        return result
        
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        logger.error(f"Bulk upload job {job_id} failed: {error_msg}")
        
        update_job_status(
            job_id,
            'failed',
            error_message=error_msg,
            error_details={'errors': error_details}
        )
        
        self.update_state(
            state="FAILURE",
            meta={
                "status": f"Job failed: {error_msg}",
                "job_id": job_id,
                "error": error_msg
            }
        )
        
        raise Exception(f"Annual bulk upload failed: {error_msg}")
        
    finally:
        db.close()


@celery_app.task(bind=True, name="app.workers.tasks.process_quarterly_bulk_upload_task")
def process_quarterly_bulk_upload_task(
    self, 
    job_id: str, 
    data: List[Dict[str, Any]], 
    user_id: str, 
    organization_id: Optional[str]
) -> Dict[str, Any]:
    """
    Celery task to process quarterly predictions bulk upload
    
    Args:
        job_id: Bulk upload job ID
        data: List of row data from Excel/CSV
        user_id: ID of user who initiated upload
        organization_id: Organization ID (None for super admin global uploads)
        
    Returns:
        Dictionary with processing results
    """
    task_id = self.request.id
    start_time = time.time()
    
    # Update job status to processing
    update_job_status(job_id, 'processing')
    
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    successful_rows = 0
    failed_rows = 0
    error_details = []
    total_rows = len(data)
    
    try:
        self.update_state(
            state="PROGRESS",
            meta={
                "status": "Processing quarterly predictions...",
                "current": 0,
                "total": total_rows,
                "job_id": job_id
            }
        )
        
        for i, row in enumerate(data):
            try:
                # Create or get company
                company = create_or_get_company(
                    db=db,
                    symbol=row['company_symbol'],
                    name=row['company_name'],
                    market_cap=safe_float(row['market_cap']),
                    sector=row['sector'],
                    organization_id=organization_id,
                    user_id=user_id
                )
                
                # Check if prediction already exists
                existing_prediction = db.query(QuarterlyPrediction).filter(
                    QuarterlyPrediction.company_id == company.id,
                    QuarterlyPrediction.reporting_year == str(row['reporting_year']),
                    QuarterlyPrediction.reporting_quarter == row['reporting_quarter']
                ).first()
                
                if existing_prediction:
                    failed_rows += 1
                    error_details.append({
                        'row': i + 1,
                        'error': f"Prediction already exists for {row['company_symbol']} {row['reporting_year']} {row['reporting_quarter']}"
                    })
                    continue
                
                # Prepare financial data for ML model
                financial_data = {
                    'total_debt_to_ebitda': safe_float(row['total_debt_to_ebitda']),
                    'sga_margin': safe_float(row['sga_margin']),
                    'long_term_debt_to_total_capital': safe_float(row['long_term_debt_to_total_capital']),
                    'return_on_capital': safe_float(row['return_on_capital'])
                }
                
                # Get ML prediction (direct call in Celery task)
                ml_result = quarterly_ml_model.predict_quarterly_default_probability(financial_data)
                
                # Create prediction
                prediction = QuarterlyPrediction(
                    id=uuid.uuid4(),
                    company_id=company.id,
                    organization_id=organization_id,
                    reporting_year=str(row['reporting_year']),
                    reporting_quarter=row['reporting_quarter'],
                    total_debt_to_ebitda=safe_float(row['total_debt_to_ebitda']),
                    sga_margin=safe_float(row['sga_margin']),
                    long_term_debt_to_total_capital=safe_float(row['long_term_debt_to_total_capital']),
                    return_on_capital=safe_float(row['return_on_capital']),
                    logistic_probability=safe_float(ml_result.get('logistic_probability', 0)),
                    gbm_probability=safe_float(ml_result.get('gbm_probability', 0)),
                    ensemble_probability=safe_float(ml_result.get('ensemble_probability', 0)),
                    risk_level=ml_result['risk_level'],
                    confidence=safe_float(ml_result['confidence']),
                    predicted_at=datetime.utcnow(),
                    created_by=user_id
                )
                
                db.add(prediction)
                successful_rows += 1
                
                # Commit every 50 rows and update progress
                if (i + 1) % 50 == 0:
                    db.commit()
                    update_job_status(
                        job_id, 
                        'processing',
                        processed_rows=i + 1,
                        successful_rows=successful_rows,
                        failed_rows=failed_rows
                    )
                    
                    self.update_state(
                        state="PROGRESS",
                        meta={
                            "status": f"Processed {i + 1}/{total_rows} rows",
                            "current": i + 1,
                            "total": total_rows,
                            "successful": successful_rows,
                            "failed": failed_rows,
                            "job_id": job_id
                        }
                    )
            
            except Exception as e:
                failed_rows += 1
                error_details.append({
                    'row': i + 1,
                    'data': {k: str(v) for k, v in row.items()},  # Convert to string for JSON serialization
                    'error': str(e)
                })
                logger.error(f"Error processing row {i + 1}: {str(e)}")
                db.rollback()
                continue
        
        # Final commit
        db.commit()
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Update job as completed
        update_job_status(
            job_id,
            'completed',
            processed_rows=total_rows,
            successful_rows=successful_rows,
            failed_rows=failed_rows,
            error_details={'errors': error_details[:100]}  # Limit to first 100 errors
        )
        
        result = {
            "status": "completed",
            "job_id": job_id,
            "total_rows": total_rows,
            "successful_rows": successful_rows,
            "failed_rows": failed_rows,
            "processing_time_seconds": round(processing_time, 2),
            "errors": error_details[:10]  # Return first 10 errors
        }
        
        return result
        
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        logger.error(f"Bulk upload job {job_id} failed: {error_msg}")
        
        update_job_status(
            job_id,
            'failed',
            error_message=error_msg,
            error_details={'errors': error_details}
        )
        
        self.update_state(
            state="FAILURE",
            meta={
                "status": f"Job failed: {error_msg}",
                "job_id": job_id,
                "error": error_msg
            }
        )
        
        raise Exception(f"Quarterly bulk upload failed: {error_msg}")
        
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.send_verification_email_task")
def send_verification_email_task(email: str, username: str, otp: str) -> bool:
    """
    Background task to send verification email.
    Currently disabled - email service not configured.
    
    Args:
        email: User's email address
        username: User's username
        otp: Generated OTP code
        
    Returns:
        Boolean indicating success
    """
    try:
        # Email service disabled for now
        print(f"Would send verification email to {email} with OTP: {otp}")
        return True  # Return success for testing
    except Exception as e:
        print(f"Failed to send verification email to {email}: {str(e)}")
        return False


@celery_app.task(name="app.workers.tasks.send_password_reset_email_task")
def send_password_reset_email_task(email: str, username: str, otp: str) -> bool:
    """
    Background task to send password reset email.
    Currently disabled - email service not configured.
    
    Args:
        email: User's email address
        username: User's username
        otp: Generated OTP code
        
    Returns:
        Boolean indicating success
    """
    try:
        # Email service disabled for now
        print(f"Would send password reset email to {email} with OTP: {otp}")
        return True  # Return success for testing
    except Exception as e:
        print(f"Failed to send password reset email to {email}: {str(e)}")
        return False


@celery_app.task(bind=True, name="app.workers.tasks.process_bulk_excel_task")
def process_bulk_excel_task(self, file_content_b64: str, original_filename: str) -> Dict[str, Any]:
    """
    Background task to process Excel file with multiple companies for bulk predictions.
    
    Args:
        file_content_b64: Base64 encoded content of the uploaded Excel file
        original_filename: Original name of the uploaded file
        
    Returns:
        Dictionary with processing results
    """
    task_id = self.request.id
    start_time = time.time()
    
    self.update_state(
        state="PROGRESS",
        meta={
            "status": "Starting bulk prediction processing...",
            "current": 0,
            "total": 0,
            "filename": original_filename
        }
    )
    
    session_factory = get_session_local()
    db = session_factory()
    
    results = []
    successful_predictions = 0
    failed_predictions = 0
    total_companies = 0
    
    try:
        file_content = base64.b64decode(file_content_b64)
        df = pd.read_excel(io.BytesIO(file_content))
        total_companies = len(df)
        
        column_mapping = {
            'long-term debt / total capital (%)': 'long_term_debt_to_total_capital',
            'long_term_debt_to_total_capital': 'long_term_debt_to_total_capital',
            'total debt / ebitda': 'total_debt_to_ebitda', 
            'total_debt_to_ebitda': 'total_debt_to_ebitda',
            'net income margin': 'net_income_margin',
            'net_income_margin': 'net_income_margin', 
            'ebit / interest expense': 'ebit_to_interest_expense',
            'ebit_to_interest_expense': 'ebit_to_interest_expense',
            'return on assets': 'return_on_assets',
            'return_on_assets': 'return_on_assets'
        }
        
        required_columns = [
            'stock_symbol', 'company_name',
            'long_term_debt_to_total_capital', 'total_debt_to_ebitda', 
            'net_income_margin', 'ebit_to_interest_expense', 'return_on_assets'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
        
        self.update_state(
            state="PROGRESS",
            meta={
                "status": f"Processing {total_companies} companies...",
                "current": 0,
                "total": total_companies,
                "filename": original_filename,
                "successful": 0,
                "failed": 0
            }
        )
        
        company_service = CompanyService(db)
        
        for index, row in df.iterrows():
            try:
                if index % 10 == 0 or index < 5 or index >= total_companies - 5:
                    self.update_state(
                        state="PROGRESS",
                        meta={
                            "status": f"Processing company {index + 1} of {total_companies}",
                            "current": index + 1,
                            "total": total_companies,
                            "filename": original_filename,
                            "successful": successful_predictions,
                            "failed": failed_predictions
                        }
                    )
                
                stock_symbol = str(row['stock_symbol']).strip()
                company_name = str(row['company_name']).strip()
                
                if not stock_symbol or not company_name:
                    raise ValueError("Stock symbol and company name are required")
                
                market_cap = row.get('market_cap', 1000000000)  
                if pd.isna(market_cap):
                    market_cap = 1000000000
                else:
                    market_cap = safe_float(market_cap)
                
                sector = row.get('sector', 'Unknown')
                if pd.isna(sector):
                    sector = 'Unknown'
                else:
                    sector = str(sector).strip()
                
                reporting_year = row.get('reporting_year')
                if pd.isna(reporting_year):
                    reporting_year = None
                else:
                    reporting_year = str(reporting_year).strip()
                
                reporting_quarter = row.get('reporting_quarter')
                if pd.isna(reporting_quarter):
                    reporting_quarter = None
                else:
                    reporting_quarter = str(reporting_quarter).strip()
                
                ratios = {
                    'long_term_debt_to_total_capital': safe_float(row['long_term_debt_to_total_capital']),
                    'total_debt_to_ebitda': safe_float(row['total_debt_to_ebitda']),
                    'net_income_margin': safe_float(row['net_income_margin']),
                    'ebit_to_interest_expense': safe_float(row['ebit_to_interest_expense']),
                    'return_on_assets': safe_float(row['return_on_assets'])
                }
                
                prediction_result = ml_model.predict_default_probability(ratios)
                
                if "error" in prediction_result:
                    raise ValueError(f"Prediction failed: {prediction_result['error']}")
                
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
                
                result_item = {
                    "company_name": company_name,
                    "stock_symbol": stock_symbol,
                    "sector": company.sector,
                    "market_cap": safe_float(company.market_cap),
                    "prediction": {
                        "id": str(company.id),
                        "risk_level": company.risk_level,
                        "confidence": safe_float(company.confidence),
                        "probability": safe_float(company.probability) if company.probability else None,
                        "predicted_at": company.predicted_at.isoformat() if company.predicted_at else None,
                        "financial_ratios": {
                            "long_term_debt_to_total_capital": safe_float(company.long_term_debt_to_total_capital),
                            "total_debt_to_ebitda": safe_float(company.total_debt_to_ebitda),
                            "net_income_margin": safe_float(company.net_income_margin),
                            "ebit_to_interest_expense": safe_float(company.ebit_to_interest_expense),
                            "return_on_assets": safe_float(company.return_on_assets)
                        }
                    },
                    "status": "success",
                    "error_message": None
                }
                
                results.append(result_item)
                successful_predictions += 1
                
            except Exception as e:
                result_item = {
                    "company_name": str(row.get('company_name', 'Unknown')),
                    "stock_symbol": str(row.get('stock_symbol', 'Unknown')),
                    "sector": str(row.get('sector', '')) if pd.notna(row.get('sector')) else None,
                    "market_cap": safe_float(row.get('market_cap', 0)) if pd.notna(row.get('market_cap')) else None,
                    "prediction": {},
                    "status": "error",
                    "error_message": str(e)
                }
                
                results.append(result_item)
                failed_predictions += 1
                print(f"Error processing row {index + 1}: {e}")
                
                db.rollback()
        
        db.commit()  
        
        processing_time = time.time() - start_time
        
        final_result = {
            "task_id": task_id,
            "success": True,
            "message": f"Processed {total_companies} companies successfully",
            "filename": original_filename,
            "total_companies": total_companies,
            "successful_predictions": successful_predictions,
            "failed_predictions": failed_predictions,
            "results": results,
            "processing_time": round(processing_time, 2),
            "completed_at": time.time()
        }
        
        return final_result
        
    except Exception as e:
        db.rollback()
        error_message = str(e)
        error_traceback = traceback.format_exc()
        
        print(f"Bulk prediction task failed: {error_message}")
        print(f"Traceback: {error_traceback}")
        
        self.update_state(
            state="FAILURE",
            meta={
                "error": error_message,
                "traceback": error_traceback,
                "filename": original_filename,
                "processed": successful_predictions + failed_predictions,
                "exc_type": type(e).__name__,
                "exc_message": error_message
            }
        )
        
        raise type(e)(error_message)
        
    finally:
        try:
            db.close()
        except Exception:
            pass


@celery_app.task(bind=True, name="app.workers.tasks.process_bulk_normalized_task")
def process_bulk_normalized_task(self, file_content_b64: str, original_filename: str, prediction_type: str = "annual", organization_id: str = None, created_by: str = None) -> Dict[str, Any]:
    """
    Background task to process CSV/Excel file with multiple companies for bulk predictions.
    Uses the new normalized database schema (companies, annual_predictions, quarterly_predictions).
    
    Args:
        file_content_b64: Base64 encoded content of the uploaded file
        original_filename: Original name of the uploaded file
        prediction_type: "annual" or "quarterly"
        organization_id: ID of the organization for multi-tenant context
        created_by: ID of the user who initiated the task
        
    Returns:
        Dictionary with processing results
    """
    task_id = self.request.id
    start_time = time.time()
    
    self.update_state(
        state="PROGRESS",
        meta={
            "status": f"Starting {prediction_type} bulk prediction processing...",
            "current": 0,
            "total": 0,
            "filename": original_filename,
            "prediction_type": prediction_type
        }
    )
    
    session_factory = get_session_local()
    db = session_factory()
    
    results = []
    successful_predictions = 0
    failed_predictions = 0
    total_companies = 0
    
    try:
        # Decode and read file
        file_content = base64.b64decode(file_content_b64)
        
        if original_filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(file_content.decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(file_content))
        
        total_companies = len(df)
        
        # Validate required columns based on prediction type
        if prediction_type == "annual":
            required_columns = [
                'stock_symbol', 'company_name',
                'long_term_debt_to_total_capital', 'total_debt_to_ebitda', 
                'net_income_margin', 'ebit_to_interest_expense', 'return_on_assets'
            ]
        else:  # quarterly
            required_columns = [
                'stock_symbol', 'company_name', 'reporting_year', 'reporting_quarter',
                'total_debt_to_ebitda', 'sga_margin', 
                'long_term_debt_to_total_capital', 'return_on_capital'
            ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
        
        # Optional columns with defaults
        optional_columns = {
            'market_cap': 1000000000,
            'sector': 'Unknown',
            'reporting_year': '2024',
            'reporting_quarter': 'Q4',  # Default for both annual and quarterly
        }
        
        # Add missing optional columns
        for col, default_value in optional_columns.items():
            if col not in df.columns:
                df[col] = default_value
        
        company_service = CompanyService(db)
        
        # Process each company
        for index, row in df.iterrows():
            try:
                # Update progress
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "status": f"Processing company {index + 1} of {total_companies}...",
                        "current": index + 1,
                        "total": total_companies,
                        "filename": original_filename,
                        "successful": successful_predictions,
                        "failed": failed_predictions,
                        "prediction_type": prediction_type
                    }
                )
                
                # Validate required data
                stock_symbol = str(row['stock_symbol']).strip().upper()
                company_name = str(row['company_name']).strip()
                
                if not stock_symbol or not company_name or stock_symbol.lower() == 'nan' or company_name.lower() == 'nan':
                    raise ValueError("Stock symbol and company name are required")
                
                # Handle optional fields
                market_cap = row.get('market_cap', 1000000000)
                if pd.isna(market_cap):
                    market_cap = 1000000000
                else:
                    market_cap = safe_float(market_cap)
                
                sector = row.get('sector', 'Unknown')
                if pd.isna(sector):
                    sector = 'Unknown'
                else:
                    sector = str(sector).strip()
                
                reporting_year = str(row.get('reporting_year', '2024')).strip()
                reporting_quarter = str(row.get('reporting_quarter', 'Q4')).strip()
                
                # Create or get company
                company = company_service.create_company(
                    symbol=stock_symbol,
                    name=company_name,
                    market_cap=market_cap,
                    sector=sector,
                    organization_id=organization_id,
                    created_by=created_by
                )
                
                if prediction_type == "annual":
                    # Annual prediction
                    ratios = {
                        'long_term_debt_to_total_capital': safe_float(row['long_term_debt_to_total_capital']),
                        'total_debt_to_ebitda': safe_float(row['total_debt_to_ebitda']),
                        'net_income_margin': safe_float(row['net_income_margin']),
                        'ebit_to_interest_expense': safe_float(row['ebit_to_interest_expense']),
                        'return_on_assets': safe_float(row['return_on_assets'])
                    }
                    
                    prediction_result = ml_model.predict_default_probability(ratios)
                    
                    if "error" in prediction_result:
                        raise ValueError(f"Annual prediction failed: {prediction_result['error']}")
                    
                    # Create annual prediction
                    annual_prediction = company_service.create_annual_prediction(
                        company=company,
                        financial_data=ratios,
                        prediction_results=prediction_result,
                        reporting_year=reporting_year,
                        reporting_quarter=reporting_quarter,
                        organization_id=organization_id,
                        created_by=created_by
                    )
                    
                    result_item = {
                        "stock_symbol": stock_symbol,
                        "company_name": company_name,
                        "sector": sector,
                        "market_cap": market_cap,
                        "prediction": {
                            "id": str(annual_prediction.id),
                            "type": "annual",
                            "probability": safe_float(annual_prediction.probability),
                            "primary_probability": safe_float(annual_prediction.probability),
                            "risk_level": annual_prediction.risk_level,
                            "confidence": safe_float(annual_prediction.confidence),
                            "reporting_year": annual_prediction.reporting_year,
                            "reporting_quarter": annual_prediction.reporting_quarter,
                            "financial_ratios": ratios
                        },
                        "status": "success",
                        "error_message": None
                    }
                    
                else:  # quarterly
                    # Quarterly prediction
                    reporting_quarter = str(row['reporting_quarter']).strip()
                    
                    ratios = {
                        'total_debt_to_ebitda': safe_float(row['total_debt_to_ebitda']),
                        'sga_margin': safe_float(row['sga_margin']),
                        'long_term_debt_to_total_capital': safe_float(row['long_term_debt_to_total_capital']),
                        'return_on_capital': safe_float(row['return_on_capital'])
                    }
                    
                    from ..services.quarterly_ml_service import quarterly_ml_model
                    prediction_result = quarterly_ml_model.predict_default_probability(ratios)
                    
                    if "error" in prediction_result:
                        raise ValueError(f"Quarterly prediction failed: {prediction_result['error']}")
                    
                    # Create quarterly prediction
                    quarterly_prediction = company_service.create_quarterly_prediction(
                        company=company,
                        financial_data=ratios,
                        prediction_results=prediction_result,
                        reporting_year=reporting_year,
                        reporting_quarter=reporting_quarter,
                        organization_id=organization_id,
                        created_by=created_by
                    )
                    
                    result_item = {
                        "stock_symbol": stock_symbol,
                        "company_name": company_name,
                        "sector": sector,
                        "market_cap": market_cap,
                        "prediction": {
                            "id": str(quarterly_prediction.id),
                            "type": "quarterly",
                            "probabilities": {
                                "logistic": safe_float(quarterly_prediction.logistic_probability),
                                "gbm": safe_float(quarterly_prediction.gbm_probability),
                                "ensemble": safe_float(quarterly_prediction.ensemble_probability)
                            },
                            "primary_probability": safe_float(quarterly_prediction.ensemble_probability),
                            "risk_level": quarterly_prediction.risk_level,
                            "confidence": safe_float(quarterly_prediction.confidence),
                            "reporting_year": quarterly_prediction.reporting_year,
                            "reporting_quarter": quarterly_prediction.reporting_quarter,
                            "financial_ratios": ratios
                        },
                        "status": "success",
                        "error_message": None
                    }
                
                results.append(result_item)
                successful_predictions += 1
                
            except Exception as e:
                # Handle individual company prediction failure
                result_item = {
                    "stock_symbol": str(row.get('stock_symbol', 'Unknown')),
                    "company_name": str(row.get('company_name', 'Unknown')),
                    "sector": str(row.get('sector', 'Unknown')),
                    "market_cap": safe_float(row.get('market_cap', 0)),
                    "prediction": None,
                    "status": "failed",
                    "error_message": str(e)
                }
                results.append(result_item)
                failed_predictions += 1
                print(f"Error processing row {index + 1}: {e}")
        
        processing_time = time.time() - start_time
        
        # Final result
        result = {
            "success": True,
            "message": f"Bulk {prediction_type} prediction completed. {successful_predictions} successful, {failed_predictions} failed.",
            "total_processed": total_companies,
            "successful_predictions": successful_predictions,
            "failed_predictions": failed_predictions,
            "results": results,
            "processing_time": processing_time,
            "completed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "prediction_type": prediction_type,
            "filename": original_filename
        }
        
        return result
        
    except Exception as e:
        error_msg = f"Bulk processing failed: {str(e)}"
        print(f"Task {task_id} failed: {error_msg}")
        print(f"Traceback: {traceback.format_exc()}")
        
        # Return error result
        return {
            "success": False,
            "message": error_msg,
            "total_processed": total_companies,
            "successful_predictions": successful_predictions,
            "failed_predictions": failed_predictions,
            "results": results,
            "processing_time": time.time() - start_time,
            "error": error_msg,
            "prediction_type": prediction_type,
            "filename": original_filename
        }
    
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.process_quarterly_bulk_task")
def process_quarterly_bulk_task(file_content_b64: str, original_filename: str, organization_id: str = None, created_by: str = None):
    """
    Process quarterly bulk prediction file in background
    """
    from ..services.quarterly_ml_service import quarterly_ml_model
    
    start_time = time.time()
    db = get_session_local()
    
    try:
        # Update task status
        current_task.update_state(
            state='PROGRESS',
            meta={'status': 'Processing quarterly file...', 'progress': 0}
        )
        
        # Decode file content
        file_content = base64.b64decode(file_content_b64)
        
        # Read file
        if original_filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(file_content.decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(file_content))
        
        total_companies = len(df)
        company_service = CompanyService(db)
        
        results = []
        successful_predictions = 0
        failed_predictions = 0
        
        # Process each company
        for index, row in df.iterrows():
            try:
                # Update progress
                progress = int((index / total_companies) * 100)
                current_task.update_state(
                    state='PROGRESS',
                    meta={
                        'status': f'Processing company {index + 1}/{total_companies}',
                        'progress': progress,
                        'current_company': row.get('stock_symbol', 'Unknown')
                    }
                )
                
                # Extract and validate data
                stock_symbol = str(row['stock_symbol']).strip()
                company_name = str(row['company_name']).strip()
                reporting_year = str(row['reporting_year']).strip()
                reporting_quarter = str(row['reporting_quarter']).strip()
                
                if not all([stock_symbol, company_name, reporting_year, reporting_quarter]):
                    results.append({
                        "stock_symbol": stock_symbol,
                        "company_name": company_name,
                        "reporting_year": reporting_year,
                        "reporting_quarter": reporting_quarter,
                        "success": False,
                        "error": "Missing required fields"
                    })
                    failed_predictions += 1
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
                        sector=sector,
                        organization_id=organization_id,
                        created_by=created_by
                    )
                
                # Check if prediction already exists
                existing_prediction = company_service.get_quarterly_prediction(
                    company.id, reporting_year, reporting_quarter
                )
                
                if existing_prediction:
                    results.append({
                        "stock_symbol": stock_symbol,
                        "company_name": company_name,
                        "reporting_year": reporting_year,
                        "reporting_quarter": reporting_quarter,
                        "success": False,
                        "error": f"Quarterly prediction for {stock_symbol} Q{reporting_quarter} {reporting_year} already exists"
                    })
                    failed_predictions += 1
                    continue
                
                # Prepare financial ratios
                financial_ratios = {
                    "total_debt_to_ebitda": safe_float(row['total_debt_to_ebitda']),
                    "sga_margin": safe_float(row['sga_margin']),
                    "long_term_debt_to_total_capital": safe_float(row['long_term_debt_to_total_capital']),
                    "return_on_capital": safe_float(row['return_on_capital'])
                }
                
                # Validate financial ratios
                missing_ratios = [k for k, v in financial_ratios.items() if v is None]
                if missing_ratios:
                    results.append({
                        "stock_symbol": stock_symbol,
                        "company_name": company_name,
                        "reporting_year": reporting_year,
                        "reporting_quarter": reporting_quarter,
                        "success": False,
                        "error": f"Missing financial ratios: {', '.join(missing_ratios)}"
                    })
                    failed_predictions += 1
                    continue
                
                # Get quarterly prediction
                prediction_result = quarterly_ml_model.predict_default_probability(financial_ratios)
                
                if "error" in prediction_result:
                    results.append({
                        "stock_symbol": stock_symbol,
                        "company_name": company_name,
                        "reporting_year": reporting_year,
                        "reporting_quarter": reporting_quarter,
                        "success": False,
                        "error": f"Quarterly prediction failed: {prediction_result['error']}"
                    })
                    failed_predictions += 1
                    continue
                
                # Save to database
                prediction = company_service.create_quarterly_prediction(
                    company=company,
                    financial_data=financial_ratios,
                    prediction_results=prediction_result,
                    reporting_year=reporting_year,
                    reporting_quarter=reporting_quarter,
                    organization_id=organization_id,
                    created_by=created_by
                )
                
                results.append({
                    "stock_symbol": stock_symbol,
                    "company_name": company_name,
                    "reporting_year": reporting_year,
                    "reporting_quarter": reporting_quarter,
                    "success": True,
                    "prediction_id": str(prediction.id),
                    "default_probability": prediction_result["ensemble_probability"],
                    "risk_level": prediction_result["risk_level"],
                    "confidence": prediction_result["confidence"]
                })
                successful_predictions += 1
                
            except Exception as e:
                results.append({
                    "stock_symbol": row.get('stock_symbol', 'Unknown'),
                    "company_name": row.get('company_name', 'Unknown'),
                    "reporting_year": row.get('reporting_year', 'Unknown'),
                    "reporting_quarter": row.get('reporting_quarter', 'Unknown'),
                    "success": False,
                    "error": f"Processing error: {str(e)}"
                })
                failed_predictions += 1
        
        # Final status update
        current_task.update_state(
            state='SUCCESS',
            meta={
                'status': 'Quarterly bulk processing completed',
                'progress': 100,
                'total_processed': total_companies,
                'successful_predictions': successful_predictions,
                'failed_predictions': failed_predictions,
                'processing_time': time.time() - start_time
            }
        )
        
        return {
            "success": True,
            "message": f"Quarterly bulk processing completed. Success: {successful_predictions}, Failed: {failed_predictions}",
            "total_processed": total_companies,
            "successful_predictions": successful_predictions,
            "failed_predictions": failed_predictions,
            "results": results,
            "processing_time": time.time() - start_time,
            "prediction_type": "quarterly",
            "filename": original_filename
        }
        
    except Exception as e:
        error_msg = f"Quarterly bulk processing failed: {str(e)}"
        print(f"Error in quarterly bulk task: {error_msg}")
        print(f"Traceback: {traceback.format_exc()}")
        
        current_task.update_state(
            state='FAILURE',
            meta={'error': error_msg}
        )
        
        return {
            "success": False,
            "message": error_msg,
            "total_processed": 0,
            "successful_predictions": 0,
            "failed_predictions": 0,
            "results": [],
            "processing_time": time.time() - start_time,
            "error": error_msg,
            "prediction_type": "quarterly",
            "filename": original_filename
        }
    
    finally:
        db.close()
