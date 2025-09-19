#!/usr/bin/env python3
"""
Ultra-Fast Bulk Annual Predictions Script
Target: Process 10,000+ records in under 30 minutes
"""

import os
import sys
import pickle
import pandas as pd
import numpy as np
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
import logging
import multiprocessing
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

# Load environment variables
load_dotenv()

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

# Import after path setup
from src.database import get_db, Company, User, AnnualPrediction, SessionLocal
from src.services import CompanyService
from src.ml_service import MLModelService

# Create logs directory
logs_dir = os.path.join(backend_dir, 'logs')
os.makedirs(logs_dir, exist_ok=True)

# Configure ultra-fast logging
def setup_ultra_fast_logging():
    """Setup optimized logging for maximum performance"""
    
    # Main logger - only essential info
    main_logger = logging.getLogger('main')
    main_logger.setLevel(logging.INFO)
    
    # Performance logger 
    perf_logger = logging.getLogger('performance')
    perf_logger.setLevel(logging.INFO)
    
    # Error logger - only errors
    error_logger = logging.getLogger('errors')
    error_logger.setLevel(logging.ERROR)
    
    # Success logger - track successful operations
    success_logger = logging.getLogger('success')
    success_logger.setLevel(logging.INFO)
    
    # Create formatters - simple for performance
    simple_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Log files in logs folder
    main_handler = logging.FileHandler(os.path.join(logs_dir, 'log1_main.log'))
    main_handler.setFormatter(simple_formatter)
    main_logger.addHandler(main_handler)
    
    perf_handler = logging.FileHandler(os.path.join(logs_dir, 'log2_performance.log'))
    perf_handler.setFormatter(simple_formatter)
    perf_logger.addHandler(perf_handler)
    
    error_handler = logging.FileHandler(os.path.join(logs_dir, 'log3_errors.log'))
    error_handler.setFormatter(simple_formatter)
    error_logger.addHandler(error_handler)
    
    success_handler = logging.FileHandler(os.path.join(logs_dir, 'log4_success.log'))
    success_handler.setFormatter(simple_formatter)
    success_logger.addHandler(success_handler)
    
    # Console for main only
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(simple_formatter)
    main_logger.addHandler(console_handler)
    
    return main_logger, perf_logger, error_logger, success_logger

main_logger, perf_logger, error_logger, success_logger = setup_ultra_fast_logging()

