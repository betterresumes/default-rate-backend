import logging
import math
import time
import traceback
import uuid
import json
import io
import base64
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional
from celery import current_task
from functools import wraps

from ..workers.celery_app import celery_app
from ..core.database import get_session_local, BulkUploadJob, Company, AnnualPrediction, QuarterlyPrediction, User, Organization
from ..services.ml_service import ml_model
from ..services.quarterly_ml_service import quarterly_ml_model

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


def normalize_quarter(quarter_value):
    """Convert quarter value to standard string format (Q1, Q2, Q3, Q4)"""
    if isinstance(quarter_value, str):
        # If already in correct format, return as is
        if quarter_value.upper() in ['Q1', 'Q2', 'Q3', 'Q4']:
            return quarter_value.upper()
        # Handle other string formats
        quarter_value = quarter_value.strip().upper()
        if quarter_value in ['1', '2', '3', '4']:
            return f'Q{quarter_value}'
    
    # Handle integer values
    try:
        quarter_int = int(quarter_value)
        if quarter_int in [1, 2, 3, 4]:
            return f'Q{quarter_int}'
    except (ValueError, TypeError):
        pass
    
    # Default fallback
    logger.warning(f"Invalid quarter value: {quarter_value}, defaulting to Q1")
    return 'Q1'


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
            market_cap=safe_float(market_cap),  # Market cap already in millions
            sector=sector,
            organization_id=organization_id,
            access_level=access_level,
            created_by=user_id
        )
        db.add(company)
        db.flush()  
    else:
        company.name = name
        company.market_cap = safe_float(market_cap)  # Market cap already in millions
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
    
    def log_task_start(self, message: str, **kwargs):
        """Log task start with full context"""
        self.info(f"🚀 Task started")
        self.info(message, **kwargs)
        
    def log_progress(self, message: str, **kwargs):
        """Log progress updates"""
        self.info(message, **kwargs)
        
    def log_completion(self, message: str, **kwargs):
        """Log task completion"""
        self.success(message, **kwargs)
        
    def warning(self, message: str, **kwargs):
        self.log('WARN', message, **kwargs)
        
    def success(self, message: str, **kwargs):
        self.log('SUCCESS', message, **kwargs)


