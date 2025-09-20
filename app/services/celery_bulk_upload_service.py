#!/usr/bin/env python3

import pandas as pd
import io
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.core.database import get_session_local, BulkUploadJob
import uuid
import logging

logger = logging.getLogger(__name__)


class CeleryBulkUploadService:
    """
    Bulk upload service that uses Celery workers instead of FastAPI BackgroundTasks
    for more robust, scalable processing
    """
    
    async def create_bulk_upload_job(
        self, 
        user_id: str,
        organization_id: Optional[str],
        job_type: str,
        filename: str,
        file_size: int,
        total_rows: int
    ) -> str:
        """Create a new bulk upload job"""
        SessionLocal = get_session_local()
        db = SessionLocal()
        
        try:
            job = BulkUploadJob(
                user_id=user_id,
                organization_id=organization_id,
                job_type=job_type,
                original_filename=filename,
                file_size=file_size,
                total_rows=total_rows,
                status='pending'
            )
            
            db.add(job)
            db.commit()
            db.refresh(job)
            
            return str(job.id)
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating bulk upload job: {str(e)}")
            raise
        finally:
            db.close()
    
    async def process_annual_bulk_upload(
        self,
        job_id: str,
        data: List[Dict[str, Any]],
        user_id: str,
        organization_id: Optional[str]
    ) -> str:
        """
        Start async annual bulk upload processing using Celery
        
        Returns:
            Celery task ID
        """
        try:
            # Import here to avoid circular imports
            from app.workers.tasks import process_annual_bulk_upload_task
            
            # Start Celery task
            task = process_annual_bulk_upload_task.delay(
                job_id=job_id,
                data=data,
                user_id=user_id,
                organization_id=organization_id
            )
            
            # Update job with Celery task ID
            SessionLocal = get_session_local()
            db = SessionLocal()
            
            try:
                job = db.query(BulkUploadJob).filter(BulkUploadJob.id == job_id).first()
                if job:
                    job.celery_task_id = task.id
                    job.status = 'queued'
                    db.commit()
            except Exception as e:
                logger.error(f"Error updating job with task ID: {str(e)}")
            finally:
                db.close()
            
            return task.id
            
        except Exception as e:
            logger.error(f"Error starting annual bulk upload task: {str(e)}")
            raise
    
    async def process_quarterly_bulk_upload(
        self,
        job_id: str,
        data: List[Dict[str, Any]],
        user_id: str,
        organization_id: Optional[str]
    ) -> str:
        """
        Start async quarterly bulk upload processing using Celery
        
        Returns:
            Celery task ID
        """
        try:
            # Import here to avoid circular imports
            from app.workers.tasks import process_quarterly_bulk_upload_task
            
            # Start Celery task
            task = process_quarterly_bulk_upload_task.delay(
                job_id=job_id,
                data=data,
                user_id=user_id,
                organization_id=organization_id
            )
            
            # Update job with Celery task ID
            SessionLocal = get_session_local()
            db = SessionLocal()
            
            try:
                job = db.query(BulkUploadJob).filter(BulkUploadJob.id == job_id).first()
                if job:
                    job.celery_task_id = task.id
                    job.status = 'queued'
                    db.commit()
            except Exception as e:
                logger.error(f"Error updating job with task ID: {str(e)}")
            finally:
                db.close()
            
            return task.id
            
        except Exception as e:
            logger.error(f"Error starting quarterly bulk upload task: {str(e)}")
            raise
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status and details with Celery task status"""
        SessionLocal = get_session_local()
        db = SessionLocal()
        
        try:
            job = db.query(BulkUploadJob).filter(BulkUploadJob.id == job_id).first()
            if not job:
                return None
            
            # Get Celery task status if available
            celery_status = None
            celery_meta = None
            
            if job.celery_task_id:
                try:
                    from app.workers.celery_app import celery_app
                    result = celery_app.AsyncResult(job.celery_task_id)
                    celery_status = result.status
                    celery_meta = result.info if result.info else {}
                except Exception as e:
                    logger.warning(f"Could not get Celery task status: {str(e)}")
            
            # Calculate safe progress percentage
            progress_percentage = 0
            if job.total_rows and job.total_rows > 0 and job.processed_rows is not None:
                try:
                    progress = (job.processed_rows / job.total_rows) * 100
                    import math
                    progress_percentage = round(progress, 2) if not (math.isnan(progress) or math.isinf(progress)) else 0
                except (ZeroDivisionError, TypeError):
                    progress_percentage = 0
            
            response = {
                'id': str(job.id),
                'status': job.status,
                'job_type': job.job_type,
                'original_filename': job.original_filename,
                'total_rows': job.total_rows or 0,
                'processed_rows': job.processed_rows or 0,
                'successful_rows': job.successful_rows or 0,
                'failed_rows': job.failed_rows or 0,
                'error_message': job.error_message,
                'error_details': json.loads(job.error_details) if job.error_details else None,
                'created_at': job.created_at.isoformat() if job.created_at else None,
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'progress_percentage': progress_percentage,
                'celery_task_id': job.celery_task_id,
                'celery_status': celery_status,
                'celery_meta': celery_meta
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Error getting job status: {str(e)}")
            return None
        finally:
            db.close()


# Global service instance
celery_bulk_upload_service = CeleryBulkUploadService()
