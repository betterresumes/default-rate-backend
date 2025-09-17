#!/usr/bin/env python3
"""
Parallel Annual Predictions Creator
Breaks data into 4 parts and processes them in parallel
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
from multiprocessing import Process
from pathlib import Path

# Load environment variables
load_dotenv()

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

# Import database and services
from src.database import SessionLocal, Company, AnnualPrediction
from src.ml_service import MLModelService

def setup_logging():
    """Setup logging with separate files for each process"""
    # Create logs directory
    Path('logs').mkdir(exist_ok=True)
    
    # Configure main logger
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/parallel_main.log'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger('parallel_main')

def process_chunk(chunk_id, start_idx, end_idx, delay_seconds=0):
    """Process a chunk of data in a separate process"""
    
    # Setup logging for this chunk
    chunk_logger = logging.getLogger(f'chunk_{chunk_id}')
    chunk_handler = logging.FileHandler(f'logs/chunk_{chunk_id}.log')
    chunk_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    chunk_handler.setFormatter(chunk_formatter)
    chunk_logger.addHandler(chunk_handler)
    chunk_logger.setLevel(logging.INFO)
    
    try:
        # Add delay to stagger processes
        if delay_seconds > 0:
            chunk_logger.info(f"⏱️ Waiting {delay_seconds} seconds before starting...")
            time.sleep(delay_seconds)
        
        chunk_logger.info(f"🚀 Starting chunk {chunk_id}: records {start_idx} to {end_idx}")
        start_time = datetime.now()
        
        # Initialize ML service
        ml_service = MLModelService()
        chunk_logger.info(f"✅ ML service initialized for chunk {chunk_id}")
        
        # Load data
        with open('src/models/annual_step.pkl', 'rb') as f:
            data = pickle.load(f)
        
        chunk_data = data.iloc[start_idx:end_idx]
        chunk_logger.info(f"📊 Loaded {len(chunk_data)} records for chunk {chunk_id}")
        
        # Get database session
        db = SessionLocal()
        
        stats = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'companies_created': 0
        }
        
        try:
            for idx, (_, row) in enumerate(chunk_data.iterrows()):
                actual_idx = start_idx + idx
                
                if idx % 50 == 0:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    rate = idx / elapsed if elapsed > 0 else 0
                    chunk_logger.info(f"📈 Chunk {chunk_id} progress: {idx}/{len(chunk_data)} "
                                    f"({idx/len(chunk_data)*100:.1f}%) - {rate:.1f} records/sec")
                
                stats['processed'] += 1
                
                try:
                    # Get basic info
                    ticker = str(row.get('ticker', '')).strip().upper()
                    company_name = str(row.get('company name', '')).strip()
                    industry = str(row.get('Industry', '')).strip()
                    fiscal_year = row.get('fy')
                    
                    # Validate ticker
                    if not ticker or ticker in ['NAN', '']:
                        stats['skipped'] += 1
                        continue
                    
                    # Extract and clean financial ratios
                    ratios = {
                        'long_term_debt_to_total_capital': clean_financial_value(
                            row.get('long-term debt / total capital (%)')
                        ),
                        'total_debt_to_ebitda': clean_financial_value(
                            row.get('total debt / ebitda')
                        ),
                        'net_income_margin': clean_financial_value(
                            row.get('net income margin')
                        ),
                        'ebit_to_interest_expense': clean_financial_value(
                            row.get('ebit / interest expense')
                        ),
                        'return_on_assets': clean_financial_value(
                            row.get('return on assets')
                        )
                    }
                    
                    # Check if we have any valid ratios
                    valid_ratios = sum(1 for v in ratios.values() if v is not None)
                    if valid_ratios == 0:
                        stats['skipped'] += 1
                        continue
                    
                    # Create or get company
                    company = create_or_get_company(db, ticker, company_name, industry)
                    if not company:
                        stats['failed'] += 1
                        continue
                    
                    # Get ML prediction
                    ml_results = get_ml_prediction(ml_service, ratios, chunk_logger)
                    if not ml_results:
                        stats['failed'] += 1
                        continue
                    
                    # Create annual prediction
                    prediction = create_annual_prediction(db, company, ratios, ml_results, fiscal_year)
                    
                    if prediction:
                        stats['successful'] += 1
                        if idx % 100 == 0:  # Log every 100th success
                            chunk_logger.info(f"✅ Created prediction for {ticker} FY{fiscal_year or '2024'} "
                                            f"(prob: {ml_results['probability']:.3f})")
                    else:
                        stats['failed'] += 1
                    
                    # Commit every 25 records
                    if stats['successful'] % 25 == 0:
                        db.commit()
                        
                except Exception as e:
                    chunk_logger.error(f"❌ Error processing record {actual_idx}: {e}")
                    stats['failed'] += 1
                    continue
            
            # Final commit
            db.commit()
            
            end_time = datetime.now()
            duration = end_time - start_time
            
            # Log final stats for this chunk
            chunk_logger.info("="*60)
            chunk_logger.info(f"📊 CHUNK {chunk_id} COMPLETED")
            chunk_logger.info("="*60)
            chunk_logger.info(f"⏱️ Duration: {duration}")
            chunk_logger.info(f"📋 Processed: {stats['processed']}")
            chunk_logger.info(f"✅ Successful: {stats['successful']}")
            chunk_logger.info(f"❌ Failed: {stats['failed']}")
            chunk_logger.info(f"⏭️ Skipped: {stats['skipped']}")
            chunk_logger.info(f"📈 Success Rate: {stats['successful']/stats['processed']*100:.1f}%")
            chunk_logger.info(f"⚡ Rate: {stats['processed']/duration.total_seconds():.1f} records/sec")
            
            return stats
            
        except Exception as e:
            chunk_logger.error(f"💥 Critical error in chunk {chunk_id}: {e}")
            db.rollback()
            return stats
        finally:
            db.close()
            
    except Exception as e:
        chunk_logger.error(f"💥 Failed to initialize chunk {chunk_id}: {e}")
        return {'processed': 0, 'successful': 0, 'failed': 0, 'skipped': 0}

def clean_financial_value(value):
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

def create_or_get_company(db, ticker, company_name, industry):
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

def get_ml_prediction(ml_service, ratios, logger):
    """Get ML prediction for financial ratios"""
    try:
        prediction_result = ml_service.predict_default_probability(ratios)
        
        if 'error' in prediction_result:
            return None
            
        return {
            'probability': prediction_result.get('probability', 0.0),
            'risk_level': prediction_result.get('risk_level', 'MEDIUM'),
            'confidence': prediction_result.get('confidence', 0.5)
        }
    except Exception as e:
        logger.warning(f"⚠️ ML prediction failed: {e}")
        return None

def create_annual_prediction(db, company, ratios, ml_results, fiscal_year):
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

def main():
    """Main function - run parallel processing"""
    logger = setup_logging()
    
    print("🚀 Parallel Annual Predictions Creator")
    print("="*60)
    
    # Load data to get total count
    logger.info("📊 Loading data to determine chunk sizes...")
    with open('src/models/annual_step.pkl', 'rb') as f:
        data = pickle.load(f)
    
    total_records = len(data)
    logger.info(f"📋 Total records: {total_records:,}")
    
    # Calculate chunk sizes for 4 processes
    chunk_size = total_records // 4
    chunks = [
        (1, 0, chunk_size, 0),                           # Chunk 1: 0-2681, no delay
        (2, chunk_size, chunk_size * 2, 10),            # Chunk 2: 2681-5362, 10s delay
        (3, chunk_size * 2, chunk_size * 3, 20),        # Chunk 3: 5362-8043, 20s delay
        (4, chunk_size * 3, total_records, 30)          # Chunk 4: 8043-10726, 30s delay
    ]
    
    logger.info("📊 Chunk distribution:")
    for chunk_id, start_idx, end_idx, delay in chunks:
        logger.info(f"  Chunk {chunk_id}: records {start_idx:,} to {end_idx:,} "
                   f"({end_idx - start_idx:,} records) - delay: {delay}s")
    
    # Start all processes
    start_time = datetime.now()
    processes = []
    
    logger.info("🚀 Starting all 4 parallel processes...")
    
    for chunk_id, start_idx, end_idx, delay in chunks:
        process = Process(target=process_chunk, args=(chunk_id, start_idx, end_idx, delay))
        process.start()
        processes.append(process)
        logger.info(f"✅ Started process for chunk {chunk_id}")
    
    # Wait for all processes to complete
    logger.info("⏳ Waiting for all processes to complete...")
    
    for i, process in enumerate(processes):
        process.join()
        logger.info(f"✅ Chunk {i+1} process completed")
    
    end_time = datetime.now()
    total_duration = end_time - start_time
    
    # Final summary
    logger.info("="*60)
    logger.info("🎉 ALL PARALLEL PROCESSES COMPLETED")
    logger.info("="*60)
    logger.info(f"⏱️ Total Duration: {total_duration}")
    logger.info(f"📊 Total Records Processed: {total_records:,}")
    logger.info("📋 Check individual chunk logs in logs/ directory")
    
    # Verify final database state
    try:
        db = SessionLocal()
        total_predictions = db.query(AnnualPrediction).count()
        total_companies = db.query(Company).count()
        
        logger.info(f"🗄️ Final Database State:")
        logger.info(f"📊 Total Predictions: {total_predictions:,}")
        logger.info(f"🏢 Total Companies: {total_companies:,}")
        
        if total_predictions > 0:
            logger.info(f"⚡ Overall Processing Rate: {total_records/total_duration.total_seconds():.1f} records/sec")
        
        db.close()
        
    except Exception as e:
        logger.error(f"❌ Error checking final database state: {e}")

if __name__ == "__main__":
    main()
