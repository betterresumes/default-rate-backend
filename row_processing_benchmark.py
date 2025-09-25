#!/usr/bin/env python3
"""
Real-Time Row Processing Benchmark
Measures actual time for each step: ML prediction + database save
"""

import asyncio
import time
import pandas as pd
import uuid
from datetime import datetime
import sys
import os

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.ml_service import ml_model
from app.services.quarterly_ml_service import quarterly_ml_model
from app.core.database import get_session_local, Company, AnnualPrediction, QuarterlyPrediction

class RowProcessingBenchmark:
    def __init__(self):
        self.results = []
        
    def log_step(self, step, elapsed_time, details=""):
        """Log each processing step with timing"""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]  # Include milliseconds
        print(f"[{timestamp}] {step:20} | {elapsed_time*1000:7.2f}ms | {details}")
        
    async def benchmark_single_annual_row(self, row_data, row_number=1):
        """Benchmark processing a single annual row with detailed timing"""
        print(f"\n🔍 BENCHMARKING ANNUAL ROW {row_number}")
        print("=" * 70)
        
        total_start = time.time()
        step_times = {}
        
        # Step 1: Data preparation
        step_start = time.time()
        financial_data = {
            'long_term_debt_to_total_capital': float(row_data['long_term_debt_to_total_capital']),
            'total_debt_to_ebitda': float(row_data['total_debt_to_ebitda']),
            'net_income_margin': float(row_data['net_income_margin']),
            'ebit_to_interest_expense': float(row_data['ebit_to_interest_expense']),
            'return_on_assets': float(row_data['return_on_assets'])
        }
        step_times['data_prep'] = time.time() - step_start
        self.log_step("Data Preparation", step_times['data_prep'], f"Company: {row_data['company_symbol']}")
        
        # Step 2: ML Prediction
        step_start = time.time()
        ml_result = await ml_model.predict_annual(financial_data)
        step_times['ml_prediction'] = time.time() - step_start
        self.log_step("ML Prediction", step_times['ml_prediction'], 
                     f"Risk: {ml_result['risk_level']}, Prob: {ml_result['probability']:.3f}")
        
        # Step 3: Database connection
        step_start = time.time()
        SessionLocal = get_session_local()
        db = SessionLocal()
        step_times['db_connection'] = time.time() - step_start
        self.log_step("DB Connection", step_times['db_connection'])
        
        # Step 4: Company lookup/creation
        step_start = time.time()
        existing_company = db.query(Company).filter(
            Company.symbol == row_data['company_symbol'].upper()
        ).first()
        
        if not existing_company:
            company = Company(
                symbol=row_data['company_symbol'].upper(),
                name=row_data['company_name'],
                market_cap=float(row_data['market_cap']),
                sector=row_data['sector'],
                access_level="system",
                organization_id=None,
                created_by="benchmark-test"
            )
            db.add(company)
            db.flush()  # Get the ID without committing
        else:
            company = existing_company
            
        step_times['company_handling'] = time.time() - step_start
        self.log_step("Company Handling", step_times['company_handling'], 
                     f"{'Created' if not existing_company else 'Found'}: {company.symbol}")
        
        # Step 5: Prediction creation
        step_start = time.time()
        prediction = AnnualPrediction(
            id=uuid.uuid4(),
            company_id=company.id,
            organization_id=None,
            access_level="system",
            reporting_year=str(row_data['reporting_year']),
            reporting_quarter=row_data.get('reporting_quarter'),
            long_term_debt_to_total_capital=financial_data['long_term_debt_to_total_capital'],
            total_debt_to_ebitda=financial_data['total_debt_to_ebitda'],
            net_income_margin=financial_data['net_income_margin'],
            ebit_to_interest_expense=financial_data['ebit_to_interest_expense'],
            return_on_assets=financial_data['return_on_assets'],
            probability=float(ml_result['probability']),
            risk_level=ml_result['risk_level'],
            confidence=float(ml_result['confidence']),
            predicted_at=datetime.utcnow(),
            created_by="benchmark-test"
        )
        db.add(prediction)
        step_times['prediction_creation'] = time.time() - step_start
        self.log_step("Prediction Creation", step_times['prediction_creation'])
        
        # Step 6: Database commit
        step_start = time.time()
        db.commit()
        step_times['db_commit'] = time.time() - step_start
        self.log_step("Database Commit", step_times['db_commit'])
        
        # Step 7: Cleanup
        step_start = time.time()
        db.close()
        step_times['cleanup'] = time.time() - step_start
        self.log_step("Cleanup", step_times['cleanup'])
        
        # Total time
        total_time = time.time() - total_start
        step_times['total'] = total_time
        
        print(f"\n📊 SUMMARY FOR ROW {row_number}:")
        print(f"   Total Time: {total_time*1000:.2f}ms ({total_time:.3f}s)")
        print(f"   Company: {row_data['company_symbol']} - {ml_result['risk_level']} Risk")
        
        return step_times, ml_result
    
    async def benchmark_single_quarterly_row(self, row_data, row_number=1):
        """Benchmark processing a single quarterly row with detailed timing"""
        print(f"\n🔍 BENCHMARKING QUARTERLY ROW {row_number}")
        print("=" * 70)
        
        total_start = time.time()
        step_times = {}
        
        # Step 1: Data preparation
        step_start = time.time()
        financial_data = {
            'total_debt_to_ebitda': float(row_data['total_debt_to_ebitda']),
            'sga_margin': float(row_data['sga_margin']),
            'long_term_debt_to_total_capital': float(row_data['long_term_debt_to_total_capital']),
            'return_on_capital': float(row_data['return_on_capital'])
        }
        step_times['data_prep'] = time.time() - step_start
        self.log_step("Data Preparation", step_times['data_prep'], f"Company: {row_data['company_symbol']}")
        
        # Step 2: ML Prediction
        step_start = time.time()
        ml_result = await quarterly_ml_model.predict_quarterly(financial_data)
        step_times['ml_prediction'] = time.time() - step_start
        self.log_step("ML Prediction", step_times['ml_prediction'], 
                     f"Risk: {ml_result['risk_level']}, Ensemble: {ml_result.get('ensemble_probability', 0):.3f}")
        
        # Steps 3-7: Same as annual (database operations)
        # ... (database operations would be similar)
        
        total_time = time.time() - total_start
        step_times['total'] = total_time
        
        print(f"\n📊 SUMMARY FOR ROW {row_number}:")
        print(f"   Total Time: {total_time*1000:.2f}ms ({total_time:.3f}s)")
        print(f"   Company: {row_data['company_symbol']} - {ml_result['risk_level']} Risk")
        
        return step_times, ml_result
    
    async def benchmark_full_file(self, data, prediction_type="annual"):
        """Benchmark processing a complete file row by row"""
        print(f"\n🚀 BENCHMARKING COMPLETE {prediction_type.upper()} FILE")
        print("=" * 80)
        print(f"📁 File contains {len(data)} companies")
        
        file_start_time = time.time()
        all_row_times = []
        total_ml_time = 0
        total_db_time = 0
        
        for i, row in enumerate(data):
            if prediction_type == "annual":
                step_times, ml_result = await self.benchmark_single_annual_row(row, i+1)
            else:
                step_times, ml_result = await self.benchmark_single_quarterly_row(row, i+1)
            
            all_row_times.append(step_times['total'])
            total_ml_time += step_times['ml_prediction']
            total_db_time += (step_times.get('company_handling', 0) + 
                             step_times.get('prediction_creation', 0) + 
                             step_times.get('db_commit', 0))
            
            # Show progress for multi-row files
            if len(data) > 1:
                progress = ((i + 1) / len(data)) * 100
                elapsed = time.time() - file_start_time
                estimated_total = elapsed / (i + 1) * len(data)
                remaining = estimated_total - elapsed
                
                print(f"\n⏱️  PROGRESS: {progress:.1f}% ({i+1}/{len(data)} rows)")
                print(f"   Elapsed: {elapsed:.1f}s | Remaining: ~{remaining:.1f}s | Total: ~{estimated_total:.1f}s")
        
        # Final file statistics
        total_file_time = time.time() - file_start_time
        avg_row_time = total_file_time / len(data)
        rows_per_second = len(data) / total_file_time
        
        print(f"\n🎯 COMPLETE FILE BENCHMARK RESULTS")
        print("=" * 80)
        print(f"📊 File Statistics:")
        print(f"   Total Rows: {len(data)}")
        print(f"   Total Time: {total_file_time:.2f} seconds")
        print(f"   Average per Row: {avg_row_time*1000:.2f}ms")
        print(f"   Processing Rate: {rows_per_second:.1f} rows/second")
        
        print(f"\n⚡ Performance Breakdown:")
        print(f"   ML Processing: {total_ml_time*1000:.1f}ms ({total_ml_time/total_file_time*100:.1f}%)")
        print(f"   Database Ops: {total_db_time*1000:.1f}ms ({total_db_time/total_file_time*100:.1f}%)")
        print(f"   Other Overhead: {(total_file_time-total_ml_time-total_db_time)*1000:.1f}ms")
        
        return {
            'total_time': total_file_time,
            'avg_row_time': avg_row_time,
            'rows_per_second': rows_per_second,
            'ml_time_percent': total_ml_time/total_file_time*100,
            'db_time_percent': total_db_time/total_file_time*100
        }

