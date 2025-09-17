#!/usr/bin/env python3
"""
Optimized Bulk Annual Predictions Script
Processes all records from annual_step.pkl data with improved performance and logging.
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
from concurrent.futures import ThreadPoolExecutor
import multiprocessing

# Load environment variables
load_dotenv()

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

# Import after path setup
from src.database import get_db, Company, User, AnnualPrediction, SessionLocal
from src.services import CompanyService
from src.ml_service import MLModelService

# Configure multiple loggers for different purposes
def setup_logging():
    """Setup multiple log files for detailed tracking"""
    # Main logger
    main_logger = logging.getLogger('bulk_predictions')
    main_logger.setLevel(logging.INFO)
    
    # Detailed process logger
    detail_logger = logging.getLogger('detailed_process')
    detail_logger.setLevel(logging.DEBUG)
    
    # Database operations logger
    db_logger = logging.getLogger('database_ops')
    db_logger.setLevel(logging.INFO)
    
    # ML predictions logger
    ml_logger = logging.getLogger('ml_predictions')
    ml_logger.setLevel(logging.INFO)
    
    # Create formatters
    detailed_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    simple_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Main log file
    main_handler = logging.FileHandler('log1_main_bulk_predictions.log')
    main_handler.setFormatter(simple_formatter)
    main_logger.addHandler(main_handler)
    
    # Detailed process log
    detail_handler = logging.FileHandler('log2_detailed_process.log')
    detail_handler.setFormatter(detailed_formatter)
    detail_logger.addHandler(detail_handler)
    
    # Database operations log
    db_handler = logging.FileHandler('log3_database_operations.log')
    db_handler.setFormatter(detailed_formatter)
    db_logger.addHandler(db_handler)
    
    # ML predictions log
    ml_handler = logging.FileHandler('log4_ml_predictions.log')
    ml_handler.setFormatter(detailed_formatter)
    ml_logger.addHandler(ml_handler)
    
    # Console handler for main logger
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(simple_formatter)
    main_logger.addHandler(console_handler)
    
    return main_logger, detail_logger, db_logger, ml_logger

logger, detail_logger, db_logger, ml_logger = setup_logging()

class BulkAnnualPredictionProcessor:
    def __init__(self, chunk_size: int = 1000, batch_size: int = 50):
        """Initialize the bulk prediction processor"""
        self.chunk_size = chunk_size
        self.batch_size = batch_size  # Process multiple predictions in a batch
        self.ml_service = None
        self.stats = {
            'total_processed': 0,
            'successful_predictions': 0,
            'failed_predictions': 0,
            'companies_created': 0,
            'companies_updated': 0,
            'skipped_invalid_data': 0,
            'duplicates_skipped': 0,
            'start_time': None,
            'end_time': None
        }
        # Cache for companies to avoid repeated database lookups
        self.company_cache = {}
        # Batch storage for bulk operations
        self.prediction_batch = []
        
    def initialize_ml_service(self) -> bool:
        """Initialize ML service"""
        try:
            logger.info("Initializing ML service...")
            self.ml_service = MLModelService()
            logger.info("✅ ML service initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize ML service: {e}")
            return False
    
    def load_annual_data(self) -> pd.DataFrame:
        """Load annual step data"""
        try:
            logger.info("Loading annual step data...")
            annual_step_path = os.path.join('src', 'models', 'annual_step.pkl')
            
            with open(annual_step_path, 'rb') as f:
                data = pickle.load(f)
            
            logger.info(f"✅ Loaded annual data: {data.shape[0]:,} records, {data.shape[1]} columns")
            logger.info(f"📊 Unique companies: {data['ticker'].nunique():,}")
            logger.info(f"📅 Year range: {data['fy'].min():.0f} - {data['fy'].max():.0f}")
            
            return data
            
        except Exception as e:
            logger.error(f"❌ Failed to load annual data: {e}")
            raise
    
    def get_or_create_user(self, db) -> User:
        """Get or create test user for predictions"""
        test_email = "bulk@predictions.com"
        user = db.query(User).filter(User.email == test_email).first()
        
        if not user:
            user = User(
                email=test_email,
                username="bulk_annual_processor",
                hashed_password="dummy_hash_for_bulk_processing",
                full_name="Bulk Annual Prediction Processor",
                is_active=True,
                is_verified=True,
                role="system"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"✅ Created system user: {user.email}")
        else:
            logger.info(f"📋 Using existing system user: {user.email}")
        
        return user
    
    def safe_float(self, value) -> float:
        """Safely convert value to float, handling various edge cases"""
        if value is None or pd.isna(value):
            return None
        
        # Handle string values like "NM" (Not Meaningful)
        if isinstance(value, str):
            value = value.strip().upper()
            if value in ['NM', 'N/A', 'NA', '', '-']:
                return None
        
        try:
            float_val = float(value)
            if np.isnan(float_val) or np.isinf(float_val):
                return None
            return float_val
        except (ValueError, TypeError):
            return None
    
    def extract_financial_ratios(self, row: pd.Series) -> Dict[str, float]:
        """Extract financial ratios required for ML prediction - optimized version"""
        # Direct dictionary access with fallback - faster than .get() calls
        try:
            return {
                'long_term_debt_to_total_capital': self.safe_float(row['long-term debt / total capital (%)']),
                'total_debt_to_ebitda': self.safe_float(row['total debt / ebitda']),
                'net_income_margin': self.safe_float(row['net income margin']),
                'ebit_to_interest_expense': self.safe_float(row['ebit / interest expense']),
                'return_on_assets': self.safe_float(row['return on assets'])
            }
        except KeyError as e:
            # Fallback to slower .get() method if direct access fails
            logger.warning(f"Missing column {e}, using fallback method")
            return {
                'long_term_debt_to_total_capital': self.safe_float(row.get('long-term debt / total capital (%)')),
                'total_debt_to_ebitda': self.safe_float(row.get('total debt / ebitda')),
                'net_income_margin': self.safe_float(row.get('net income margin')),
                'ebit_to_interest_expense': self.safe_float(row.get('ebit / interest expense')),
                'return_on_assets': self.safe_float(row.get('return on assets'))
            }
    
    def validate_financial_data(self, ratios: Dict[str, float]) -> Tuple[bool, int]:
        """Validate financial data - allow up to 3 null values as ML service can handle them now"""
        null_count = sum(1 for v in ratios.values() if v is None)
        
        # With improved ML service, we can handle more missing values
        # Only reject if ALL values are missing (need at least 1 valid ratio)
        if null_count >= 5:
            return False, null_count
        
        # Check if remaining values are realistic
        valid_ratios = {k: v for k, v in ratios.items() if v is not None}
        
        # Basic sanity checks for remaining values
        for key, value in valid_ratios.items():
            if abs(value) > 10000:  # Extremely high values might indicate data quality issues
                logger.warning(f"⚠️ Suspicious value for {key}: {value}")
        
        return True, null_count
    
    def prepare_ratios_for_ml(self, ratios: Dict[str, float]) -> Dict[str, float]:
        """Prepare ratios for ML service - now we can pass None/NaN directly"""
        # The ML service can now handle None/NaN values directly
        # No need to convert to 0.0 anymore
        prepared_ratios = {}
        for key, value in ratios.items():
            if value is None:
                prepared_ratios[key] = None  # Keep None as-is
            elif pd.isna(value) or np.isinf(value):
                prepared_ratios[key] = None  # Convert NaN/inf to None
            else:
                prepared_ratios[key] = float(value)
        return prepared_ratios
    
    def add_to_prediction_batch(self, company: Company, row: pd.Series, ratios: Dict[str, float], 
                               prediction_result: Dict, user_id: str) -> None:
        """Add prediction to batch for bulk insert"""
        # Get fiscal year
        fiscal_year = row.get('fy')
        if pd.isna(fiscal_year) or fiscal_year is None:
            fiscal_year = 2024
        
        # Create prediction data
        prediction_data = {
            'company': company,
            'financial_data': ratios,
            'prediction_results': prediction_result,
            'fiscal_year': fiscal_year,
            'user_id': user_id
        }
        
        self.prediction_batch.append(prediction_data)
    
    def flush_prediction_batch(self, company_service: CompanyService, db, dry_run: bool = False) -> Tuple[int, int]:
        """Flush the prediction batch to database - optimized bulk insert"""
        if not self.prediction_batch:
            return 0, 0
        
        successful = 0
        failed = 0
        
        try:
            if dry_run:
                # In dry run, just simulate
                for pred_data in self.prediction_batch:
                    company = pred_data['company']
                    prob = pred_data['prediction_results'].get('default_probability', 0.0)
                    logger.info(f"✅ [DRY RUN] Would create prediction for {company.symbol}: probability={prob:.3f}")
                    successful += 1
                
                self.prediction_batch = []
                return successful, failed
            
            # PRODUCTION MODE - Actually create predictions in database
            db_logger.info(f"🗄️ Creating {len(self.prediction_batch)} annual predictions in database...")
            
            for pred_data in self.prediction_batch:
                try:
                    company = pred_data['company']
                    ratios = pred_data['financial_data']
                    prediction_result = pred_data['prediction_results']
                    fiscal_year = pred_data.get('fiscal_year', 2024)
                    user_id = pred_data.get('user_id')
                    
                    # Log detailed input data
                    detail_logger.debug(f"📊 Creating prediction for {company.symbol} (ID: {company.id})")
                    detail_logger.debug(f"   Financial Ratios: {ratios}")
                    detail_logger.debug(f"   ML Results: {prediction_result}")
                    detail_logger.debug(f"   Fiscal Year: {fiscal_year}")
                    
                    # Create the annual prediction using the service
                    annual_prediction = company_service.create_annual_prediction(
                        company=company,
                        financial_data=ratios,
                        prediction_results=prediction_result,
                        reporting_year=str(int(fiscal_year)),
                        reporting_quarter="Q4"
                    )
                    
                    if annual_prediction:
                        successful += 1
                        db_logger.info(f"✅ Created prediction {annual_prediction.id} for {company.symbol} (FY{fiscal_year}): "
                                      f"probability={prediction_result.get('default_probability', 0.0):.3f}, "
                                      f"risk_score={prediction_result.get('risk_score', 'Unknown')}")
                        
                        # Log the complete created record
                        detail_logger.info(f"📋 CREATED: AnnualPrediction(id={annual_prediction.id}, "
                                          f"company_id={annual_prediction.company_id}, "
                                          f"reporting_year={annual_prediction.reporting_year}, "
                                          f"predicted_default_probability={annual_prediction.predicted_default_probability})")
                    else:
                        failed += 1
                        db_logger.error(f"❌ Failed to create prediction for {company.symbol}")
                        
                except Exception as e:
                    failed += 1
                    db_logger.error(f"❌ Database error creating prediction for {pred_data['company'].symbol}: {e}")
                    detail_logger.exception(f"Full error details:")
            
            # Clear the batch
            self.prediction_batch = []
            
            db_logger.info(f"🎯 Batch complete: {successful} successful, {failed} failed")
            
        except Exception as e:
            logger.error(f"❌ Batch flush failed: {e}")
            db_logger.error(f"❌ Critical batch flush error: {e}")
            failed = len(self.prediction_batch)
            self.prediction_batch = []
        
        return successful, failed
    
    def create_or_get_company(self, row: pd.Series, company_service: CompanyService) -> Optional[Company]:
        """Create or get company from data row - with caching for performance"""
        try:
            # Extract company info with direct access for speed
            ticker = str(row['ticker']).strip().upper() if 'ticker' in row else ''
            
            # Check cache first
            if ticker in self.company_cache:
                detail_logger.debug(f"🗂️ Found {ticker} in cache")
                return self.company_cache[ticker]
            
            company_name = str(row.get('company name', '')).strip()
            industry = str(row.get('Industry', '')).strip()
            
            # Log input data
            detail_logger.debug(f"🏢 Processing company: ticker={ticker}, name={company_name}, industry={industry}")
            
            # Validation
            if not ticker or ticker in ['NAN', '']:
                logger.warning(f"⚠️ Invalid ticker: {ticker}")
                return None
            
            if not company_name or company_name in ['NAN', '']:
                company_name = ticker  # Use ticker as fallback
                detail_logger.debug(f"📝 Using ticker as company name: {company_name}")
            
            # Handle sector
            sector = industry if industry and industry.lower() not in ['', 'nan', 'none', 'null'] else "Other"
            
            # Fixed market cap as requested
            market_cap = 100.00  # $100 million (in thousands)
            
            # Create or update company
            company = company_service.create_or_get_company(
                symbol=ticker,
                name=company_name,
                market_cap=market_cap,
                sector=sector
            )
            
            if company:
                # Cache the company for future use
                self.company_cache[ticker] = company
                db_logger.info(f"🏢 Company ready: {company.symbol} (ID: {company.id}) - {company.name}")
                detail_logger.debug(f"📋 Company details: {company.__dict__}")
            else:
                db_logger.error(f"❌ Failed to create/get company for ticker: {ticker}")
            
            return company
            
        except Exception as e:
            logger.error(f"❌ Error creating company from row: {e}")
            detail_logger.exception(f"Company creation error details:")
            return None
    
    def create_annual_prediction(self, company: Company, row: pd.Series, ratios: Dict[str, float], 
                               company_service: CompanyService) -> Optional[AnnualPrediction]:
        """Create annual prediction for company"""
        try:
            # Ensure ML service is initialized
            if self.ml_service is None:
                if not self.initialize_ml_service():
                    logger.error("❌ Failed to initialize ML service")
                    return None
            
            # Get fiscal year
            fiscal_year = row.get('fy')
            if pd.isna(fiscal_year) or fiscal_year is None:
                reporting_year = "2024"  # Default year
            else:
                reporting_year = str(int(fiscal_year))
            
            reporting_quarter = "Q4"  # Fixed as requested
            
            # Check if prediction already exists
            existing_prediction = company_service.get_annual_prediction(
                company_id=str(company.id), 
                reporting_year=reporting_year
            )
            
            if existing_prediction and existing_prediction.reporting_quarter == reporting_quarter:
                logger.debug(f"⏭️ Prediction already exists for {company.symbol} FY{reporting_year} {reporting_quarter}")
                return existing_prediction
            
            # Run ML prediction with prepared ratios
            prepared_ratios = self.prepare_ratios_for_ml(ratios)
            prediction_result = self.ml_service.predict_default_probability(prepared_ratios)
            
            if 'error' in prediction_result:
                logger.warning(f"⚠️ ML prediction failed for {company.symbol}: {prediction_result['error']}")
                return None
            
            # Create prediction record with original ratios (can now include None values)
            annual_prediction = company_service.create_annual_prediction(
                company=company,
                financial_data=ratios,  # Use original ratios (can include None values now)
                prediction_results=prediction_result,
                reporting_year=reporting_year,
                reporting_quarter=reporting_quarter
            )
            
            return annual_prediction
            
        except Exception as e:
            logger.error(f"❌ Error creating prediction for {company.symbol}: {e}")
            return None
    
    def process_chunk(self, chunk: pd.DataFrame, chunk_number: int, db, user_id: str, dry_run: bool = False) -> Dict:
        """Process a chunk of data - ultra-optimized version with dry run support"""
        chunk_stats = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'duplicates_skipped': 0,
            'companies_created': 0
        }
        
        mode_text = "[DRY RUN] " if dry_run else ""
        logger.info(f"🔄 {mode_text}Processing chunk {chunk_number}: {len(chunk)} records")
        
        try:
            company_service = CompanyService(db)
            
            # Batch ML predictions for better performance
            valid_records = []
            ratios_batch = []
            
            # First pass: validate and prepare batch
            for idx, (_, row) in enumerate(chunk.iterrows()):
                chunk_stats['processed'] += 1
                
                try:
                    # Extract financial ratios
                    ratios = self.extract_financial_ratios(row)
                    
                    # Validate financial data
                    is_valid, null_count = self.validate_financial_data(ratios)
                    
                    if not is_valid:
                        chunk_stats['skipped'] += 1
                        if chunk_stats['processed'] <= 5:  # Log first few skips
                            logger.debug(f"⏭️ Skipping record {idx+1}: too many null values ({null_count}/5)")
                        continue
                    
                    # Create or get company (even in dry run for validation)
                    company = self.create_or_get_company(row, company_service)
                    if not company:
                        chunk_stats['skipped'] += 1
                        if chunk_stats['processed'] <= 5:
                            logger.debug(f"⏭️ Skipping record {idx+1}: could not create company")
                        continue
                    
                    # Add to valid records
                    valid_records.append((idx, row, ratios, company))
                    ratios_batch.append(self.prepare_ratios_for_ml(ratios))
                    
                except Exception as e:
                    chunk_stats['failed'] += 1
                    if chunk_stats['failed'] <= 3:  # Log first few failures
                        logger.warning(f"⚠️ Error processing record {idx+1}: {e}")
                    continue
            
            # Second pass: batch ML predictions
            if valid_records and ratios_batch:
                logger.info(f"📊 {mode_text}Running ML predictions for {len(valid_records)} records...")
                
                # Process records in smaller ML batches for speed
                ml_batch_size = 50
                for i in range(0, len(valid_records), ml_batch_size):
                    batch_end = min(i + ml_batch_size, len(valid_records))
                    batch_records = valid_records[i:batch_end]
                    batch_ratios = ratios_batch[i:batch_end]
                    
                    for j, ((idx, row, ratios, company), prepared_ratios) in enumerate(zip(batch_records, batch_ratios)):
                        try:
                            # Log input data for ML prediction
                            ticker = company.symbol
                            ml_logger.debug(f"🤖 ML Input for {ticker}: {prepared_ratios}")
                            
                            # Run ML prediction
                            prediction_result = self.ml_service.predict_default_probability(prepared_ratios)
                            
                            # Log ML output
                            ml_logger.info(f"🎯 ML Output for {ticker}: {prediction_result}")
                            
                            if 'error' in prediction_result:
                                chunk_stats['failed'] += 1
                                ml_logger.error(f"❌ ML prediction failed for {ticker}: {prediction_result['error']}")
                                continue
                            
                            if dry_run:
                                # In dry run, just count as successful without saving
                                chunk_stats['successful'] += 1
                                if chunk_stats['successful'] <= 3:
                                    logger.info(f"✅ [DRY RUN] Would create prediction for {company.symbol}: "
                                              f"probability={prediction_result.get('default_probability', 0.0):.3f}")
                            else:
                                # PRODUCTION MODE - Add to batch for database insertion
                                self.add_to_prediction_batch(company, row, ratios, prediction_result, user_id)
                                
                                # Flush batch when it reaches batch_size
                                if len(self.prediction_batch) >= self.batch_size:
                                    batch_successful, batch_failed = self.flush_prediction_batch(company_service, db, dry_run)
                                    chunk_stats['successful'] += batch_successful
                                    chunk_stats['failed'] += batch_failed
                                    
                                    # Commit batch (only in production mode)
                                    db.commit()
                                    db_logger.debug(f"💾 Committed batch of {batch_successful} predictions")
                                    chunk_stats['successful'] += batch_successful
                                    chunk_stats['failed'] += batch_failed
                                    
                                    # Commit batch
                                    db.commit()
                            
                        except Exception as e:
                            chunk_stats['failed'] += 1
                            if chunk_stats['failed'] <= 3:
                                logger.warning(f"⚠️ Error processing {company.symbol if 'company' in locals() else 'unknown'}: {e}")
                            continue
                
                # Flush remaining predictions (only in production mode)
                if not dry_run and self.prediction_batch:
                    batch_successful, batch_failed = self.flush_prediction_batch(company_service, db)
                    chunk_stats['successful'] += batch_successful
                    chunk_stats['failed'] += batch_failed
            
            # Final commit for chunk (only in production mode)
            if not dry_run:
                db.commit()
            
            logger.info(f"✅ {mode_text}Chunk {chunk_number} completed: {chunk_stats['successful']} successful, "
                       f"{chunk_stats['failed']} failed, {chunk_stats['skipped']} skipped")
            
        except Exception as e:
            logger.error(f"❌ Critical error in chunk {chunk_number}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            if not dry_run:
                db.rollback()
            raise
        
        return chunk_stats
    
    def process_bulk_predictions(self, run_id: str = None, dry_run: bool = False) -> Tuple[int, int, int]:
        """
        Main method to run bulk predictions with optional dry run mode
        Returns: (successful_count, failed_count, total_processed)
        """
        try:
            self.stats['start_time'] = datetime.now()
            run_mode = "DRY RUN" if dry_run else "PRODUCTION"
            logger.info(f"🚀 Starting {run_mode} bulk annual predictions at {self.stats['start_time']}")
            
            # Initialize services
            if not self.initialize_ml_service():
                return 0, 0, 0
            
            # Load data
            start_load = time.time()
            data = self.load_annual_data()
            load_time = time.time() - start_load
            logger.info(f"⚡ Data loading completed in {load_time:.2f} seconds")
            
            # Pre-filter data to remove obviously invalid records
            logger.info("🔍 Pre-filtering data for performance...")
            original_size = len(data)
            
            # Remove records with invalid tickers
            data = data[data['ticker'].notna() & (data['ticker'] != '') & (data['ticker'] != 'nan')]
            
            # Log filtering results
            filtered_size = len(data)
            logger.info(f"📊 Pre-filtering: {original_size:,} → {filtered_size:,} records "
                       f"({((original_size - filtered_size) / original_size * 100):.1f}% filtered out)")
            
            # Get database session
            db = SessionLocal()
            
            try:
                # Get user
                user = self.get_or_create_user(db)
                
                # Process data in chunks
                total_chunks = (len(data) + self.chunk_size - 1) // self.chunk_size
                logger.info(f"📊 Processing {len(data):,} records in {total_chunks} chunks of {self.chunk_size}")
                logger.info(f"⚡ Using batch size of {self.batch_size} for database operations")
                logger.info(f"🎯 Mode: {run_mode}")
                
                chunk_times = []
                
                for chunk_num in range(total_chunks):
                    chunk_start = time.time()
                    
                    start_idx = chunk_num * self.chunk_size
                    end_idx = min(start_idx + self.chunk_size, len(data))
                    chunk = data.iloc[start_idx:end_idx]
                    
                    chunk_stats = self.process_chunk(chunk, chunk_num + 1, db, str(user.id), dry_run)
                    
                    chunk_time = time.time() - chunk_start
                    chunk_times.append(chunk_time)
                    
                    # Update overall stats
                    self.stats['total_processed'] += chunk_stats['processed']
                    self.stats['successful_predictions'] += chunk_stats['successful']
                    self.stats['failed_predictions'] += chunk_stats['failed']
                    self.stats['skipped_invalid_data'] += chunk_stats['skipped']
                    
                    # Progress update with performance metrics
                    progress = ((chunk_num + 1) / total_chunks) * 100
                    avg_chunk_time = sum(chunk_times) / len(chunk_times)
                    estimated_remaining = avg_chunk_time * (total_chunks - chunk_num - 1)
                    
                    logger.info(f"📈 Progress: {progress:.1f}% ({chunk_num + 1}/{total_chunks} chunks) | "
                               f"⚡ Chunk time: {chunk_time:.1f}s | "
                               f"🕒 Est. remaining: {estimated_remaining/60:.1f}m")
                
                self.stats['end_time'] = datetime.now()
                self.log_final_stats()
                
                return (self.stats['successful_predictions'], 
                       self.stats['failed_predictions'], 
                       self.stats['total_processed'])
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Critical error in bulk predictions: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.stats['end_time'] = datetime.now()
            return 0, 0, 0

    def run_bulk_predictions(self) -> bool:
        """Legacy method for backward compatibility"""
        successful, failed, total = self.process_bulk_predictions()
        return successful > 0 and total > 0
    
    def log_final_stats(self):
        """Log final statistics with enhanced details"""
        duration = self.stats['end_time'] - self.stats['start_time']
        
        logger.info("=" * 80)
        logger.info("📊 BULK ANNUAL PREDICTIONS COMPLETED")
        logger.info("=" * 80)
        logger.info(f"⏱️  Total Duration: {duration}")
        logger.info(f"📋 Total Records Processed: {self.stats['total_processed']:,}")
        logger.info(f"✅ Successful Predictions: {self.stats['successful_predictions']:,}")
        logger.info(f"❌ Failed Predictions: {self.stats['failed_predictions']:,}")
        logger.info(f"⏭️  Skipped (Invalid Data): {self.stats['skipped_invalid_data']:,}")
        logger.info(f"🏢 Companies in Cache: {len(self.company_cache):,}")
        
        if self.stats['total_processed'] > 0:
            success_rate = (self.stats['successful_predictions'] / self.stats['total_processed']) * 100
            logger.info(f"📈 Success Rate: {success_rate:.2f}%")
            
            records_per_second = self.stats['total_processed'] / duration.total_seconds()
            logger.info(f"⚡ Processing Rate: {records_per_second:.2f} records/second")
            
            # Estimate database size impact
            avg_record_size = 0.5  # KB per prediction record estimate
            total_data_kb = self.stats['successful_predictions'] * avg_record_size
            logger.info(f"💾 Estimated Database Impact: {total_data_kb:.1f} KB ({total_data_kb/1024:.1f} MB)")
        
        # Performance insights
        if duration.total_seconds() > 0:
            if self.stats['successful_predictions'] > 8000:
                logger.info("🏆 EXCELLENT: High throughput achieved!")
            elif self.stats['successful_predictions'] > 5000:
                logger.info("✅ GOOD: Satisfactory processing speed")
            else:
                logger.info("⚠️  SLOW: Consider optimizing chunk/batch sizes")
        
        logger.info("=" * 80)


def main():
    """Main function - ultra-optimized for maximum speed"""
    # Use aggressive settings for speed
    cpu_count = multiprocessing.cpu_count()
    
    # Larger chunks and batches for maximum throughput
    optimal_chunk_size = min(5000, max(1000, cpu_count * 500))  # Bigger chunks
    optimal_batch_size = min(500, max(100, cpu_count * 50))     # Much bigger batches
    
    logger.info(f"🖥️  System info: {cpu_count} CPU cores")
    logger.info(f"⚡ Ultra-optimized chunk size: {optimal_chunk_size}")
    logger.info(f"⚡ Ultra-optimized batch size: {optimal_batch_size}")
    
    processor = BulkAnnualPredictionProcessor(
        chunk_size=optimal_chunk_size, 
        batch_size=optimal_batch_size
    )
    
    start_time = time.time()
    success = processor.run_bulk_predictions()
    end_time = time.time()
    
    total_time = end_time - start_time
    
    if success:
        logger.info(f"🎉 Ultra-optimized bulk predictions completed in {total_time/60:.1f} minutes!")
        if processor.stats['total_processed'] > 0:
            rate = processor.stats['total_processed'] / total_time
            logger.info(f"🚀 Final processing rate: {rate:.1f} records/second")
        sys.exit(0)
    else:
        logger.error(f"💥 Bulk predictions failed after {total_time/60:.1f} minutes!")
        sys.exit(1)


if __name__ == "__main__":
    main()
