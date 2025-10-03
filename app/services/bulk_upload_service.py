#!/usr/bin/env python3

import asyncio
import pandas as pd
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_session_local, BulkUploadJob, Company, AnnualPrediction, QuarterlyPrediction, User
from app.services.ml_service import MLModelService
from app.services.quarterly_ml_service import QuarterlyMLModelService
import uuid
import logging

logger = logging.getLogger(__name__)

class BulkUploadService:
    def __init__(self):
        self.ml_service = MLModelService()
        self.quarterly_ml_service = QuarterlyMLModelService()
    
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
    
    async def update_job_status(
        self,
        job_id: str,
        status: str,
        processed_rows: Optional[int] = None,
        successful_rows: Optional[int] = None,
        failed_rows: Optional[int] = None,
        error_message: Optional[str] = None,
        error_details: Optional[Dict] = None
    ):
        """Update job status and progress"""
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
    
    def create_or_get_company(self, db: Session, symbol: str, name: str, market_cap: float, sector: str, organization_id: Optional[str]) -> Company:
        """Create or get company with organization scoping"""
        if organization_id:
            company = db.query(Company).filter(
                Company.symbol == symbol,
                Company.organization_id == organization_id
            ).first()
        else:
            company = db.query(Company).filter(
                Company.symbol == symbol,
                Company.organization_id.is_(None)
            ).first()
        
        if not company:
            company = Company(
                symbol=symbol,
                name=name,
                market_cap=self.safe_float(market_cap),  # Raw dollar values
                sector=sector,
                organization_id=organization_id
            )
            db.add(company)
            db.flush()  
        else:
            company.name = name
            company.market_cap = self.safe_float(market_cap)  # Raw dollar values
            company.sector = sector
        
        return company
    
    async def process_annual_bulk_upload(
        self,
        job_id: str,
        data: List[Dict[str, Any]],
        user_id: str,
        organization_id: Optional[str]
    ):
        """Process annual predictions bulk upload"""
        await self.update_job_status(job_id, 'processing')
        
        SessionLocal = get_session_local()
        db = SessionLocal()
        
        successful_rows = 0
        failed_rows = 0
        error_details = []
        
        try:
            for i, row in enumerate(data):
                try:
                    company = self.create_or_get_company(
                        db=db,
                        symbol=row['company_symbol'],
                        name=row['company_name'],
                        market_cap=self.safe_float(row['market_cap']),
                        sector=row['sector'],
                        organization_id=organization_id
                    )
                    
                    financial_data = {
                        'long_term_debt_to_total_capital': self.safe_float(row['long_term_debt_to_total_capital']),
                        'total_debt_to_ebitda': self.safe_float(row['total_debt_to_ebitda']),
                        'net_income_margin': self.safe_float(row['net_income_margin']),
                        'ebit_to_interest_expense': self.safe_float(row['ebit_to_interest_expense']),
                        'return_on_assets': self.safe_float(row['return_on_assets'])
                    }
                    
                    ml_result = await self.ml_service.predict_annual(financial_data)
                    
                    prediction = AnnualPrediction(
                        company_id=company.id,
                        organization_id=organization_id,
                        reporting_year=int(row['reporting_year']),
                        reporting_quarter=int(row['reporting_quarter']) if row.get('reporting_quarter') else None,
                        long_term_debt_to_total_capital=self.safe_float(row['long_term_debt_to_total_capital']),
                        total_debt_to_ebitda=self.safe_float(row['total_debt_to_ebitda']),
                        net_income_margin=self.safe_float(row['net_income_margin']),
                        ebit_to_interest_expense=self.safe_float(row['ebit_to_interest_expense']),
                        return_on_assets=self.safe_float(row['return_on_assets']),
                        probability=self.safe_float(ml_result['probability']),
                        risk_level=ml_result['risk_level'],
                        confidence=self.safe_float(ml_result['confidence']),
                        predicted_at=datetime.utcnow(),
                        created_by=user_id
                    )
                    
                    db.add(prediction)
                    successful_rows += 1
                    
                    if (i + 1) % 50 == 0:
                        db.commit()
                        await self.update_job_status(
                            job_id, 
                            'processing',
                            processed_rows=i + 1,
                            successful_rows=successful_rows,
                            failed_rows=failed_rows
                        )
                
                except Exception as e:
                    failed_rows += 1
                    error_details.append({
                        'row': i + 1,
                        'data': row,
                        'error': str(e)
                    })
                    logger.error(f"Error processing row {i + 1}: {str(e)}")
                    db.rollback()
                    continue
            
            db.commit()
            
            await self.update_job_status(
                job_id,
                'completed',
                processed_rows=len(data),
                successful_rows=successful_rows,
                failed_rows=failed_rows,
                error_details={'errors': error_details[:100]}  
            )
            
        except Exception as e:
            db.rollback()
            await self.update_job_status(
                job_id,
                'failed',
                error_message=str(e),
                error_details={'errors': error_details}
            )
            logger.error(f"Bulk upload job {job_id} failed: {str(e)}")
        finally:
            db.close()
    
    async def process_quarterly_bulk_upload(
        self,
        job_id: str,
        data: List[Dict[str, Any]],
        user_id: str,
        organization_id: Optional[str]
    ):
        """Process quarterly predictions bulk upload"""
        await self.update_job_status(job_id, 'processing')
        
        SessionLocal = get_session_local()
        db = SessionLocal()
        
        successful_rows = 0
        failed_rows = 0
        error_details = []
        
        try:
            for i, row in enumerate(data):
                try:
                    company = self.create_or_get_company(
                        db=db,
                        symbol=row['company_symbol'],
                        name=row['company_name'],
                        market_cap=self.safe_float(row['market_cap']),
                        sector=row['sector'],
                        organization_id=organization_id
                    )
                    
                    financial_data = {
                        'total_debt_to_ebitda': self.safe_float(row['total_debt_to_ebitda']),
                        'sga_margin': self.safe_float(row['sga_margin']),
                        'long_term_debt_to_total_capital': self.safe_float(row['long_term_debt_to_total_capital']),
                        'return_on_capital': self.safe_float(row['return_on_capital'])
                    }
                    
                    ml_result = await self.quarterly_ml_service.predict_quarterly(financial_data)
                    
                    prediction = QuarterlyPrediction(
                        company_id=company.id,
                        organization_id=organization_id,
                        reporting_year=int(row['reporting_year']),
                        reporting_quarter=int(row['reporting_quarter']),
                        total_debt_to_ebitda=self.safe_float(row['total_debt_to_ebitda']),
                        sga_margin=self.safe_float(row['sga_margin']),
                        long_term_debt_to_total_capital=self.safe_float(row['long_term_debt_to_total_capital']),
                        return_on_capital=self.safe_float(row['return_on_capital']),
                        logistic_probability=self.safe_float(ml_result.get('logistic_probability', 0)),
                        gbm_probability=self.safe_float(ml_result.get('gbm_probability', 0)),
                        ensemble_probability=self.safe_float(ml_result.get('ensemble_probability', 0)),
                        risk_level=ml_result['risk_level'],
                        confidence=self.safe_float(ml_result['confidence']),
                        predicted_at=datetime.utcnow(),
                        created_by=user_id
                    )
                    
                    db.add(prediction)
                    successful_rows += 1
                    
                    if (i + 1) % 50 == 0:
                        db.commit()
                        await self.update_job_status(
                            job_id, 
                            'processing',
                            processed_rows=i + 1,
                            successful_rows=successful_rows,
                            failed_rows=failed_rows
                        )
                
                except Exception as e:
                    failed_rows += 1
                    error_details.append({
                        'row': i + 1,
                        'data': row,
                        'error': str(e)
                    })
                    logger.error(f"Error processing row {i + 1}: {str(e)}")
                    db.rollback()
                    continue
            
            db.commit()
            
            await self.update_job_status(
                job_id,
                'completed',
                processed_rows=len(data),
                successful_rows=successful_rows,
                failed_rows=failed_rows,
                error_details={'errors': error_details[:100]}
            )
            
        except Exception as e:
            db.rollback()
            await self.update_job_status(
                job_id,
                'failed',
                error_message=str(e),
                error_details={'errors': error_details}
            )
            logger.error(f"Bulk upload job {job_id} failed: {str(e)}")
        finally:
            db.close()
    
    def safe_float(self, value):
        """Convert value to float, handling None and NaN values"""
        if value is None:
            return 0
        try:
            import math
            float_val = float(value)
            if math.isnan(float_val) or math.isinf(float_val):
                return 0
            return float_val
        except (ValueError, TypeError):
            return 0
    
    def safe_progress_percentage(self, processed_rows, total_rows):
        """Calculate progress percentage safely"""
        if not total_rows or total_rows <= 0:
            return 0
        if processed_rows is None:
            return 0
        
        try:
            import math
            percentage = (processed_rows / total_rows) * 100
            if math.isnan(percentage) or math.isinf(percentage):
                return 0
            return round(percentage, 2)
        except (ValueError, TypeError, ZeroDivisionError):
            return 0

    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status and details"""
        SessionLocal = get_session_local()
        db = SessionLocal()
        
        try:
            job = db.query(BulkUploadJob).filter(BulkUploadJob.id == job_id).first()
            if not job:
                return None
            
            return {
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
                'progress_percentage': self.safe_progress_percentage(job.processed_rows, job.total_rows)
            }
            
        except Exception as e:
            logger.error(f"Error getting job status: {str(e)}")
            return None
        finally:
            db.close()

bulk_upload_service = BulkUploadService()