# Test data for benchmarking
annual_test_data = [
    {
        'company_symbol': 'AAPL',
        'company_name': 'Apple Inc',
        'market_cap': 3000000000000,
        'sector': 'Technology',
        'reporting_year': 2024,
        'reporting_quarter': 'Q4',
        'long_term_debt_to_total_capital': 0.35,
        'total_debt_to_ebitda': 2.1,
        'net_income_margin': 0.25,
        'ebit_to_interest_expense': 15.2,
        'return_on_assets': 0.18
    },
    {
        'company_symbol': 'MSFT',
        'company_name': 'Microsoft Corp',
        'market_cap': 2800000000000,
        'sector': 'Technology',
        'reporting_year': 2024,
        'reporting_quarter': 'Q4',
        'long_term_debt_to_total_capital': 0.28,
        'total_debt_to_ebitda': 1.8,
        'net_income_margin': 0.31,
        'ebit_to_interest_expense': 18.5,
        'return_on_assets': 0.16
    },
    {
        'company_symbol': 'GOOGL',
        'company_name': 'Alphabet Inc',
        'market_cap': 1800000000000,
        'sector': 'Technology',
        'reporting_year': 2024,
        'reporting_quarter': 'Q4',
        'long_term_debt_to_total_capital': 0.12,
        'total_debt_to_ebitda': 0.8,
        'net_income_margin': 0.21,
        'ebit_to_interest_expense': 25.1,
        'return_on_assets': 0.12
    },
    {
        'company_symbol': 'TSLA',
        'company_name': 'Tesla Inc',
        'market_cap': 800000000000,
        'sector': 'Automotive',
        'reporting_year': 2024,
        'reporting_quarter': 'Q4',
        'long_term_debt_to_total_capital': 0.45,
        'total_debt_to_ebitda': 3.2,
        'net_income_margin': 0.08,
        'ebit_to_interest_expense': 4.2,
        'return_on_assets': 0.05
    },
    {
        'company_symbol': 'META',
        'company_name': 'Meta Platforms',
        'market_cap': 750000000000,
        'sector': 'Technology',
        'reporting_year': 2024,
        'reporting_quarter': 'Q4',
        'long_term_debt_to_total_capital': 0.22,
        'total_debt_to_ebitda': 1.5,
        'net_income_margin': 0.23,
        'ebit_to_interest_expense': 12.8,
        'return_on_assets': 0.14
    }
]

