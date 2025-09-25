#!/usr/bin/env python3
"""
REAL-TIME BULK UPLOAD BENCHMARK
Measures actual processing time for each row using real database and ML models
"""

import asyncio
import time
import statistics
import pandas as pd
import uuid
import os
import sys
from datetime import datetime
from typing import Dict, Any, List

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()
load_dotenv('.env.local')

from app.services.ml_service import ml_model
from app.services.quarterly_ml_service import quarterly_ml_model
from app.core.database import get_session_local, Company, AnnualPrediction, QuarterlyPrediction

class RealTimeBulkUploadBenchmark:
    def __init__(self):
        self.results = []
        
    def create_test_data(self, num_rows=5):
        """Create test data for benchmarking"""
        
        # Annual prediction test data
        annual_companies = [
            {
                'company_symbol': f'TEST{i:03d}',
                'company_name': f'Test Company {i+1}',
                'market_cap': 1000000000 + (i * 100000000),
                'sector': ['Technology', 'Healthcare', 'Finance', 'Energy', 'Consumer'][i % 5],
                'reporting_year': '2024',
                'reporting_quarter': 'Q4',
                'long_term_debt_to_total_capital': 0.25 + (i * 0.05),
                'total_debt_to_ebitda': 2.0 + (i * 0.3),
                'net_income_margin': 0.10 + (i * 0.02),
                'ebit_to_interest_expense': 5.0 + (i * 1.5),
                'return_on_assets': 0.08 + (i * 0.01)
            }
            for i in range(num_rows)
        ]
        
        # Quarterly prediction test data
        quarterly_companies = [
            {
                'company_symbol': f'QTEST{i:03d}',
                'company_name': f'Quarterly Test Company {i+1}',
                'market_cap': 800000000 + (i * 80000000),
                'sector': ['Technology', 'Healthcare', 'Finance', 'Energy', 'Consumer'][i % 5],
                'reporting_year': '2024',
                'reporting_quarter': 'Q3',
                'total_debt_to_ebitda': 2.5 + (i * 0.4),
                'sga_margin': 0.20 + (i * 0.03),
                'long_term_debt_to_total_capital': 0.30 + (i * 0.05),
                'return_on_capital': 0.15 + (i * 0.02)
            }
            for i in range(num_rows)
        ]
        
        return annual_companies, quarterly_companies
    
    def safe_float(self, value):
        """Convert value to float, handling None and NaN values"""
        if value is None:
            return 0.0
        try:
            float_val = float(value)
            return float_val if not (float_val != float_val) else 0.0  # Check for NaN
        except (ValueError, TypeError):
            return 0.0
    
    def create_or_get_company(self, db, symbol, name, market_cap, sector, user_id=None):
        """Create or get company (simplified for testing)"""
        try:
            # Generate a valid UUID for testing if none provided
            if user_id is None:
                user_id = str(uuid.uuid4())
            
            existing = db.query(Company).filter(Company.symbol == symbol).first()
            if existing:
                return existing
                
            company = Company(
                symbol=symbol,
                name=name,
                market_cap=market_cap,
                sector=sector,
                access_level="personal",
                created_by=user_id
            )
            db.add(company)
            db.commit()
            db.refresh(company)
            return company
        except Exception as e:
            db.rollback()  # Rollback on error
            raise e
    
    async def process_single_annual_row(self, db, row_data, user_id=None):
        """Process a single annual prediction row and return detailed timing"""
        
        step_times = {}
        total_start = time.time()
        
        # Generate a valid UUID for testing if none provided
        if user_id is None:
            user_id = str(uuid.uuid4())
        
        try:
            # Step 1: Company creation/lookup
            step_start = time.time()
            company = self.create_or_get_company(
                db=db,
                symbol=row_data['company_symbol'],
                name=row_data['company_name'],
                market_cap=self.safe_float(row_data['market_cap']),
                sector=row_data['sector'],
                user_id=user_id
            )
            step_times['company_lookup'] = (time.time() - step_start) * 1000  # ms
            
            # Step 2: ML Prediction
            step_start = time.time()
            financial_data = {
                'long_term_debt_to_total_capital': self.safe_float(row_data['long_term_debt_to_total_capital']),
                'total_debt_to_ebitda': self.safe_float(row_data['total_debt_to_ebitda']),
                'net_income_margin': self.safe_float(row_data['net_income_margin']),
                'ebit_to_interest_expense': self.safe_float(row_data['ebit_to_interest_expense']),
                'return_on_assets': self.safe_float(row_data['return_on_assets'])
            }
            ml_result = await ml_model.predict_annual(financial_data)
            step_times['ml_prediction'] = (time.time() - step_start) * 1000  # ms
            
            # Step 3: Database prediction insert
            step_start = time.time()
            prediction = AnnualPrediction(
                id=uuid.uuid4(),
                company_id=company.id,
                organization_id=None,
                access_level="personal",
                reporting_year=str(row_data['reporting_year']),
                reporting_quarter=row_data.get('reporting_quarter'),
                long_term_debt_to_total_capital=financial_data['long_term_debt_to_total_capital'],
                total_debt_to_ebitda=financial_data['total_debt_to_ebitda'],
                net_income_margin=financial_data['net_income_margin'],
                ebit_to_interest_expense=financial_data['ebit_to_interest_expense'],
                return_on_assets=financial_data['return_on_assets'],
                probability=self.safe_float(ml_result['probability']),
                risk_level=ml_result['risk_level'],
                confidence=self.safe_float(ml_result['confidence']),
                predicted_at=datetime.utcnow(),
                created_by=user_id
            )
            db.add(prediction)
            db.commit()
            step_times['db_insert'] = (time.time() - step_start) * 1000  # ms
            
            step_times['total'] = (time.time() - total_start) * 1000  # ms
            step_times['success'] = True
            step_times['company_symbol'] = row_data['company_symbol']
            step_times['risk_level'] = ml_result['risk_level']
            step_times['probability'] = ml_result['probability']
            
            return step_times
            
        except Exception as e:
            step_times['total'] = (time.time() - total_start) * 1000
            step_times['success'] = False
            step_times['error'] = str(e)
            step_times['company_symbol'] = row_data.get('company_symbol', 'unknown')
            return step_times
    
    async def process_single_quarterly_row(self, db, row_data, user_id=None):
        """Process a single quarterly prediction row and return detailed timing"""
        
        step_times = {}
        total_start = time.time()
        
        # Generate a valid UUID for testing if none provided
        if user_id is None:
            user_id = str(uuid.uuid4())
        
        try:
            # Step 1: Company creation/lookup
            step_start = time.time()
            company = self.create_or_get_company(
                db=db,
                symbol=row_data['company_symbol'],
                name=row_data['company_name'],
                market_cap=self.safe_float(row_data['market_cap']),
                sector=row_data['sector'],
                user_id=user_id
            )
            step_times['company_lookup'] = (time.time() - step_start) * 1000
            
            # Step 2: ML Prediction
            step_start = time.time()
            financial_data = {
                'total_debt_to_ebitda': self.safe_float(row_data['total_debt_to_ebitda']),
                'sga_margin': self.safe_float(row_data['sga_margin']),
                'long_term_debt_to_total_capital': self.safe_float(row_data['long_term_debt_to_total_capital']),
                'return_on_capital': self.safe_float(row_data['return_on_capital'])
            }
            ml_result = await quarterly_ml_model.predict_quarterly(financial_data)
            step_times['ml_prediction'] = (time.time() - step_start) * 1000
            
            # Step 3: Database prediction insert
            step_start = time.time()
            prediction = QuarterlyPrediction(
                id=uuid.uuid4(),
                company_id=company.id,
                organization_id=None,
                access_level="personal",
                reporting_year=str(row_data['reporting_year']),
                reporting_quarter=row_data['reporting_quarter'],
                total_debt_to_ebitda=financial_data['total_debt_to_ebitda'],
                sga_margin=financial_data['sga_margin'],
                long_term_debt_to_total_capital=financial_data['long_term_debt_to_total_capital'],
                return_on_capital=financial_data['return_on_capital'],
                logistic_probability=self.safe_float(ml_result.get('logistic_probability', 0)),
                gbm_probability=self.safe_float(ml_result.get('gbm_probability', 0)),
                ensemble_probability=self.safe_float(ml_result.get('ensemble_probability', 0)),
                risk_level=ml_result['risk_level'],
                confidence=self.safe_float(ml_result['confidence']),
                predicted_at=datetime.utcnow(),
                created_by=user_id
            )
            db.add(prediction)
            db.commit()
            step_times['db_insert'] = (time.time() - step_start) * 1000
            
            step_times['total'] = (time.time() - total_start) * 1000
            step_times['success'] = True
            step_times['company_symbol'] = row_data['company_symbol']
            step_times['risk_level'] = ml_result['risk_level']
            step_times['ensemble_probability'] = ml_result.get('ensemble_probability', 0)
            
            return step_times
            
        except Exception as e:
            step_times['total'] = (time.time() - total_start) * 1000
            step_times['success'] = False
            step_times['error'] = str(e)
            step_times['company_symbol'] = row_data.get('company_symbol', 'unknown')
            return step_times
    
    async def benchmark_annual_processing(self, num_rows=5):
        """Benchmark annual prediction processing"""
        print(f"\n🧪 BENCHMARKING ANNUAL PREDICTIONS ({num_rows} rows)")
        print("=" * 70)
        
        # Get database session
        SessionLocal = get_session_local()
        db = SessionLocal()
        
        try:
            # Create test data
            annual_data, _ = self.create_test_data(num_rows)
            
            results = []
            total_start = time.time()
            
            print(f"Processing {num_rows} annual prediction rows...")
            print()
            
            for i, row_data in enumerate(annual_data):
                print(f"📊 Processing Row {i+1}/{num_rows}: {row_data['company_symbol']}")
                
                row_result = await self.process_single_annual_row(db, row_data)
                results.append(row_result)
                
                if row_result['success']:
                    print(f"   ✅ Success: {row_result['total']:.2f}ms total")
                    print(f"      - Company lookup: {row_result.get('company_lookup', 0):.2f}ms")
                    print(f"      - ML prediction:  {row_result.get('ml_prediction', 0):.2f}ms")  
                    print(f"      - DB insert:      {row_result.get('db_insert', 0):.2f}ms")
                    print(f"      - Risk level:     {row_result.get('risk_level', 'N/A')}")
                    print(f"      - Probability:    {row_result.get('probability', 0):.3f}")
                else:
                    print(f"   ❌ Failed: {row_result.get('error', 'Unknown error')}")
                print()
            
            total_time = time.time() - total_start
            
            # Calculate statistics
            successful_results = [r for r in results if r['success']]
            if successful_results:
                avg_total = statistics.mean([r['total'] for r in successful_results])
                avg_company_lookup = statistics.mean([r.get('company_lookup', 0) for r in successful_results])
                avg_ml_prediction = statistics.mean([r.get('ml_prediction', 0) for r in successful_results])
                avg_db_insert = statistics.mean([r.get('db_insert', 0) for r in successful_results])
                
                print(f"📊 ANNUAL PREDICTIONS BENCHMARK RESULTS")
                print(f"=" * 50)
                print(f"Total rows processed: {len(results)}")
                print(f"Successful: {len(successful_results)}")
                print(f"Failed: {len(results) - len(successful_results)}")
                print(f"Total processing time: {total_time:.2f}s")
                print()
                print(f"Average timings per row:")
                print(f"   📈 Total per row:    {avg_total:.2f}ms")
                print(f"   🏢 Company lookup:   {avg_company_lookup:.2f}ms ({avg_company_lookup/avg_total*100:.1f}%)")
                print(f"   🧠 ML prediction:    {avg_ml_prediction:.2f}ms ({avg_ml_prediction/avg_total*100:.1f}%)")
                print(f"   💾 DB insert:        {avg_db_insert:.2f}ms ({avg_db_insert/avg_total*100:.1f}%)")
                print()
                print(f"Performance metrics:")
                print(f"   ⚡ Rows per second:   {1000/avg_total:.1f}")
                print(f"   ⏱️  Rows per minute:   {60000/avg_total:.0f}")
                
                return {
                    'type': 'annual',
                    'total_rows': len(results),
                    'successful_rows': len(successful_results),
                    'avg_total_ms': avg_total,
                    'avg_company_lookup_ms': avg_company_lookup,
                    'avg_ml_prediction_ms': avg_ml_prediction,
                    'avg_db_insert_ms': avg_db_insert,
                    'rows_per_second': 1000/avg_total,
                    'total_processing_time': total_time
                }
            
        finally:
            db.close()
    
    async def benchmark_quarterly_processing(self, num_rows=5):
        """Benchmark quarterly prediction processing"""
        print(f"\n🧪 BENCHMARKING QUARTERLY PREDICTIONS ({num_rows} rows)")
        print("=" * 70)
        
        # Get database session
        SessionLocal = get_session_local()
        db = SessionLocal()
        
        try:
            # Create test data
            _, quarterly_data = self.create_test_data(num_rows)
            
            results = []
            total_start = time.time()
            
            print(f"Processing {num_rows} quarterly prediction rows...")
            print()
            
            for i, row_data in enumerate(quarterly_data):
                print(f"📊 Processing Row {i+1}/{num_rows}: {row_data['company_symbol']}")
                
                row_result = await self.process_single_quarterly_row(db, row_data)
                results.append(row_result)
                
                if row_result['success']:
                    print(f"   ✅ Success: {row_result['total']:.2f}ms total")
                    print(f"      - Company lookup: {row_result.get('company_lookup', 0):.2f}ms")
                    print(f"      - ML prediction:  {row_result.get('ml_prediction', 0):.2f}ms")
                    print(f"      - DB insert:      {row_result.get('db_insert', 0):.2f}ms")
                    print(f"      - Risk level:     {row_result.get('risk_level', 'N/A')}")
                    print(f"      - Ensemble prob:  {row_result.get('ensemble_probability', 0):.3f}")
                else:
                    print(f"   ❌ Failed: {row_result.get('error', 'Unknown error')}")
                print()
            
            total_time = time.time() - total_start
            
            # Calculate statistics  
            successful_results = [r for r in results if r['success']]
            if successful_results:
                avg_total = statistics.mean([r['total'] for r in successful_results])
                avg_company_lookup = statistics.mean([r.get('company_lookup', 0) for r in successful_results])
                avg_ml_prediction = statistics.mean([r.get('ml_prediction', 0) for r in successful_results])
                avg_db_insert = statistics.mean([r.get('db_insert', 0) for r in successful_results])
                
                print(f"📊 QUARTERLY PREDICTIONS BENCHMARK RESULTS")
                print(f"=" * 50)
                print(f"Total rows processed: {len(results)}")
                print(f"Successful: {len(successful_results)}")
                print(f"Failed: {len(results) - len(successful_results)}")
                print(f"Total processing time: {total_time:.2f}s")
                print()
                print(f"Average timings per row:")
                print(f"   📈 Total per row:    {avg_total:.2f}ms")
                print(f"   🏢 Company lookup:   {avg_company_lookup:.2f}ms ({avg_company_lookup/avg_total*100:.1f}%)")
                print(f"   🧠 ML prediction:    {avg_ml_prediction:.2f}ms ({avg_ml_prediction/avg_total*100:.1f}%)")
                print(f"   💾 DB insert:        {avg_db_insert:.2f}ms ({avg_db_insert/avg_total*100:.1f}%)")
                print()
                print(f"Performance metrics:")
                print(f"   ⚡ Rows per second:   {1000/avg_total:.1f}")
                print(f"   ⏱️  Rows per minute:   {60000/avg_total:.0f}")
                
                return {
                    'type': 'quarterly',
                    'total_rows': len(results),
                    'successful_rows': len(successful_results),
                    'avg_total_ms': avg_total,
                    'avg_company_lookup_ms': avg_company_lookup,
                    'avg_ml_prediction_ms': avg_ml_prediction,
                    'avg_db_insert_ms': avg_db_insert,
                    'rows_per_second': 1000/avg_total,
                    'total_processing_time': total_time
                }
                
        finally:
            db.close()
    
    def calculate_file_completion_estimates(self, annual_results, quarterly_results):
        """Calculate file completion estimates based on benchmark results"""
        print(f"\n🚀 FILE COMPLETION TIME ESTIMATES")
        print("=" * 70)
        
        file_sizes = [5, 10, 50, 100, 500, 1000, 5000, 10000]
        
        for results in [annual_results, quarterly_results]:
            if not results:
                continue
                
            prediction_type = results['type']
            avg_time_ms = results['avg_total_ms']
            rows_per_second = results['rows_per_second']
            
            print(f"\n📈 {prediction_type.title()} Prediction File Estimates:")
            print(f"   Single row processing: {avg_time_ms:.2f}ms")
            print(f"   Processing rate: {rows_per_second:.1f} rows/second")
            print()
            
            # Sequential processing estimates
            print("   📄 File Completion Times (Sequential):")
            for file_size in file_sizes:
                total_time_seconds = (file_size * avg_time_ms) / 1000
                
                if total_time_seconds < 60:
                    time_str = f"{total_time_seconds:.1f}s"
                elif total_time_seconds < 3600:
                    time_str = f"{total_time_seconds/60:.1f}min"
                else:
                    time_str = f"{total_time_seconds/3600:.1f}hr"
                    
                print(f"      {file_size:5d} rows: {time_str:>8}")
            
            print()
            
            # Parallel processing estimates (with different worker counts)
            worker_counts = [1, 4, 8, 16, 32]
            
            print("   ⚡ File Completion Times (Parallel Workers):")
            print("      Rows  |  1 Worker |  4 Workers |  8 Workers | 16 Workers | 32 Workers")
            print("      ------|-----------|------------|------------|------------|------------")
            
            for file_size in [100, 500, 1000, 5000, 10000]:
                sequential_time = (file_size * avg_time_ms) / 1000
                
                row_str = f"{file_size:5d} |"
                
                for workers in worker_counts:
                    # Account for overhead and diminishing returns
                    if workers == 1:
                        efficiency = 1.0
                    elif workers <= 8:
                        efficiency = 0.90  # 90% efficiency
                    else:
                        efficiency = 0.75  # 75% efficiency due to contention
                    
                    parallel_time = (sequential_time / workers) / efficiency
                    
                    if parallel_time < 60:
                        time_str = f"{parallel_time:.1f}s"
                    elif parallel_time < 3600:
                        time_str = f"{parallel_time/60:.1f}m"
                    else:
                        time_str = f"{parallel_time/3600:.1f}h"
                    
                    row_str += f" {time_str:>9} |"
                
                print(row_str)
    
    async def run_complete_benchmark(self, num_rows=5):
        """Run complete benchmark for both annual and quarterly predictions"""
        print("🚀 REAL-TIME BULK UPLOAD BENCHMARK")
        print("=" * 70)
        print(f"Testing with {num_rows} rows each")
        print(f"Using real database and ML models")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Test both prediction types
            annual_results = await self.benchmark_annual_processing(num_rows)
            quarterly_results = await self.benchmark_quarterly_processing(num_rows)
            
            # Calculate file completion estimates
            self.calculate_file_completion_estimates(annual_results, quarterly_results)
            
            print(f"\n✅ Benchmark completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            return annual_results, quarterly_results
            
        except Exception as e:
            print(f"\n❌ Benchmark failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return None, None

async def main():
    """Main function to run the benchmark"""
    benchmark = RealTimeBulkUploadBenchmark()
    
    # Run benchmark with 5 rows (as requested)
    await benchmark.run_complete_benchmark(num_rows=5)

if __name__ == "__main__":
    asyncio.run(main())
