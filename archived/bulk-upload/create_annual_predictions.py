#!/usr/bin/env python3
"""
Simple Annual Predictions Creator with Parallel Processing
Creates annual predictions from annual_step.pkl data in parallel chunks
"""

import os
import sys
import pickle
import pandas as pd
import numpy as np
import time
import logging
from datetime import datetime
from dotenv import load_dotenv
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from multiprocessing import Manager
import threading

# Load environment variables
load_dotenv()

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

# Import database and services
from src.database import SessionLocal, Company, AnnualPrediction
from src.ml_service import MLModelService

# Setup logging
def setup_logging():
    """Setup logging with timestamps"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'{log_dir}/annual_predictions.log'),
            logging.StreamHandler()
        ]
    )
    
    # Create separate loggers
    main_logger = logging.getLogger('main')
    detail_logger = logging.getLogger('detail')
    error_logger = logging.getLogger('error')
    
    # Add file handlers for each logger
    detail_handler = logging.FileHandler(f'{log_dir}/detail.log')
    detail_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    detail_logger.addHandler(detail_handler)
    
    error_handler = logging.FileHandler(f'{log_dir}/errors.log')
    error_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    error_logger.addHandler(error_handler)
    
    return main_logger, detail_logger, error_logger

main_logger, detail_logger, error_logger = setup_logging()

class SimpleAnnualPredictionCreator:
    def __init__(self, chunk_id=None):
        self.chunk_id = chunk_id or "main"
        self.ml_service = MLModelService()
        main_logger.info(f"🚀 Initialized processor for chunk {self.chunk_id}")
        
    def load_data(self):
        """Load annual step data"""
        main_logger.info("📊 Loading annual_step.pkl data...")
        with open('src/models/annual_step.pkl', 'rb') as f:
            data = pickle.load(f)
        main_logger.info(f"✅ Loaded {len(data):,} records")
        return data
    
    def clean_financial_value(self, value):
        """Clean financial value - handle 'NM', outliers, etc."""
        if value is None or pd.isna(value):
            return None
            
        if isinstance(value, str):
            value = value.strip().upper()
            if value in ['NM', 'N/A', 'NA', '', '-']:
                return None
        
        try:
            float_val = float(value)
            if np.isnan(float_val) or np.isinf(float_val):
                return None
            # Remove extreme outliers
            if abs(float_val) > 1000:
                return None
            return float_val
        except (ValueError, TypeError):
            return None
    
    def extract_financial_ratios(self, row):
        """Extract and clean financial ratios from row"""
        return {
            'long_term_debt_to_total_capital': self.clean_financial_value(
                row.get('long-term debt / total capital (%)')
            ),
            'total_debt_to_ebitda': self.clean_financial_value(
                row.get('total debt / ebitda')
            ),
            'net_income_margin': self.clean_financial_value(
                row.get('net income margin')
            ),
            'ebit_to_interest_expense': self.clean_financial_value(
                row.get('ebit / interest expense')
            ),
            'return_on_assets': self.clean_financial_value(
                row.get('return on assets')
            )
        }
    
    def create_or_get_company(self, db, ticker, company_name, industry):
        """Create or get company from database"""
        # Check if company exists
        company = db.query(Company).filter(Company.symbol == ticker.upper()).first()
        
        if company:
            return company
        
        # Create new company
        company = Company(
            symbol=ticker.upper(),
            name=company_name or ticker,
            market_cap=100000.0,  # Default market cap
            sector=industry or "Other"
        )
        db.add(company)
        db.flush()  # Get the ID without committing
        return company
    
    def get_ml_prediction(self, ratios):
        """Get ML prediction for financial ratios"""
        try:
            # Prepare ratios for ML (can handle None values)
            prediction_result = self.ml_service.predict_default_probability(ratios)
            
            if 'error' in prediction_result:
                return None
                
            return {
                'probability': prediction_result.get('probability', 0.0),
                'risk_level': prediction_result.get('risk_level', 'MEDIUM'),
                'confidence': prediction_result.get('confidence', 0.5)
            }
        except Exception as e:
            error_logger.error(f"⚠️ ML prediction failed: {e}")
            return None
    
    def create_annual_prediction(self, db, company, ratios, ml_results, fiscal_year):
        """Create annual prediction record"""
        reporting_year = str(int(fiscal_year)) if not pd.isna(fiscal_year) else "2024"
        
        # Check if prediction already exists
        existing = db.query(AnnualPrediction).filter(
            AnnualPrediction.company_id == company.id,
            AnnualPrediction.reporting_year == reporting_year,
            AnnualPrediction.reporting_quarter == "Q4"
        ).first()
        
        if existing:
            return existing
        
        # Create new prediction
        prediction = AnnualPrediction(
            company_id=company.id,
            reporting_year=reporting_year,
            reporting_quarter="Q4",
            long_term_debt_to_total_capital=ratios['long_term_debt_to_total_capital'],
            total_debt_to_ebitda=ratios['total_debt_to_ebitda'],
            net_income_margin=ratios['net_income_margin'],
            ebit_to_interest_expense=ratios['ebit_to_interest_expense'],
            return_on_assets=ratios['return_on_assets'],
            probability=ml_results['probability'],
            risk_level=ml_results['risk_level'],
            confidence=ml_results['confidence']
        )
        
        db.add(prediction)
        return prediction
    
    def process_data_chunk(self, data, start_idx, end_idx, delay_seconds=0):
        """Process a specific chunk of data with timing and logging"""
        chunk_name = f"chunk-{self.chunk_id}"
        chunk_data = data.iloc[start_idx:end_idx]
        chunk_size = len(chunk_data)
        
        # Add delay to avoid database conflicts
        if delay_seconds > 0:
            main_logger.info(f"⏱️ {chunk_name}: Waiting {delay_seconds}s before starting...")
            time.sleep(delay_seconds)
        
        main_logger.info(f"🚀 {chunk_name}: Starting processing of {chunk_size} records ({start_idx}-{end_idx})")
        start_time = time.time()
        
        db = SessionLocal()
        
        try:
            stats = {
                'processed': 0,
                'successful': 0,
                'failed': 0,
                'skipped': 0,
                'start_time': start_time,
                'chunk_name': chunk_name
            }
            
            # Process records
            for idx, (_, row) in enumerate(chunk_data.iterrows()):
                record_num = start_idx + idx + 1
                
                if idx % 50 == 0:
                    elapsed = time.time() - start_time
                    rate = idx / elapsed if elapsed > 0 else 0
                    remaining = (chunk_size - idx) / rate if rate > 0 else 0
                    main_logger.info(f"📈 {chunk_name}: {idx}/{chunk_size} ({idx/chunk_size*100:.1f}%) | "
                                   f"Rate: {rate:.1f} rec/sec | ETA: {remaining/60:.1f}min")
                
                stats['processed'] += 1
                
                try:
                    # Get basic info
                    ticker = str(row.get('ticker', '')).strip().upper()
                    company_name = str(row.get('company name', '')).strip()
                    industry = str(row.get('Industry', '')).strip()
                    fiscal_year = row.get('fy')
                    
                    # Validate ticker
                    if not ticker or ticker in ['NAN', '']:
                        detail_logger.debug(f"⏭️ {chunk_name}: Skipped record {record_num} - invalid ticker")
                        stats['skipped'] += 1
                        continue
                    
                    # Extract financial ratios
                    ratios = self.extract_financial_ratios(row)
                    
                    # Check if we have any valid ratios
                    valid_ratios = sum(1 for v in ratios.values() if v is not None)
                    if valid_ratios == 0:
                        detail_logger.debug(f"⏭️ {chunk_name}: Skipped record {record_num} - no valid ratios")
                        stats['skipped'] += 1
                        continue
                    
                    # Create or get company
                    company = self.create_or_get_company(db, ticker, company_name, industry)
                    if not company:
                        error_logger.error(f"❌ {chunk_name}: Failed to create company for {ticker}")
                        stats['failed'] += 1
                        continue
                    
                    # Get ML prediction
                    ml_results = self.get_ml_prediction(ratios)
                    if not ml_results:
                        error_logger.error(f"❌ {chunk_name}: ML prediction failed for {ticker}")
                        stats['failed'] += 1
                        continue
                    
                    # Create annual prediction
                    prediction = self.create_annual_prediction(
                        db, company, ratios, ml_results, fiscal_year
                    )
                    
                    if prediction:
                        stats['successful'] += 1
                        detail_logger.info(f"✅ {chunk_name}: Created prediction for {ticker} "
                                         f"FY{fiscal_year or '2024'} (prob: {ml_results['probability']:.3f})")
                    else:
                        stats['failed'] += 1
                    
                    # Commit every 25 records for this chunk
                    if stats['successful'] % 25 == 0:
                        db.commit()
                        detail_logger.debug(f"💾 {chunk_name}: Committed batch at {stats['successful']} records")
                        
                except Exception as e:
                    error_logger.error(f"❌ {chunk_name}: Error processing record {record_num}: {e}")
                    stats['failed'] += 1
                    continue
            
            # Final commit
            db.commit()
            
            # Calculate final timing
            end_time = time.time()
            duration = end_time - start_time
            rate = stats['processed'] / duration if duration > 0 else 0
            
            # Log final stats for this chunk
            main_logger.info(f"✅ {chunk_name}: COMPLETED in {duration/60:.2f} minutes")
            main_logger.info(f"� {chunk_name}: Processed: {stats['processed']}, "
                           f"Successful: {stats['successful']}, Failed: {stats['failed']}, "
                           f"Skipped: {stats['skipped']}")
            main_logger.info(f"⚡ {chunk_name}: Rate: {rate:.1f} records/second")
            
            return stats
            
        except Exception as e:
            error_logger.error(f"💥 {chunk_name}: Critical error: {e}")
            db.rollback()
            return {'processed': 0, 'successful': 0, 'failed': chunk_size, 'skipped': 0}
        finally:
            db.close()

def process_chunk_worker(chunk_id, start_idx, end_idx, delay_seconds):
    """Worker function for processing a chunk in parallel"""
    try:
        creator = SimpleAnnualPredictionCreator(chunk_id=chunk_id)
        data = creator.load_data()
        return creator.process_data_chunk(data, start_idx, end_idx, delay_seconds)
    except Exception as e:
        error_logger.error(f"💥 Worker {chunk_id} failed: {e}")
        return {'processed': 0, 'successful': 0, 'failed': end_idx - start_idx, 'skipped': 0}

def run_parallel_processing(total_records, num_chunks=4, delay_between_chunks=5):
    """Run parallel processing with multiple chunks"""
    main_logger.info(f"🚀 Starting parallel processing: {total_records:,} records in {num_chunks} chunks")
    main_logger.info(f"⏱️ Delay between chunks: {delay_between_chunks} seconds")
    
    # Calculate chunk sizes
    chunk_size = total_records // num_chunks
    chunks = []
    
    for i in range(num_chunks):
        start_idx = i * chunk_size
        if i == num_chunks - 1:
            # Last chunk gets remaining records
            end_idx = total_records
        else:
            end_idx = start_idx + chunk_size
        
        delay = i * delay_between_chunks  # Stagger start times
        chunks.append((f"chunk-{i+1}", start_idx, end_idx, delay))
        main_logger.info(f"📋 Chunk {i+1}: Records {start_idx}-{end_idx} ({end_idx-start_idx} records), "
                        f"Delay: {delay}s")
    
    start_time = time.time()
    
    # Run chunks in parallel using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=num_chunks) as executor:
        # Submit all chunks
        futures = []
        for chunk_id, start_idx, end_idx, delay in chunks:
            future = executor.submit(process_chunk_worker, chunk_id, start_idx, end_idx, delay)
            futures.append(future)
        
        # Collect results
        all_stats = []
        for i, future in enumerate(futures):
            try:
                stats = future.result()
                all_stats.append(stats)
                main_logger.info(f"✅ Chunk {i+1} completed: {stats['successful']} successful")
            except Exception as e:
                error_logger.error(f"❌ Chunk {i+1} failed: {e}")
                all_stats.append({'processed': 0, 'successful': 0, 'failed': 0, 'skipped': 0})
    
    end_time = time.time()
    total_duration = end_time - start_time
    
    # Aggregate results
    total_stats = {
        'processed': sum(s['processed'] for s in all_stats),
        'successful': sum(s['successful'] for s in all_stats),
        'failed': sum(s['failed'] for s in all_stats),
        'skipped': sum(s['skipped'] for s in all_stats)
    }
    
    # Log final results
    main_logger.info("="*80)
    main_logger.info("🏁 PARALLEL PROCESSING COMPLETED")
    main_logger.info("="*80)
    main_logger.info(f"⏱️ Total Duration: {total_duration/60:.2f} minutes")
    main_logger.info(f"📋 Total Processed: {total_stats['processed']:,}")
    main_logger.info(f"✅ Total Successful: {total_stats['successful']:,}")
    main_logger.info(f"❌ Total Failed: {total_stats['failed']:,}")
    main_logger.info(f"⏭️ Total Skipped: {total_stats['skipped']:,}")
    
    if total_stats['processed'] > 0:
        success_rate = (total_stats['successful'] / total_stats['processed']) * 100
        rate = total_stats['processed'] / total_duration
        main_logger.info(f"📈 Success Rate: {success_rate:.1f}%")
        main_logger.info(f"⚡ Processing Rate: {rate:.1f} records/second")
    
    # Verify database
    try:
        db = SessionLocal()
        total_predictions = db.query(AnnualPrediction).count()
        total_companies = db.query(Company).count()
        db.close()
        
        main_logger.info(f"🗄️ DATABASE VERIFICATION:")
        main_logger.info(f"📊 Total Predictions in DB: {total_predictions:,}")
        main_logger.info(f"🏢 Total Companies in DB: {total_companies:,}")
    except Exception as e:
        error_logger.error(f"❌ Database verification failed: {e}")
    
    return total_stats['successful'] > 0

def main():
    """Main function with parallel processing options"""
    main_logger.info("🎯 Annual Predictions Creator - Parallel Processing")
    main_logger.info("="*60)
    
    # Get user preferences
    try:
        max_records = input("Enter max records to process (or press Enter for all 10,726): ").strip()
        max_records = int(max_records) if max_records else None
        
        num_chunks = input("Enter number of parallel chunks (default 4): ").strip()
        num_chunks = int(num_chunks) if num_chunks else 4
        
        delay = input("Enter delay between chunks in seconds (default 5): ").strip()
        delay = int(delay) if delay else 5
        
    except ValueError:
        main_logger.info("Using default values...")
        max_records = None
        num_chunks = 4
        delay = 5
    
    # Load data to determine actual size
    creator = SimpleAnnualPredictionCreator()
    data = creator.load_data()
    
    total_records = min(len(data), max_records) if max_records else len(data)
    
    main_logger.info(f"🎯 Configuration:")
    main_logger.info(f"   📊 Records to process: {total_records:,}")
    main_logger.info(f"   🔀 Parallel chunks: {num_chunks}")
    main_logger.info(f"   ⏱️ Delay between chunks: {delay}s")
    
    # Start parallel processing
    start_time = datetime.now()
    success = run_parallel_processing(total_records, num_chunks, delay)
    end_time = datetime.now()
    
    duration = end_time - start_time
    main_logger.info(f"\n⏱️ Total execution time: {duration}")
    
    if success:
        main_logger.info("🎉 Annual predictions created successfully!")
    else:
        main_logger.error("💥 Failed to create predictions!")

if __name__ == "__main__":
    main()
