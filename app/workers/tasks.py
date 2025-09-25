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
from functools import wraps

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
    if organization_id:
        access_level = "organization"
        company = db.query(Company).filter(
            Company.symbol == symbol.upper(),
            Company.organization_id == organization_id,
            Company.access_level == "organization"
        ).first()
    else:
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.role == "super_admin":
            access_level = "system"
            company = db.query(Company).filter(
                Company.symbol == symbol.upper(),
                Company.access_level == "system"
            ).first()
        else:
            access_level = "personal"
            company = db.query(Company).filter(
                Company.symbol == symbol.upper(),
                Company.organization_id.is_(None),
                Company.access_level == "personal",
                Company.created_by == user_id
            ).first()
    
    if not company:
        company = Company(
            symbol=symbol.upper(),
            name=name,
            market_cap=safe_float(market_cap) * 1_000_000,  
            sector=sector,
            organization_id=organization_id,
            access_level=access_level,
            created_by=user_id
        )
        db.add(company)
        db.flush()  
    else:
        company.name = name
        company.market_cap = safe_float(market_cap) * 1_000_000
        company.sector = sector
    
    return company


# ENHANCED LOGGING SYSTEM FOR WORKER TASKS
class TaskLogger:
    """Enhanced logging for Celery tasks with job and user context"""
    
    def __init__(self, task_name: str = None):
        self.task_name = task_name or "unknown"
        self.start_time = datetime.utcnow()
        
    def log(self, level: str, message: str, **kwargs):
        """Log with enhanced context"""
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        task_id = getattr(current_task.request, 'id', 'no-task-id') if current_task else 'no-task'
        
        # Extract context from kwargs
        job_id = kwargs.get('job_id', 'no-job-id')
        user_id = kwargs.get('user_id', 'no-user')
        file_name = kwargs.get('file_name', 'unknown-file')
        total_rows = kwargs.get('total_rows', 0)
        processed_rows = kwargs.get('processed_rows', 0)
        queue_priority = kwargs.get('queue_priority', 'medium')
        
        # Calculate processing stats
        elapsed_time = (datetime.utcnow() - self.start_time).total_seconds()
        rows_per_second = processed_rows / elapsed_time if elapsed_time > 0 and processed_rows > 0 else 0
        
        # Format enhanced log message
        log_message = (
            f"[{timestamp}] [{level}] [TASK:{self.task_name}] [ID:{task_id}] "
            f"[JOB:{job_id}] [USER:{user_id}] [FILE:{file_name}] "
            f"[ROWS:{processed_rows}/{total_rows}] [QUEUE:{queue_priority}] "
            f"[RATE:{rows_per_second:.1f}/s] [TIME:{elapsed_time:.1f}s] {message}"
        )
        
        print(log_message)
        
        # Also log to standard logger
        logger_method = getattr(logger, level.lower(), logger.info)
        logger_method(f"[{self.task_name}] {message}", extra={
            'task_id': task_id,
            'job_id': job_id,
            'user_id': user_id,
            'file_name': file_name,
            'total_rows': total_rows,
            'processed_rows': processed_rows,
            'queue_priority': queue_priority,
            'rows_per_second': rows_per_second,
            'elapsed_time': elapsed_time
        })
    
    def info(self, message: str, **kwargs):
        self.log('INFO', message, **kwargs)
        
    def error(self, message: str, **kwargs):
        self.log('ERROR', message, **kwargs)
        
    def warning(self, message: str, **kwargs):
        self.log('WARN', message, **kwargs)
        
    def success(self, message: str, **kwargs):
        self.log('SUCCESS', message, **kwargs)