async def main():
    """Run the complete row processing benchmark"""
    print("🔬 REAL-TIME ROW PROCESSING BENCHMARK")
    print("=" * 80)
    print(f"Testing with {len(annual_test_data)} companies")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    benchmark = RowProcessingBenchmark()
    
    # Benchmark the complete file
    results = await benchmark.benchmark_full_file(annual_test_data, "annual")
    
    # Generate projections for different file sizes
    print(f"\n📈 PROJECTIONS FOR DIFFERENT FILE SIZES")
    print("=" * 80)
    
    file_sizes = [10, 50, 100, 500, 1000, 5000, 10000]
    avg_time_per_row = results['avg_row_time']
    
    for size in file_sizes:
        estimated_time = size * avg_time_per_row
        if estimated_time < 60:
            time_str = f"{estimated_time:.1f} seconds"
        elif estimated_time < 3600:
            time_str = f"{estimated_time/60:.1f} minutes"
        else:
            time_str = f"{estimated_time/3600:.1f} hours"
        
        print(f"   {size:5,} rows: {time_str:15} (at {results['rows_per_second']:.1f} rows/sec)")
    
    print(f"\n✅ Benchmark completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Summary for user
    print(f"\n🎯 KEY TAKEAWAYS:")
    print(f"   • Single row processing: {avg_time_per_row*1000:.1f}ms")
    print(f"   • Your 5-row file: ~{5*avg_time_per_row:.1f} seconds")
    print(f"   • ML prediction: {results['ml_time_percent']:.1f}% of total time")
    print(f"   • Database operations: {results['db_time_percent']:.1f}% of total time")
    print(f"   • Processing rate: {results['rows_per_second']:.1f} companies per second")

if __name__ == "__main__":
    asyncio.run(main())