def enhanced_task_logging(task_name: str = None):
    """Decorator to add enhanced logging to Celery tasks"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Robust parameter extraction for bulk upload tasks
            try:
                # Debug log the actual parameters received
                logger.info(f"🔍 ENHANCED LOGGING DEBUG: args={[str(arg)[:50] + '...' if len(str(arg)) > 50 else str(arg) for arg in args]}, kwargs={kwargs}")
                
                # For bind=True tasks, args[0] is self, so parameters start at args[1]
                if len(args) >= 2:
                    job_id = args[1]  # First parameter after self
                    if not job_id or job_id in ['', 'null', 'undefined']:
                        job_id = 'no-job-id'
                        logger.warning(f"⚠️ Empty job_id detected in args[1]")
                else:
                    job_id = kwargs.get('job_id', 'no-job-id')
                    logger.warning(f"⚠️ job_id not found in args, using kwargs: {job_id}")
                    
                if len(args) >= 4:
                    user_id = args[3]  # Third parameter after self (self, job_id, data, user_id)
                    if not user_id or user_id in ['', 'null', 'undefined']:
                        user_id = 'no-user'
                        logger.warning(f"⚠️ Empty user_id detected in args[3]")
                else:
                    user_id = kwargs.get('user_id', 'no-user')
                    logger.warning(f"⚠️ user_id not found in args, using kwargs: {user_id}")
                    
            except Exception as e:
                job_id = 'extraction-error'
                user_id = 'extraction-error'
                logger.error(f"Parameter extraction error in enhanced_task_logging: {e}")
            
            task_logger = TaskLogger(task_name or func.__name__)
            
            # Log task start with safe parameter access
            try:
                task_logger.info(f"🚀 Task started", 
                               job_id=job_id, 
                               user_id=user_id,
                               args_count=len(args),
                               kwargs_keys=list(kwargs.keys()) if kwargs else [])
            except Exception as log_error:
                logger.error(f"Error in task start logging: {log_error}")
            
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
    
    # CRITICAL: Validate task parameters immediately
    if not job_id or job_id in ['', 'undefined', 'null']:
        logger.error(f"❌ CRITICAL: Invalid job_id parameter: {job_id}")
        raise ValueError(f"Invalid job_id parameter: {job_id}")
        
    if not user_id or user_id in ['', 'undefined', 'null']:
        logger.error(f"❌ CRITICAL: Invalid user_id parameter: {user_id}")
        raise ValueError(f"Invalid user_id parameter: {user_id}")
        
    if not data or not isinstance(data, list):
        logger.error(f"❌ CRITICAL: Invalid data parameter: {type(data)}, length: {len(data) if hasattr(data, '__len__') else 'N/A'}")
        raise ValueError(f"Invalid data parameter: {type(data)}")
        
    logger.info(f"✅ Task parameter validation passed: job_id={job_id}, user_id={user_id}, data_rows={len(data)}, org_id={organization_id}")
    
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
                        
                except Exception as outer_error:
                    # Handle any errors not caught by nested try/except in row processing
                    failed_rows += 1
                    error_details.append({
                        'row': i + 1,
                        'error': f"Outer processing error: {str(outer_error)}"
                    })
                    
                    task_logger.error(
                        f"❌ Outer processing error on row {i+1}: {str(outer_error)}",
                        job_id=job_id,
                        user_id=user_id,
                        row_number=i+1,
                        error=str(outer_error)
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
        
        except Exception as processing_error:
            # Handle any errors during the main processing loop
            task_logger.error(
                f"❌ Main processing loop failed: {str(processing_error)}",
                job_id=job_id,
                user_id=user_id,
                error=str(processing_error)
            )
            
            # Update job status to failed
            update_job_status(
                job_id,
                'failed',
                processed_rows=len(data) if 'data' in locals() else 0,
                successful_rows=successful_rows if 'successful_rows' in locals() else 0,
                failed_rows=failed_rows if 'failed_rows' in locals() else 0,
                error_message=str(processing_error)
            )
            
            raise processing_error  # Re-raise to be caught by function-level except
        
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
        
        # Use empty list if error_details is not defined yet
        error_list = locals().get('error_details', [])
        
        update_job_status(
            job_id,
            'failed',
            error_message=error_msg,
            error_details={'errors': error_list, 'exception': traceback.format_exc()}
        )
        
        self.update_state(
            state="FAILURE",
            meta={
                "status": f"Job failed: {error_msg}",
                "job_id": job_id,
                "error": error_msg,
                "processing_time_seconds": round(processing_time, 2),
                "exc_type": type(e).__name__,
                "exc_message": error_msg
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
    Enhanced Celery task to process quarterly predictions bulk upload with comprehensive logging
    
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
    
    # CRITICAL: Validate task parameters immediately
    if not job_id or job_id in ['', 'undefined', 'null']:
        logger.error(f"❌ CRITICAL: Invalid job_id parameter: {job_id}")
        raise ValueError(f"Invalid job_id parameter: {job_id}")
        
    if not user_id or user_id in ['', 'undefined', 'null']:
        logger.error(f"❌ CRITICAL: Invalid user_id parameter: {user_id}")
        raise ValueError(f"Invalid user_id parameter: {user_id}")
        
    if not data or not isinstance(data, list):
        logger.error(f"❌ CRITICAL: Invalid data parameter: {type(data)}, length: {len(data) if hasattr(data, '__len__') else 'N/A'}")
        raise ValueError(f"Invalid data parameter: {type(data)}")
        
    logger.info(f"✅ Task parameter validation passed: job_id={job_id}, user_id={user_id}, data_rows={len(data)}, org_id={organization_id}")
    
    # Initialize enhanced logger
    task_logger = TaskLogger("process_quarterly_bulk_upload_task")
    
    # Initialize error tracking
    error_details = []
    successful_rows = 0
    failed_rows = 0
    
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
        task_logger.log_task_start(
            f"📊 Starting quarterly bulk upload processing",
            job_id=job_id,
            user_id=user_id,
            file_name=file_name,
            total_rows=total_rows,
            processed_rows=0,
            queue_priority=queue_priority,
            successful_rows=0,
            failed_rows=0,
            success_rate_percent=0,
            processing_time_seconds=0,
            rows_per_second=0
        )
        
        update_job_status(job_id, 'processing')
        
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
                
                # Normalize quarter format
                normalized_quarter = normalize_quarter(row['reporting_quarter'])
                
                existing_prediction = db.query(QuarterlyPrediction).filter(
                    QuarterlyPrediction.company_id == company.id,
                    QuarterlyPrediction.reporting_year == str(row['reporting_year']),
                    QuarterlyPrediction.reporting_quarter == normalized_quarter
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
                
                logger.info(f"🔍 DEBUG: Processing row {i+1}/{len(data)} - {row['company_symbol']} with financial_data: {financial_data}")
                
                # Check for None/invalid values that might cause hanging
                for key, value in financial_data.items():
                    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
                        logger.warning(f"⚠️ DEBUG: Invalid value for {key}: {value} in row {i+1}")
                
                try:
                    import signal
                    
                    def timeout_handler(signum, frame):
                        raise TimeoutError("ML prediction timed out")
                    
                    # Set a 30-second timeout for ML prediction
                    signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(30)  # 30 seconds timeout
                    
                    try:
                        ml_result = quarterly_ml_model.predict_quarterly_default_probability(financial_data)
                        signal.alarm(0)  # Cancel the alarm
                        logger.info(f"✅ DEBUG: ML prediction successful for {row['company_symbol']}: {ml_result.get('logistic_probability', 'N/A')}")
                    except TimeoutError:
                        signal.alarm(0)  # Cancel the alarm
                        logger.error(f"⏰ DEBUG: ML prediction timed out for {row['company_symbol']} after 30 seconds")
                        failed_rows += 1
                        error_details.append({
                            'row': i + 1,
                            'error': f"ML prediction timed out after 30 seconds"
                        })
                        continue
                        
                except Exception as ml_error:
                    signal.alarm(0)  # Cancel the alarm if set
                    logger.error(f"❌ DEBUG: ML prediction failed for {row['company_symbol']}: {str(ml_error)}")
                    failed_rows += 1
                    error_details.append({
                        'row': i + 1,
                        'error': f"ML prediction failed: {str(ml_error)}"
                    })
                    continue
                
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
                    reporting_quarter=normalized_quarter,
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
                
                # Enhanced progress logging every 7 rows or at specific intervals
                if (i + 1) % 7 == 0 or (i + 1) in [1, 5, 10, 15, 20] or (i + 1) == total_rows:
                    current_time = time.time()
                    processing_time = current_time - start_time
                    rows_per_second = (i + 1) / processing_time if processing_time > 0 else 0
                    progress_percent = ((i + 1) / total_rows) * 100 if total_rows > 0 else 0
                    success_rate = (successful_rows / (i + 1)) * 100 if (i + 1) > 0 else 0
                    
                    # Database commit for progress updates
                    db.commit()
                    update_job_status(
                        job_id, 
                        'processing',
                        processed_rows=i + 1,
                        successful_rows=successful_rows,
                        failed_rows=failed_rows
                    )
                    
                    # Enhanced progress logging
                    task_logger.log_progress(
                        f"📈 Processing progress: {progress_percent:.1f}% ({i + 1}/{total_rows} rows)",
                        job_id=job_id,
                        user_id=user_id,
                        file_name=file_name,
                        total_rows=total_rows,
                        processed_rows=i + 1,
                        queue_priority=queue_priority,
                        successful_rows=successful_rows,
                        failed_rows=failed_rows,
                        success_rate_percent=success_rate,
                        processing_time_seconds=processing_time,
                        rows_per_second=rows_per_second
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
                elif (i + 1) % 50 == 0:  # Fallback for larger files
                    db.commit()
                    update_job_status(
                        job_id, 
                        'processing',
                        processed_rows=i + 1,
                        successful_rows=successful_rows,
                        failed_rows=failed_rows
                    )
                    
            except Exception as row_error:
                failed_rows += 1
                error_details.append({
                    'row': i + 1,
                    'data': {k: str(v) for k, v in row.items()},  
                    'error': str(row_error)
                })
                
                db.rollback()
                continue
            
        # Final commit and completion logging
        db.commit()
        
        processing_time = time.time() - start_time
        rows_per_second = total_rows / processing_time if processing_time > 0 else 0
        success_rate = (successful_rows / total_rows) * 100 if total_rows > 0 else 0
        
        # Enhanced completion logging
        task_logger.log_completion(
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
        logger.error(f"Bulk upload job {job_id} failed: {error_msg}")
        
        # Use empty list if error_details is not defined yet
        error_list = locals().get('error_details', [])
        
        update_job_status(
            job_id,
            'failed',
            error_message=error_msg,
            error_details={'errors': error_list}
        )
        
        self.update_state(
            state="FAILURE",
            meta={
                "status": f"Job failed: {error_msg}",
                "job_id": job_id,
                "error": error_msg,
                "exc_type": type(e).__name__,
                "exc_message": error_msg
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
    error_details = []
    successful_predictions = 0
    failed_predictions = 0
    total_companies = 0
    
    try:
        file_content = base64.b64decode(file_content_b64)
        df = pd.read_excel(io.BytesIO(file_content))
        total_companies = len(df)
        
        # Process each company...
        for i, row in df.iterrows():
            try:
                company_symbol = row.get('stock_symbol')
                company_name = row.get('company_name')
                market_cap = row.get('market_cap')
                sector = row.get('sector')
                
                # Basic validation
                if not company_symbol or not company_name:
                    failed_predictions += 1
                    error_details.append({
                        'row': i + 1,
                        'error': "Missing required fields: 'stock_symbol' or 'company_name'"
                    })
                    continue
                
                # Create or get company
                company = create_or_get_company(
                    db=db,
                    symbol=company_symbol,
                    name=company_name,
                    market_cap=market_cap,
                    sector=sector,
                    organization_id=None,  # Global scope for bulk upload
                    user_id="system"  # System user for bulk uploads
                )
                
                # For each financial metric, predict default probability
                financial_metrics = ['long_term_debt_to_total_capital', 'total_debt_to_ebitda', 
                                    'net_income_margin', 'ebit_to_interest_expense', 'return_on_assets']
                
                for metric in financial_metrics:
                    if metric not in row or row[metric] is None:
                        failed_predictions += 1
                        error_details.append({
                            'row': i + 1,
                            'error': f"Missing value for financial metric: {metric}"
                        })
                        break
                
                # Predict using ML model
                financial_data = {metric: safe_float(row[metric]) for metric in financial_metrics}
                ml_result = ml_model.predict_default_probability(financial_data)
                
                # Save prediction result
                prediction = AnnualPrediction(
                    id=uuid.uuid4(),
                    company_id=company.id,
                    organization_id=None,  # Global scope
                    access_level="system",  # System access for bulk uploads
                    reporting_year=str(row['reporting_year']),
                    reporting_quarter=row.get('reporting_quarter'),
                    long_term_debt_to_total_capital=safe_float(row['long_term_debt_to_total_capital']),
                    total_debt_to_ebitda=safe_float(row['total_debt_to_ebitda']),
                    net_income_margin=safe_float(row['net_income_margin']),
                    ebit_to_interest_expense=safe_float(row['ebit_to_interest_expense']),
                    return_on_assets=safe_float(row['return_on_assets']),
                    probability=safe_float(ml_result['probability']),
                    risk_level=ml_result['risk_level'],
                    confidence=safe_float(ml_result['confidence']),
                    predicted_at=datetime.utcnow(),
                    created_by="system"  # System user
                )
                
                db.add(prediction)
                successful_predictions += 1
                
                # Commit in batches
                if (i + 1) % 50 == 0:
                    db.commit()
                    self.update_state(
                        state="PROGRESS",
                        meta={
                            "status": f"Processed {i + 1}/{total_companies} companies",
                            "current": i + 1,
                            "total": total_companies,
                            "successful": successful_predictions,
                            "failed": failed_predictions,
                            "job_id": task_id
                        }
                    )
            
            except Exception as e:
                failed_predictions += 1
                error_details.append({
                    'row': i + 1,
                    'data': {k: str(v) for k, v in row.items()},  
                    'error': str(e)
                })
                
                db.rollback()
                continue
        
        # Final commit
        db.commit()
        
        processing_time = time.time() - start_time
        
        self.update_state(
            state="SUCCESS",
            meta={
                'status': 'Bulk processing completed',
                'total_companies': total_companies,
                'successful_predictions': successful_predictions,
                'failed_predictions': failed_predictions,
                'processing_time': processing_time
            }
        )
        
        return {
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


@celery_app.task(name="app.workers.tasks.process_quarterly_bulk_task")
@enhanced_task_logging("process_quarterly_bulk_task")
def process_quarterly_bulk_task(file_content_b64: str, original_filename: str, organization_id: str = None, created_by: str = None):
    """
    Process quarterly bulk prediction file in background
    """
    start_time = time.time()
    SessionLocal = get_session_local()
    db = SessionLocal()
    
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
                
                # Process individual quarterly prediction
                company_symbol = row.get('stock_symbol')
                company_name = row.get('company_name')
                market_cap = row.get('market_cap')
                sector = row.get('sector')
                
                # Create or get company
                company = create_or_get_company(
                    db=db,
                    symbol=company_symbol,
                    name=company_name,
                    market_cap=market_cap,
                    sector=sector,
                    organization_id=organization_id,
                    user_id=created_by
                )
                
                # Check if prediction already exists
                existing_prediction = db.query(QuarterlyPrediction).filter(
                    QuarterlyPrediction.company_id == company.id,
                    QuarterlyPrediction.reporting_year == str(row['reporting_year']),
                    QuarterlyPrediction.reporting_quarter == row['reporting_quarter']
                ).first()
                
                if existing_prediction:
                    failed_predictions += 1
                    results.append({
                        "stock_symbol": company_symbol,
                        "company_name": company_name,
                        "success": False,
                        "error": f"Prediction already exists for {row['reporting_year']} Q{row['reporting_quarter']}"
                    })
                    continue
                
                # Prepare financial data for prediction
                financial_data = {
                    'total_debt_to_ebitda': safe_float(row['total_debt_to_ebitda']),
                    'sga_margin': safe_float(row['sga_margin']),
                    'long_term_debt_to_total_capital': safe_float(row['long_term_debt_to_total_capital']),
                    'return_on_capital': safe_float(row['return_on_capital'])
                }
                
                # Predict using ML model
                ml_result = quarterly_ml_model.predict_quarterly_default_probability(financial_data)
                
                # Save prediction result
                prediction = QuarterlyPrediction(
                    id=uuid.uuid4(),
                    company_id=company.id,
                    organization_id=organization_id,
                    access_level="organization" if organization_id else "personal",
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
                    created_by=created_by
                )
                
                db.add(prediction)
                successful_predictions += 1
                
            except Exception as e:
                failed_predictions += 1
                results.append({
                    "stock_symbol": row.get('stock_symbol', 'Unknown'),
                    "company_name": row.get('company_name', 'Unknown'),
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


# Simple health check task for debugging parameter passing
@celery_app.task(bind=True, name="app.workers.tasks.health_check")
def health_check_task(self, test_param: str = "default"):
    """Simple health check task to verify parameter passing"""
    task_id = self.request.id
    logger.info(f"✅ Health check task received: task_id={task_id}, test_param='{test_param}'")
    
    return {
        "status": "healthy",
        "task_id": task_id,
        "test_param": test_param,
        "message": "Worker is healthy and receiving parameters correctly"
    }