def enhanced_task_logging(task_name: str = None):
    """Decorator to add enhanced logging to Celery tasks"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract context for logging
            job_id = kwargs.get('job_id', args[0] if args else 'unknown')
            user_id = kwargs.get('user_id', 'unknown')
            
            task_logger = TaskLogger(task_name or func.__name__)
            
            # Log task start
            task_logger.info(f"🚀 Task started", 
                           job_id=job_id, 
                           user_id=user_id,
                           **kwargs)
            
            try:
                # Execute the task
                result = func(*args, **kwargs)
                
                # Log successful completion
                task_logger.success(f"✅ Task completed successfully", 
                                  job_id=job_id, 
                                  user_id=user_id,
                                  **kwargs)
                return result
                
            except Exception as e:
                # Log error with full context
                task_logger.error(f"❌ Task failed: {str(e)}", 
                                job_id=job_id, 
                                user_id=user_id,
                                error=str(e),
                                **kwargs)
                
                # Log stack trace for debugging
                task_logger.error(f"📋 Stack trace: {traceback.format_exc()}", 
                                job_id=job_id, 
                                user_id=user_id,
                                **kwargs)
                raise
                
        return wrapper
    return decorator


@celery_app.task(bind=True, name="app.workers.tasks.process_annual_bulk_upload_task")
@enhanced_task_logging("process_annual_bulk_upload_task")
def process_annual_bulk_upload_task(
    self, 
    job_id: str, 
    data: List[Dict[str, Any]], 
    user_id: str, 
    organization_id: Optional[str]
) -> Dict[str, Any]:
    """
    Enhanced Celery task to process annual predictions bulk upload with comprehensive logging
    
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
    
    # Initialize enhanced logger
    task_logger = TaskLogger("process_annual_bulk_upload_task")
    
    # Get job details for logging
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    try:
        job = db.query(BulkUploadJob).filter(BulkUploadJob.id == job_id).first()
        file_name = job.original_filename if job else "unknown-file"
        total_rows = len(data)
        
        # Determine queue priority based on file size
        if total_rows <= 100:
            queue_priority = "high"
        elif total_rows <= 1000:
            queue_priority = "medium"
        else:
            queue_priority = "low"
        
        # Log detailed task start
        task_logger.info(
            f"📊 Starting annual bulk upload processing",
            job_id=job_id,
            user_id=user_id,
            file_name=file_name,
            total_rows=total_rows,
            queue_priority=queue_priority,
            organization_id=organization_id or "global"
        )
        
        # Update job status
        update_job_status(job_id, 'processing')
        
        successful_rows = 0
        failed_rows = 0
        error_details = []
        
        # Progress tracking for large files
        progress_interval = max(1, total_rows // 20)  # Report progress every 5%
        next_progress_report = progress_interval
        
        # Main processing loop with enhanced logging
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
                    # Progress reporting with detailed logging
                    if i >= next_progress_report or i == total_rows - 1:
                        progress_percent = (i / total_rows) * 100
                        elapsed_time = time.time() - start_time
                        rows_per_second = i / elapsed_time if elapsed_time > 0 else 0
                        estimated_remaining = ((total_rows - i) / rows_per_second) if rows_per_second > 0 else 0
                        
                        task_logger.info(
                            f"📈 Processing progress: {progress_percent:.1f}% ({i}/{total_rows} rows)",
                            job_id=job_id,
                            user_id=user_id,
                            file_name=file_name,
                            total_rows=total_rows,
                            processed_rows=i,
                            queue_priority=queue_priority,
                            successful_rows=successful_rows,
                            failed_rows=failed_rows,
                            estimated_remaining_seconds=estimated_remaining
                        )
                        next_progress_report = min(i + progress_interval, total_rows)
                        
                        # Update job progress
                        update_job_status(
                            job_id, 
                            'processing', 
                            processed_rows=i,
                            successful_rows=successful_rows,
                            failed_rows=failed_rows
                        )
                    
                    # Process individual row with error resilience
                    try:
                        company = create_or_get_company(
                            db=db,
                            symbol=row['company_symbol'],
                            name=row['company_name'],
                            market_cap=safe_float(row['market_cap']),
                            sector=row['sector'],
                            organization_id=organization_id,
                            user_id=user_id
                        )
                    
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
                        
                        financial_data = {
                            'long_term_debt_to_total_capital': safe_float(row['long_term_debt_to_total_capital']),
                            'total_debt_to_ebitda': safe_float(row['total_debt_to_ebitda']),
                            'net_income_margin': safe_float(row['net_income_margin']),
                            'ebit_to_interest_expense': safe_float(row['ebit_to_interest_expense']),
                            'return_on_assets': safe_float(row['return_on_assets'])
                        }
                        
                        ml_result = ml_model.predict_default_probability(financial_data)
                        
                        if organization_id:
                            access_level = "organization"
                        else:
                            user = db.query(User).filter(User.id == user_id).first()
                            if user and user.role == "super_admin":
                                access_level = "system"
                            else:
                                access_level = "personal"
                        
                        prediction = AnnualPrediction(
                            id=uuid.uuid4(),
                            company_id=company.id,
                            organization_id=organization_id,
                            access_level=access_level,
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
                            'data': {k: str(v) for k, v in row.items()},  
                            'error': str(e)
                        })
                        
                        # Enhanced error logging for individual rows
                        task_logger.error(
                            f"❌ Row processing failed: {str(e)}",
                            job_id=job_id,
                            user_id=user_id,
                            file_name=file_name,
                            total_rows=total_rows,
                            processed_rows=i,
                            queue_priority=queue_priority,
                            row_number=i+1,
                            company_symbol=row.get('company_symbol', 'unknown'),
                            error=str(e)
                        )
                        
                        db.rollback()
                        continue
                
                except Exception as outer_e:
                    # Handle any other errors not caught by inner try/except
                    failed_rows += 1
                    error_details.append({
                        'row': i + 1,
                        'data': {k: str(v) for k, v in row.items()},  
                        'error': str(outer_e)
                    })
                    
                    task_logger.error(
                        f"❌ Unexpected error processing row {i+1}: {str(outer_e)}",
                        job_id=job_id,
                        user_id=user_id,
                        row_number=i+1,
                        error=str(outer_e)
                    )
                    
                    db.rollback()
                    continue
        
        # Final commit and completion logging
        db.commit()
        
        processing_time = time.time() - start_time
        rows_per_second = total_rows / processing_time if processing_time > 0 else 0
        success_rate = (successful_rows / total_rows * 100) if total_rows > 0 else 0
        
        # Log detailed completion statistics
        task_logger.success(
            f"🎉 Bulk upload completed successfully",
            job_id=job_id,
            user_id=user_id,
            file_name=file_name,
            total_rows=total_rows,
            processed_rows=total_rows,
            queue_priority=queue_priority,
            successful_rows=successful_rows,
            failed_rows=failed_rows,
            success_rate_percent=success_rate,
            processing_time_seconds=processing_time,
            rows_per_second=rows_per_second
        )
        
        update_job_status(
            job_id,
            'completed',
            processed_rows=total_rows,
            successful_rows=successful_rows,
            failed_rows=failed_rows,
            error_details={'errors': error_details[:100]}  
        )
        
        result = {
            "status": "completed",
            "job_id": job_id,
            "total_rows": total_rows,
            "successful_rows": successful_rows,
            "failed_rows": failed_rows,
            "processing_time_seconds": round(processing_time, 2),
            "rows_per_second": round(rows_per_second, 2),
            "success_rate_percent": round(success_rate, 2),
            "errors": error_details[:10]  
        }
        
        return result
        
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        processing_time = time.time() - start_time
        
        # Enhanced error logging for task failures
        task_logger.error(
            f"💥 CRITICAL: Task failed with exception",
            job_id=job_id,
            user_id=user_id,
            file_name=file_name,
            total_rows=total_rows,
            processed_rows=successful_rows + failed_rows,
            queue_priority=queue_priority,
            error=error_msg,
            processing_time_seconds=processing_time
        )
        
        # Log full stack trace for debugging
        task_logger.error(
            f"📋 Full stack trace: {traceback.format_exc()}",
            job_id=job_id,
            user_id=user_id
        )
        
        logger.error(f"Bulk upload job {job_id} failed: {error_msg}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        
        update_job_status(
            job_id,
            'failed',
            error_message=error_msg,
            error_details={'errors': error_details, 'exception': traceback.format_exc()}
        )
        
        self.update_state(
            state="FAILURE",
            meta={
                "status": f"Job failed: {error_msg}",
                "job_id": job_id,
                "error": error_msg,
                "processing_time_seconds": round(processing_time, 2)
            }
        )
        
        return {
            "status": "failed",
            "job_id": job_id,
            "error": error_msg,
            "total_rows": total_rows,
            "successful_rows": successful_rows,
            "failed_rows": failed_rows
        }
    
    finally:
        db.close()


@celery_app.task(bind=True, name="app.workers.tasks.process_quarterly_bulk_upload_task")
@enhanced_task_logging("process_quarterly_bulk_upload_task")
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
                company = create_or_get_company(
                    db=db,
                    symbol=row['company_symbol'],
                    name=row['company_name'],
                    market_cap=safe_float(row['market_cap']),
                    sector=row['sector'],
                    organization_id=organization_id,
                    user_id=user_id
                )
                
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
                
                financial_data = {
                    'total_debt_to_ebitda': safe_float(row['total_debt_to_ebitda']),
                    'sga_margin': safe_float(row['sga_margin']),
                    'long_term_debt_to_total_capital': safe_float(row['long_term_debt_to_total_capital']),
                    'return_on_capital': safe_float(row['return_on_capital'])
                }
                
                ml_result = quarterly_ml_model.predict_quarterly_default_probability(financial_data)
                
                if organization_id:
                    access_level = "organization"
                else:
                    user = db.query(User).filter(User.id == user_id).first()
                    if user and user.role == "super_admin":
                        access_level = "system"
                    else:
                        access_level = "personal"
                
                prediction = QuarterlyPrediction(
                    id=uuid.uuid4(),
                    company_id=company.id,
                    organization_id=organization_id,
                    access_level=access_level,
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
                    
                    except Exception as row_error:
                        failed_rows += 1
                        error_details.append({
                            'row': i + 1,
                            'data': {k: str(v) for k, v in row.items()},  
                            'error': str(row_error)
                        })
                        
                        # Enhanced error logging for individual rows
                        task_logger.error(
                            f"❌ Row processing failed: {str(row_error)}",
                            job_id=job_id,
                            user_id=user_id,
                            file_name=file_name,
                            total_rows=total_rows,
                            processed_rows=i,
                            queue_priority=queue_priority,
                            row_number=i+1,
                            company_symbol=row.get('company_symbol', 'unknown'),
                            error=str(row_error)
                        )
                        
                        db.rollback()
                        continue
                
                except Exception as outer_e:
                    # Handle any other errors not caught by inner try/except
                    failed_rows += 1
                    error_details.append({
                        'row': i + 1,
                        'data': {k: str(v) for k, v in row.items()},  
                        'error': str(outer_e)
                    })
                    
                    task_logger.error(
                        f"❌ Unexpected error processing row {i+1}: {str(outer_e)}",
                        job_id=job_id,
                        user_id=user_id,
                        row_number=i+1,
                        error=str(outer_e)
                    )
                    
                    db.rollback()
                    continue
            
            # Final commit and completion logging
            db.commit()
            
            processing_time = time.time() - start_time
            
            update_job_status(
                job_id,
                'completed',
                processed_rows=total_rows,
                successful_rows=successful_rows,
                failed_rows=failed_rows,
                error_details={'errors': error_details[:100]}  
            )
            
            result = {
                "status": "completed",
                "job_id": job_id,
                "total_rows": total_rows,
                "successful_rows": successful_rows,
                "failed_rows": failed_rows,
                "processing_time_seconds": round(processing_time, 2),
                "errors": error_details[:10]  
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
            
            return {
                "status": "failed",
                "job_id": job_id,
                "error": error_msg,
                "total_rows": len(data) if 'data' in locals() else 0,
                "successful_rows": successful_rows,
                "failed_rows": failed_rows
            }
            
        finally:
            db.close()


@celery_app.task(bind=True, name="app.workers.tasks.process_bulk_excel_task")
@enhanced_task_logging("process_bulk_excel_task")
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
@enhanced_task_logging("process_bulk_normalized_task")
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
        file_content = base64.b64decode(file_content_b64)
        
        if original_filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(file_content.decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(file_content))
        
        total_companies = len(df)
        
        if prediction_type == "annual":
            required_columns = [
                'stock_symbol', 'company_name',
                'long_term_debt_to_total_capital', 'total_debt_to_ebitda', 
                'net_income_margin', 'ebit_to_interest_expense', 'return_on_assets'
            ]
        else:  
            required_columns = [
                'stock_symbol', 'company_name', 'reporting_year', 'reporting_quarter',
                'total_debt_to_ebitda', 'sga_margin', 
                'long_term_debt_to_total_capital', 'return_on_capital'
            ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
        
        optional_columns = {
            'market_cap': 1000000000,
            'sector': 'Unknown',
            'reporting_year': '2024',
            'reporting_quarter': 'Q3',  
        }
        
        for col, default_value in optional_columns.items():
            if col not in df.columns:
                df[col] = default_value
        
        company_service = CompanyService(db)
        
        for index, row in df.iterrows():
            try:
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
                
                stock_symbol = str(row['stock_symbol']).strip().upper()
                company_name = str(row['company_name']).strip()
                
                if not stock_symbol or not company_name or stock_symbol.lower() == 'nan' or company_name.lower() == 'nan':
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
                
                reporting_year = str(row.get('reporting_year', '2024')).strip()
                reporting_quarter = str(row.get('reporting_quarter', 'Q4')).strip()
                
                company = company_service.create_company(
                    symbol=stock_symbol,
                    name=company_name,
                    market_cap=market_cap,
                    sector=sector,
                    organization_id=organization_id,
                    created_by=created_by
                )
                
                if prediction_type == "annual":
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
                    
                else: 
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
@enhanced_task_logging("process_quarterly_bulk_task")
def process_quarterly_bulk_task(file_content_b64: str, original_filename: str, organization_id: str = None, created_by: str = None):
    """
    Process quarterly bulk prediction file in background
    """
    from ..services.quarterly_ml_service import quarterly_ml_model
    
    start_time = time.time()
    db = get_session_local()
    
    try:
        current_task.update_state(
            state='PROGRESS',
            meta={'status': 'Processing quarterly file...', 'progress': 0}
        )
        
        file_content = base64.b64decode(file_content_b64)
        
        if original_filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(file_content.decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(file_content))
        
        total_companies = len(df)
        company_service = CompanyService(db)
        
        results = []
        successful_predictions = 0
        failed_predictions = 0
        
        for index, row in df.iterrows():
            try:
                progress = int((index / total_companies) * 100)
                current_task.update_state(
                    state='PROGRESS',
                    meta={
                        'status': f'Processing company {index + 1}/{total_companies}',
                        'progress': progress,
                        'current_company': row.get('stock_symbol', 'Unknown')
                    }
                )
                
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
                
                financial_ratios = {
                    "total_debt_to_ebitda": safe_float(row['total_debt_to_ebitda']),
                    "sga_margin": safe_float(row['sga_margin']),
                    "long_term_debt_to_total_capital": safe_float(row['long_term_debt_to_total_capital']),
                    "return_on_capital": safe_float(row['return_on_capital'])
                }
                
                missing_ratios = [k for k, v in financial_ratios.items() if v is None]
                if missing_ratios:
                    results.append({
                        "stock_symbol": stock_symbol,
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
