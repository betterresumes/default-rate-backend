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
    ) -> Dict[str, Any]:  # Enhanced return type
        """
        Start async annual bulk upload processing using Celery with smart queue routing
        
        Returns:
            Dictionary with task info and auto-scaling details
        """
        try:
            from app.workers.tasks import process_annual_bulk_upload_task
            from app.services.auto_scaling_service import auto_scaling_service
            
            # SMART QUEUE ROUTING based on file size
            total_rows = len(data)
            queue_priority = self._get_task_queue(total_rows)
            
            # Get current system capacity for user feedback
            scaling_status = await auto_scaling_service.get_scaling_status()
            current_workers = scaling_status.get('scaling_recommendation', {}).get('current_workers', 4)
            queue_metrics = scaling_status.get('queue_metrics', {})
            
            # Apply task with smart routing
            task = process_annual_bulk_upload_task.apply_async(
                args=[job_id, data, user_id, organization_id],
                queue=queue_priority,
                routing_key=queue_priority
            )
            
            SessionLocal = get_session_local()
            db = SessionLocal()
            
            try:
                job = db.query(BulkUploadJob).filter(BulkUploadJob.id == job_id).first()
                if job:
                    if hasattr(job, 'celery_task_id'):
                        job.celery_task_id = task.id
                    job.status = 'queued'
                    db.commit()
            except Exception as e:
                logger.error(f"Error updating job with task ID: {str(e)}")
            finally:
                db.close()
            
            # Calculate queue position and estimated completion
            queue_position = queue_metrics.get(queue_priority, {}).get('pending_tasks', 0) + 1
            estimated_minutes = self._calculate_estimated_time(total_rows, queue_priority, current_workers)
            
            return {
                'task_id': task.id,
                'queue_priority': queue_priority,
                'queue_position': queue_position,
                'current_worker_capacity': current_workers * 8,  # 8 workers per instance
                'estimated_time_minutes': estimated_minutes,
                'processing_message': self._get_processing_message(total_rows, queue_priority),
                'system_load': self._get_system_load_status(queue_metrics)
            }
            
        except Exception as e:
            logger.error(f"Error starting annual bulk upload task: {str(e)}")
            raise
            raise
    
    async def process_quarterly_bulk_upload(
        self,
        job_id: str,
        data: List[Dict[str, Any]],
        user_id: str,
        organization_id: Optional[str]
    ) -> Dict[str, Any]:  # Enhanced return type
        """
        Start async quarterly bulk upload processing using Celery with smart queue routing
        
        Returns:
            Dictionary with task info and auto-scaling details
        """
        try:
            from app.workers.tasks import process_quarterly_bulk_upload_task
            from app.services.auto_scaling_service import auto_scaling_service
            
            # SMART QUEUE ROUTING based on file size
            total_rows = len(data)
            queue_priority = self._get_task_queue(total_rows)
            
            # Get current system capacity for user feedback
            scaling_status = await auto_scaling_service.get_scaling_status()
            current_workers = scaling_status.get('scaling_recommendation', {}).get('current_workers', 4)
            queue_metrics = scaling_status.get('queue_metrics', {})
            
            # Apply task with smart routing
            task = process_quarterly_bulk_upload_task.apply_async(
                args=[job_id, data, user_id, organization_id],
                queue=queue_priority,
                routing_key=queue_priority
            )
            
            SessionLocal = get_session_local()
            db = SessionLocal()
            
            try:
                job = db.query(BulkUploadJob).filter(BulkUploadJob.id == job_id).first()
                if job:
                    if hasattr(job, 'celery_task_id'):
                        job.celery_task_id = task.id
                    job.status = 'queued'
                    db.commit()
            except Exception as e:
                logger.error(f"Error updating job with task ID: {str(e)}")
            finally:
                db.close()
            
            # Calculate queue position and estimated completion
            queue_position = queue_metrics.get(queue_priority, {}).get('pending_tasks', 0) + 1
            estimated_minutes = self._calculate_estimated_time(total_rows, queue_priority, current_workers)
            
            return {
                'task_id': task.id,
                'queue_priority': queue_priority,
                'queue_position': queue_position,
                'current_worker_capacity': current_workers * 8,  # 8 workers per instance
                'estimated_time_minutes': estimated_minutes,
                'processing_message': self._get_processing_message(total_rows, queue_priority),
                'system_load': self._get_system_load_status(queue_metrics)
            }
            
        except Exception as e:
            logger.error(f"Error starting quarterly bulk upload task: {str(e)}")
            raise
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status and details with Celery task status and auto-scaling info"""
        SessionLocal = get_session_local()
        db = SessionLocal()
        
        try:
            job = db.query(BulkUploadJob).filter(BulkUploadJob.id == job_id).first()
            if not job:
                return None
            
            # Get basic job info
            job_data = {
                'id': str(job.id),
                'status': job.status,
                'job_type': job.job_type,
                'original_filename': job.original_filename,
                'total_rows': job.total_rows or 0,
                'processed_rows': job.processed_rows or 0,
                'successful_rows': job.successful_rows or 0,
                'failed_rows': job.failed_rows or 0,
                'error_message': job.error_message,
                'created_at': job.created_at.isoformat() if job.created_at else None,
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            }
            
            # Calculate progress percentage
            if job.total_rows and job.total_rows > 0:
                progress = (job.processed_rows or 0) / job.total_rows * 100
                job_data['progress_percentage'] = round(progress, 2)
            else:
                job_data['progress_percentage'] = 0
            
            # ADD AUTO-SCALING INFORMATION
            try:
                from app.services.auto_scaling_service import auto_scaling_service
                
                scaling_status = await auto_scaling_service.get_scaling_status()
                queue_metrics = scaling_status.get('queue_metrics', {})
                current_workers = scaling_status.get('scaling_recommendation', {}).get('current_workers', 4)
                
                # Determine queue priority based on file size
                queue_priority = self._get_task_queue(job.total_rows or 0)
                
                # Get current queue position (if still pending/processing)
                queue_position = 0
                if job.status in ['pending', 'queued', 'processing']:
                    queue_position = queue_metrics.get(queue_priority, {}).get('pending_tasks', 0)
                
                # Calculate estimated completion time
                estimated_completion = None
                if job.status == 'processing' and job.total_rows and job.processed_rows is not None:
                    remaining_rows = job.total_rows - job.processed_rows
                    if remaining_rows > 0:
                        estimated_minutes = self._calculate_estimated_time(remaining_rows, queue_priority, current_workers)
                        from datetime import datetime, timedelta
                        estimated_completion = (datetime.now() + timedelta(minutes=estimated_minutes)).isoformat()
                
                # Add auto-scaling fields
                job_data.update({
                    'queue_priority': queue_priority,
                    'queue_position': queue_position,
                    'estimated_completion': estimated_completion,
                    'current_worker_capacity': current_workers * 8,
                    'system_load': self._get_system_load_status(queue_metrics),
                    'processing_rate': f"{queue_metrics.get(queue_priority, {}).get('processing_rate', 4.0)} tasks/min"
                })
                
            except Exception as e:
                logger.warning(f"Could not add auto-scaling info to job status: {e}")
                # Add default values if auto-scaling service unavailable
                job_data.update({
                    'queue_priority': 'medium_priority',
                    'queue_position': 0,
                    'estimated_completion': None,
                    'current_worker_capacity': 32,
                    'system_load': 'unknown',
                    'processing_rate': '4.0 tasks/min'
                })
            
            return job_data
            
        except Exception as e:
            logger.error(f"Error getting job status: {str(e)}")
            return None
        finally:
            db.close()
    
    async def get_enhanced_job_status(self, job_id: str) -> Optional[Dict]:
        """Get enhanced job status with Celery task information"""
        SessionLocal = get_session_local()
        db = SessionLocal()
        
        try:
            job = db.query(BulkUploadJob).filter(BulkUploadJob.id == job_id).first()
            if not job:
                return None
            
            celery_status = None
            celery_meta = None
            celery_task_id = getattr(job, 'celery_task_id', None)
            
            if celery_task_id:
                try:
                    from app.workers.celery_app import celery_app
                    result = celery_app.AsyncResult(celery_task_id)
                    celery_status = result.status
                    celery_meta = result.info if result.info else {}
                except Exception as e:
                    logger.warning(f"Could not get Celery task status: {str(e)}")
            
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
                'celery_task_id': celery_task_id,
                'celery_status': celery_status,
                'celery_meta': celery_meta
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Error getting enhanced job status: {str(e)}")
            return None
        finally:
            db.close()
    
    # AUTO-SCALING HELPER METHODS
    def _get_task_queue(self, total_rows: int) -> str:
        """Determine optimal queue based on file size"""
        if total_rows < 2000:
            return "high_priority"    # Small files - process immediately
        elif total_rows < 8000:
            return "medium_priority"  # Normal files - standard processing
        else:
            return "low_priority"     # Large files - background processing
    
    def _calculate_estimated_time(self, total_rows: int, queue_priority: str, current_workers: int) -> int:
        """Calculate estimated processing time based on queue and system load"""
        base_processing_rates = {
            "high_priority": 100,    # rows per minute
            "medium_priority": 60,   # rows per minute  
            "low_priority": 40       # rows per minute
        }
        
        rate_per_minute = base_processing_rates.get(queue_priority, 60)
        total_capacity = current_workers * 8 * rate_per_minute  # workers per instance * rate
        
        # Base time calculation
        estimated_minutes = max(1, total_rows / total_capacity * 60)
        
        # Add queue wait time buffer
        queue_buffers = {
            "high_priority": 1.2,    # 20% buffer
            "medium_priority": 1.5,  # 50% buffer
            "low_priority": 2.0      # 100% buffer
        }
        
        buffer = queue_buffers.get(queue_priority, 1.5)
        return int(estimated_minutes * buffer)
    
    def _get_processing_message(self, total_rows: int, queue_priority: str) -> str:
        """Get user-friendly processing message"""
        messages = {
            "high_priority": f"Fast processing - Results in 2-5 minutes ({total_rows:,} rows)",
            "medium_priority": f"Standard processing - Results in 10-20 minutes ({total_rows:,} rows)",
            "low_priority": f"Large file processing - Results in 20-40 minutes ({total_rows:,} rows)"
        }
        return messages.get(queue_priority, f"Processing {total_rows:,} rows")
    
    def _get_system_load_status(self, queue_metrics: dict) -> str:
        """Determine current system load status"""
        total_pending = sum(
            metrics.get('pending_tasks', 0) 
            for metrics in queue_metrics.values()
        )
        
        if total_pending < 10:
            return "low"
        elif total_pending < 50:
            return "medium"  
        else:
            return "high"


celery_bulk_upload_service = CeleryBulkUploadService()