class UltraFastBulkProcessor:
    def __init__(self, chunk_size: int = 2000, batch_size: int = 500):
        """Ultra-fast bulk processor - optimized for 30 min target"""
        self.chunk_size = chunk_size
        self.batch_size = batch_size
        self.ml_service = None
        self.stats = {
            'total_processed': 0,
            'successful_predictions': 0,
            'failed_predictions': 0,
            'skipped_records': 0,
            'start_time': None,
            'end_time': None
        }
        # Pre-cache companies
        self.company_cache = {}
        # Bulk operations
        self.prediction_objects = []
        
    def initialize_ml_service(self) -> bool:
        """Initialize ML service once"""
        try:
            self.ml_service = MLModelService()
            main_logger.info("✅ ML service initialized")
            return True
        except Exception as e:
            error_logger.error(f"❌ ML service failed: {e}")
            return False
    
    def load_and_preprocess_data(self) -> pd.DataFrame:
        """Load and preprocess data for maximum speed"""
        try:
            start_time = time.time()
            
            # Load data
            annual_step_path = os.path.join('src', 'models', 'annual_step.pkl')
            with open(annual_step_path, 'rb') as f:
                data = pickle.load(f)
            
            load_time = time.time() - start_time
            main_logger.info(f"📁 Loaded {len(data):,} records in {load_time:.2f}s")
            
            # Ultra-fast preprocessing
            start_preprocess = time.time()
            
            # Remove obviously invalid records
            original_size = len(data)
            data = data[
                data['ticker'].notna() & 
                (data['ticker'] != '') & 
                (data['ticker'] != 'nan') &
                data['fy'].notna()
            ].copy()
            
            # Convert types for speed
            data['ticker'] = data['ticker'].astype(str).str.upper()
            data['fy'] = pd.to_numeric(data['fy'], errors='coerce')
            
            preprocess_time = time.time() - start_preprocess
            filtered_size = len(data)
            
            main_logger.info(f"🔍 Preprocessed in {preprocess_time:.2f}s: {original_size:,} → {filtered_size:,} records")
            perf_logger.info(f"Data loading: {load_time:.2f}s, Preprocessing: {preprocess_time:.2f}s")
            
            return data
            
        except Exception as e:
            error_logger.error(f"❌ Data loading failed: {e}")
            raise
    
    def extract_financial_ratios_fast(self, row: pd.Series) -> Dict[str, float]:
        """Ultra-fast financial ratio extraction"""
        try:
            ratios = {
                'long_term_debt_to_total_capital': self.safe_float(row.get('long-term debt / total capital (%)')),
                'total_debt_to_ebitda': self.safe_float(row.get('total debt / ebitda')),
                'net_income_margin': self.safe_float(row.get('net income margin')),
                'ebit_to_interest_expense': self.safe_float(row.get('ebit / interest expense')),
                'return_on_assets': self.safe_float(row.get('return on assets'))
            }
            return ratios
        except Exception:
            return {k: None for k in ['long_term_debt_to_total_capital', 'total_debt_to_ebitda', 
                                    'net_income_margin', 'ebit_to_interest_expense', 'return_on_assets']}
    
    def safe_float(self, value) -> Optional[float]:
        """Ultra-fast float conversion"""
        if value is None or pd.isna(value):
            return None
        if isinstance(value, str) and value.strip().upper() in ['NM', 'N/A', 'NA', '', '-']:
            return None
        try:
            float_val = float(value)
            return None if (np.isnan(float_val) or np.isinf(float_val)) else float_val
        except:
            return None
    
    def validate_ratios_fast(self, ratios: Dict[str, float]) -> bool:
        """Ultra-fast validation - need at least 2 valid ratios"""
        valid_count = sum(1 for v in ratios.values() if v is not None)
        return valid_count >= 2
    
    def get_or_create_company_cached(self, ticker: str, company_name: str, company_service: CompanyService) -> Optional[Company]:
        """Cached company creation - avoid repeated DB calls"""
        if ticker in self.company_cache:
            return self.company_cache[ticker]
        
        try:
            company = company_service.create_or_get_company(
                symbol=ticker,
                name=company_name or ticker,
                market_cap=100000.0,  # Fixed value
                sector="Technology"   # Fixed value for speed
            )
            
            if company:
                self.company_cache[ticker] = company
            
            return company
            
        except Exception as e:
            error_logger.error(f"Company creation failed for {ticker}: {e}")
            return None
    
    def create_prediction_object(self, company: Company, ratios: Dict[str, float], 
                               prediction_result: Dict, fiscal_year: float, user_id: str) -> AnnualPrediction:
        """Create prediction object for bulk insert"""
        
        reporting_year = str(int(fiscal_year)) if not pd.isna(fiscal_year) else "2024"
        
        # Extract prediction values with correct field names
        probability = prediction_result.get('probability', 0.0)
        risk_level = prediction_result.get('risk_level', 'MEDIUM')
        confidence = prediction_result.get('confidence', 0.5)
        
        return AnnualPrediction(
            company_id=company.id,
            reporting_year=reporting_year,
            reporting_quarter="Q4",
            long_term_debt_to_total_capital=ratios.get('long_term_debt_to_total_capital'),
            total_debt_to_ebitda=ratios.get('total_debt_to_ebitda'),
            net_income_margin=ratios.get('net_income_margin'),
            ebit_to_interest_expense=ratios.get('ebit_to_interest_expense'),
            return_on_assets=ratios.get('return_on_assets'),
            probability=probability,  # Correct field name
            risk_level=risk_level,
            confidence=confidence
        )
    
    def bulk_insert_predictions(self, db) -> Tuple[int, int]:
        """Ultra-fast bulk database insert"""
        if not self.prediction_objects:
            return 0, 0
        
        try:
            start_time = time.time()
            
            # Bulk insert all at once
            db.bulk_save_objects(self.prediction_objects)
            db.commit()
            
            insert_time = time.time() - start_time
            successful = len(self.prediction_objects)
            
            perf_logger.info(f"Bulk insert: {successful} records in {insert_time:.2f}s ({successful/insert_time:.1f} records/s)")
            success_logger.info(f"✅ Inserted {successful} predictions successfully")
            
            # Clear objects
            self.prediction_objects = []
            
            return successful, 0
            
        except Exception as e:
            error_logger.error(f"❌ Bulk insert failed: {e}")
            self.prediction_objects = []
            return 0, len(self.prediction_objects)
    
    def process_chunk_ultra_fast(self, chunk: pd.DataFrame, chunk_num: int, db, user_id: str) -> Dict:
        """Ultra-fast chunk processing"""
        start_time = time.time()
        
        chunk_stats = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0
        }
        
        try:
            company_service = CompanyService(db)
            
            # Process all records in chunk
            valid_records = []
            
            # First pass: validate and collect valid records
            for _, row in chunk.iterrows():
                chunk_stats['processed'] += 1
                
                try:
                    ticker = str(row['ticker']).strip().upper()
                    fiscal_year = row.get('fy')
                    
                    if not ticker or pd.isna(fiscal_year):
                        chunk_stats['skipped'] += 1
                        continue
                    
                    # Extract ratios
                    ratios = self.extract_financial_ratios_fast(row)
                    
                    # Validate
                    if not self.validate_ratios_fast(ratios):
                        chunk_stats['skipped'] += 1
                        continue
                    
                    # Get company
                    company_name = str(row.get('company name', ticker))
                    company = self.get_or_create_company_cached(ticker, company_name, company_service)
                    
                    if not company:
                        chunk_stats['failed'] += 1
                        continue
                    
                    valid_records.append((ticker, company, ratios, fiscal_year))
                    
                except Exception as e:
                    chunk_stats['failed'] += 1
                    continue
            
            # Second pass: batch ML predictions
            if valid_records:
                for ticker, company, ratios, fiscal_year in valid_records:
                    try:
                        # Run ML prediction
                        prediction_result = self.ml_service.predict_default_probability(ratios)
                        
                        if 'error' in prediction_result:
                            chunk_stats['failed'] += 1
                            continue
                        
                        # Create prediction object
                        prediction_obj = self.create_prediction_object(
                            company, ratios, prediction_result, fiscal_year, user_id
                        )
                        
                        self.prediction_objects.append(prediction_obj)
                        chunk_stats['successful'] += 1
                        
                        # Bulk insert when batch is full
                        if len(self.prediction_objects) >= self.batch_size:
                            batch_successful, batch_failed = self.bulk_insert_predictions(db)
                            # Note: we're accumulating in chunk_stats but bulk insert handles multiple chunks
                        
                    except Exception as e:
                        error_logger.error(f"Prediction failed for {ticker}: {e}")
                        chunk_stats['failed'] += 1
                        continue
            
            chunk_time = time.time() - start_time
            perf_logger.info(f"Chunk {chunk_num}: {chunk_stats['successful']}/{chunk_stats['processed']} in {chunk_time:.1f}s")
            
        except Exception as e:
            error_logger.error(f"❌ Chunk {chunk_num} failed: {e}")
            
        return chunk_stats
    
    def run_ultra_fast_bulk(self) -> bool:
        """Main ultra-fast processing method"""
        try:
            self.stats['start_time'] = datetime.now()
            main_logger.info(f"🚀 ULTRA-FAST MODE: Starting at {self.stats['start_time']}")
            
            # Initialize ML service
            if not self.initialize_ml_service():
                return False
            
            # Load and preprocess data
            data = self.load_and_preprocess_data()
            
            # Get database session
            db = SessionLocal()
            
            try:
                # Get or create user
                user = self.get_or_create_user(db)
                
                # Process in large chunks for speed
                total_chunks = (len(data) + self.chunk_size - 1) // self.chunk_size
                main_logger.info(f"📊 Processing {len(data):,} records in {total_chunks} chunks of {self.chunk_size}")
                main_logger.info(f"⚡ Target: Complete in under 30 minutes")
                
                chunk_times = []
                
                for chunk_num in range(total_chunks):
                    chunk_start = time.time()
                    
                    start_idx = chunk_num * self.chunk_size
                    end_idx = min(start_idx + self.chunk_size, len(data))
                    chunk = data.iloc[start_idx:end_idx]
                    
                    chunk_stats = self.process_chunk_ultra_fast(chunk, chunk_num + 1, db, str(user.id))
                    
                    chunk_time = time.time() - chunk_start
                    chunk_times.append(chunk_time)
                    
                    # Update stats
                    self.stats['total_processed'] += chunk_stats['processed']
                    self.stats['successful_predictions'] += chunk_stats['successful']
                    self.stats['failed_predictions'] += chunk_stats['failed']
                    self.stats['skipped_records'] += chunk_stats['skipped']
                    
                    # Progress tracking
                    progress = ((chunk_num + 1) / total_chunks) * 100
                    if chunk_times:
                        avg_time = sum(chunk_times) / len(chunk_times)
                        est_remaining = avg_time * (total_chunks - chunk_num - 1)
                        est_remaining_min = est_remaining / 60
                        
                        main_logger.info(f"📈 Progress: {progress:.1f}% | Chunk: {chunk_time:.1f}s | Est: {est_remaining_min:.1f}m")
                
                # Final bulk insert
                if self.prediction_objects:
                    final_successful, final_failed = self.bulk_insert_predictions(db)
                    self.stats['successful_predictions'] += final_successful
                    self.stats['failed_predictions'] += final_failed
                
                self.stats['end_time'] = datetime.now()
                self.log_final_stats()
                
                return True
                
            finally:
                db.close()
                
        except Exception as e:
            error_logger.error(f"❌ Critical error: {e}")
            self.stats['end_time'] = datetime.now()
            return False
    
    def get_or_create_user(self, db) -> User:
        """Get or create system user"""
        test_email = "ultra_bulk@predictions.com"
        user = db.query(User).filter(User.email == test_email).first()
        
        if not user:
            user = User(
                email=test_email,
                username="ultra_bulk_processor",
                hashed_password="dummy_hash",
                full_name="Ultra Fast Bulk Processor",
                is_active=True,
                is_verified=True,
                role="system"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        return user
    
    def log_final_stats(self):
        """Log final performance statistics"""
        duration = self.stats['end_time'] - self.stats['start_time']
        duration_minutes = duration.total_seconds() / 60
        
        main_logger.info("=" * 80)
        main_logger.info("🏁 ULTRA-FAST BULK PROCESSING COMPLETED")
        main_logger.info("=" * 80)
        main_logger.info(f"⏱️  Total Time: {duration_minutes:.2f} minutes")
        main_logger.info(f"📊 Total Processed: {self.stats['total_processed']:,}")
        main_logger.info(f"✅ Successful: {self.stats['successful_predictions']:,}")
        main_logger.info(f"❌ Failed: {self.stats['failed_predictions']:,}")
        main_logger.info(f"⏭️  Skipped: {self.stats['skipped_records']:,}")
        
        if self.stats['total_processed'] > 0:
            success_rate = (self.stats['successful_predictions'] / self.stats['total_processed']) * 100
            processing_rate = self.stats['total_processed'] / duration.total_seconds()
            
            main_logger.info(f"📈 Success Rate: {success_rate:.2f}%")
            main_logger.info(f"⚡ Processing Rate: {processing_rate:.2f} records/second")
            
            # Check if we met the 30-minute target
            if duration_minutes <= 30:
                main_logger.info("🎯 ✅ TARGET ACHIEVED: Completed in under 30 minutes!")
            else:
                main_logger.info(f"⚠️  Target missed: Took {duration_minutes:.1f} minutes (target: 30)")
        
        main_logger.info("=" * 80)


def main():
    """Ultra-fast main function"""
    # Ultra-aggressive settings for 30-minute target
    cpu_count = multiprocessing.cpu_count()
    
    # Large chunks and batches for maximum speed
    ultra_chunk_size = min(5000, max(2000, cpu_count * 1000))  # Very large chunks
    ultra_batch_size = min(1000, max(500, cpu_count * 100))    # Very large batches
    
    main_logger.info(f"🖥️  System: {cpu_count} CPU cores")
    main_logger.info(f"⚡ Ultra chunk size: {ultra_chunk_size}")
    main_logger.info(f"⚡ Ultra batch size: {ultra_batch_size}")
    main_logger.info(f"🎯 Target: Complete in under 30 minutes")
    
    processor = UltraFastBulkProcessor(
        chunk_size=ultra_chunk_size,
        batch_size=ultra_batch_size
    )
    
    success = processor.run_ultra_fast_bulk()
    
    if success:
        main_logger.info("🎉 Ultra-fast bulk processing completed successfully!")
        sys.exit(0)
    else:
        main_logger.error("💥 Ultra-fast bulk processing failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
