#!/usr/bin/env python3

import os
import sys
import pandas as pd
import time
import traceback
import math
from datetime import datetime
from typing import Dict, Any, List, Optional
from celery import current_task

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

def update_chunk_progress(
    job_id: str,
    chunk_index: int,
    chunk_rows_processed: int,
    chunk_rows_successful: int,
    chunk_rows_failed: int,
    is_chunk_complete: bool = False,
    error_message: Optional[str] = None
):
    """Update job progress when a chunk is processed"""
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    try:
        job = db.query(BulkUploadJob).filter(BulkUploadJob.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found for chunk progress update")
            return
        
        # Update processed rows (atomic increment)
        job.processed_rows = (job.processed_rows or 0) + chunk_rows_processed
        job.successful_rows = (job.successful_rows or 0) + chunk_rows_successful
        job.failed_rows = (job.failed_rows or 0) + chunk_rows_failed
        
        if is_chunk_complete:
            job.completed_chunks = (job.completed_chunks or 0) + 1
            logger.info(f"Job {job_id}: Completed chunk {chunk_index}, total completed: {job.completed_chunks}/{job.total_chunks}")
        
        # Check if all chunks are complete
        if job.completed_chunks >= (job.total_chunks or 1):
            job.status = 'completed'
            job.completed_at = datetime.utcnow()
            logger.info(f"Job {job_id}: All chunks completed! Final stats - Total: {job.processed_rows}, Success: {job.successful_rows}, Failed: {job.failed_rows}")
        
        # Update error message if provided
        if error_message:
            job.error_message = error_message
            
        job.updated_at = datetime.utcnow()
        
        db.commit()
        
    except Exception as e:
        logger.error(f"Error updating chunk progress: {str(e)}")
        db.rollback()
    finally:
        db.close()

@celery_app.task(bind=True, name="process_chunk_task")
def process_chunk_task(
    self, 
    job_id: str, 
    chunk_data: Dict[str, Any], 
    chunk_index: int,
    job_type: str,
    total_chunks: int
):
    """
    Process a single chunk of data for bulk upload
    This enables parallel processing of large files
    
    Args:
        job_id: UUID of the bulk upload job
        chunk_data: Dictionary containing chunk data and metadata
        chunk_index: Index of this chunk (0-based)
        job_type: Type of job (annual/quarterly)
        total_chunks: Total number of chunks in the job
    """
    
    task_id = self.request.id
    logger.info(f"Starting chunk {chunk_index+1}/{total_chunks} for job {job_id} (Task: {task_id})")
    
    try:
        # Convert chunk data back to DataFrame
        df = pd.DataFrame(chunk_data['data'])
        chunk_start_row = chunk_data['chunk_start_row']
        chunk_end_row = chunk_data['chunk_end_row']
        
        logger.info(f"Processing chunk {chunk_index}: rows {chunk_start_row}-{chunk_end_row} ({len(df)} records)")
        
        # Initialize counters
        processed_count = 0
        success_count = 0
        failed_count = 0
        
        # Process based on job type
        if job_type == 'annual':
            success_count, failed_count = process_annual_chunk(job_id, df, chunk_index)
        elif job_type == 'quarterly':
            success_count, failed_count = process_quarterly_chunk(job_id, df, chunk_index)
        else:
            raise ValueError(f"Unsupported job type: {job_type}")
        
        processed_count = len(df)
        
        # Update progress
        update_chunk_progress(
            job_id=job_id,
            chunk_index=chunk_index,
            chunk_rows_processed=processed_count,
            chunk_rows_successful=success_count,
            chunk_rows_failed=failed_count,
            is_chunk_complete=True
        )
        
        # Update Celery task progress
        self.update_state(
            state='SUCCESS',
            meta={
                'chunk_index': chunk_index,
                'processed': processed_count,
                'successful': success_count,
                'failed': failed_count,
                'message': f'Chunk {chunk_index+1}/{total_chunks} completed successfully'
            }
        )
        
        logger.info(f"Chunk {chunk_index+1}/{total_chunks} completed: {success_count} success, {failed_count} failed")
        
        return {
            'chunk_index': chunk_index,
            'processed': processed_count,
            'successful': success_count,
            'failed': failed_count,
            'status': 'completed'
        }
        
    except Exception as e:
        error_msg = f"Error processing chunk {chunk_index}: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        
        # Update progress with error
        update_chunk_progress(
            job_id=job_id,
            chunk_index=chunk_index,
            chunk_rows_processed=len(chunk_data.get('data', [])),
            chunk_rows_successful=0,
            chunk_rows_failed=len(chunk_data.get('data', [])),
            is_chunk_complete=True,
            error_message=error_msg
        )
        
        # Update Celery task state
        self.update_state(
            state='FAILURE',
            meta={
                'chunk_index': chunk_index,
                'error': error_msg,
                'message': f'Chunk {chunk_index+1}/{total_chunks} failed'
            }
        )
        
        raise

def process_annual_chunk(job_id: str, chunk_df: pd.DataFrame, chunk_index: int) -> tuple[int, int]:
    """Process a chunk for annual predictions"""
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    success_count = 0
    failed_count = 0
    
    try:
        # Get job info
        job = db.query(BulkUploadJob).filter(BulkUploadJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        for index, row in chunk_df.iterrows():
            try:
                # Extract and validate data
                ticker = str(row.get('ticker', '')).strip().upper()
                
                if not ticker:
                    failed_count += 1
                    continue
                
                # Get or create company
                company = db.query(Company).filter(Company.ticker == ticker).first()
                if not company:
                    company = Company(
                        ticker=ticker,
                        company_name=str(row.get('company_name', ticker)),
                        organization_id=job.organization_id
                    )
                    db.add(company)
                    db.flush()
                
                # Prepare features for ML model
                features = {
                    'total_debt_to_total_capital': safe_float(row.get('total_debt_to_total_capital')),
                    'long_term_debt_to_total_capital': safe_float(row.get('long_term_debt_to_total_capital')),
                    'total_debt_to_ebitda': safe_float(row.get('total_debt_to_ebitda')),
                    'free_cash_flow_to_total_debt': safe_float(row.get('free_cash_flow_to_total_debt')),
                    'net_income_to_total_capital': safe_float(row.get('net_income_to_total_capital')),
                    'return_on_total_capital': safe_float(row.get('return_on_total_capital')),
                    'return_on_assets': safe_float(row.get('return_on_assets')),
                    'return_on_equity': safe_float(row.get('return_on_equity')),
                    'earnings_before_interest_to_total_capital': safe_float(row.get('earnings_before_interest_to_total_capital')),
                    'ebitda_interest_coverage_ratio': safe_float(row.get('ebitda_interest_coverage_ratio')),
                    'short_long_term_debt_to_total_capital': safe_float(row.get('short_long_term_debt_to_total_capital')),
                }
                
                # Get ML prediction
                prediction_result = ml_model.predict_annual(features)
                
                # Create prediction record
                prediction = AnnualPrediction(
                    company_id=company.id,
                    organization_id=job.organization_id,
                    user_id=job.user_id,
                    
                    # Original features
                    total_debt_to_total_capital=features['total_debt_to_total_capital'],
                    long_term_debt_to_total_capital=features['long_term_debt_to_total_capital'],
                    total_debt_to_ebitda=features['total_debt_to_ebitda'],
                    free_cash_flow_to_total_debt=features['free_cash_flow_to_total_debt'],
                    net_income_to_total_capital=features['net_income_to_total_capital'],
                    return_on_total_capital=features['return_on_total_capital'],
                    return_on_assets=features['return_on_assets'],
                    return_on_equity=features['return_on_equity'],
                    earnings_before_interest_to_total_capital=features['earnings_before_interest_to_total_capital'],
                    ebitda_interest_coverage_ratio=features['ebitda_interest_coverage_ratio'],
                    short_long_term_debt_to_total_capital=features['short_long_term_debt_to_total_capital'],
                    
                    # Prediction results
                    predicted_default_rate=prediction_result['default_rate'],
                    confidence_score=prediction_result.get('confidence', 0.0),
                    risk_category=prediction_result.get('risk_category', 'Medium'),
                    
                    bulk_upload_job_id=job.id,
                    chunk_index=chunk_index,
                    row_index=index
                )
                
                db.add(prediction)
                success_count += 1
                
            except Exception as e:
                logger.error(f"Error processing row {index} in chunk {chunk_index}: {str(e)}")
                failed_count += 1
                continue
        
        db.commit()
        
    except Exception as e:
        logger.error(f"Error in annual chunk processing: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()
    
    return success_count, failed_count

def process_quarterly_chunk(job_id: str, chunk_df: pd.DataFrame, chunk_index: int) -> tuple[int, int]:
    """Process a chunk for quarterly predictions"""
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    success_count = 0
    failed_count = 0
    
    try:
        # Get job info
        job = db.query(BulkUploadJob).filter(BulkUploadJob.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        for index, row in chunk_df.iterrows():
            try:
                # Extract and validate data
                ticker = str(row.get('ticker', '')).strip().upper()
                quarter = str(row.get('quarter', '')).strip()
                year = int(row.get('year', 0))
                
                if not ticker or not quarter or not year:
                    failed_count += 1
                    continue
                
                # Get or create company
                company = db.query(Company).filter(Company.ticker == ticker).first()
                if not company:
                    company = Company(
                        ticker=ticker,
                        company_name=str(row.get('company_name', ticker)),
                        organization_id=job.organization_id
                    )
                    db.add(company)
                    db.flush()
                
                # Prepare features for ML model
                features = {
                    'total_debt_to_total_capital': safe_float(row.get('total_debt_to_total_capital')),
                    'long_term_debt_to_total_capital': safe_float(row.get('long_term_debt_to_total_capital')),
                    'total_debt_to_ebitda': safe_float(row.get('total_debt_to_ebitda')),
                    'free_cash_flow_to_total_debt': safe_float(row.get('free_cash_flow_to_total_debt')),
                    'net_income_to_total_capital': safe_float(row.get('net_income_to_total_capital')),
                    'return_on_total_capital': safe_float(row.get('return_on_total_capital')),
                    'return_on_assets': safe_float(row.get('return_on_assets')),
                    'return_on_equity': safe_float(row.get('return_on_equity')),
                    'earnings_before_interest_to_total_capital': safe_float(row.get('earnings_before_interest_to_total_capital')),
                    'ebitda_interest_coverage_ratio': safe_float(row.get('ebitda_interest_coverage_ratio')),
                    'short_long_term_debt_to_total_capital': safe_float(row.get('short_long_term_debt_to_total_capital')),
                }
                
                # Get ML prediction
                prediction_result = quarterly_ml_model.predict_quarterly(features)
                
                # Create prediction record
                prediction = QuarterlyPrediction(
                    company_id=company.id,
                    organization_id=job.organization_id,
                    user_id=job.user_id,
                    
                    quarter=quarter,
                    year=year,
                    
                    # Original features
                    total_debt_to_total_capital=features['total_debt_to_total_capital'],
                    long_term_debt_to_total_capital=features['long_term_debt_to_total_capital'],
                    total_debt_to_ebitda=features['total_debt_to_ebitda'],
                    free_cash_flow_to_total_debt=features['free_cash_flow_to_total_debt'],
                    net_income_to_total_capital=features['net_income_to_total_capital'],
                    return_on_total_capital=features['return_on_total_capital'],
                    return_on_assets=features['return_on_assets'],
                    return_on_equity=features['return_on_equity'],
                    earnings_before_interest_to_total_capital=features['earnings_before_interest_to_total_capital'],
                    ebitda_interest_coverage_ratio=features['ebitda_interest_coverage_ratio'],
                    short_long_term_debt_to_total_capital=features['short_long_term_debt_to_total_capital'],
                    
                    # Prediction results
                    predicted_default_rate=prediction_result['default_rate'],
                    confidence_score=prediction_result.get('confidence', 0.0),
                    risk_category=prediction_result.get('risk_category', 'Medium'),
                    
                    bulk_upload_job_id=job.id,
                    chunk_index=chunk_index,
                    row_index=index
                )
                
                db.add(prediction)
                success_count += 1
                
            except Exception as e:
                logger.error(f"Error processing row {index} in chunk {chunk_index}: {str(e)}")
                failed_count += 1
                continue
        
        db.commit()
        
    except Exception as e:
        logger.error(f"Error in quarterly chunk processing: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()
    
    return success_count, failed_count
