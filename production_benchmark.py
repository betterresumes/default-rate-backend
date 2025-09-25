#!/usr/bin/env python3
"""
PRODUCTION-LEVEL BENCHMARK
Tests complete end-to-end process including database operations using real JWT token
Measures actual production speed with database inserts, company creation, and prediction storage
"""

import asyncio
import time
import statistics
import pandas as pd
import numpy as np
import os
import sys
import requests
import json
from datetime import datetime
from typing import Dict, Any, List

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import database and models
from app.core.database import get_session_local, Company, AnnualPrediction, QuarterlyPrediction

# Import ML services
from app.services.ml_service import MLModelService
from app.services.quarterly_ml_service import QuarterlyMLModelService

class ProductionBenchmark:
    def __init__(self, jwt_token=None, base_url="http://localhost:8000"):
        self.jwt_token = jwt_token
        self.base_url = base_url
        self.ml_service = None
        self.quarterly_ml_service = None
        self.headers = {
            "Authorization": f"Bearer {jwt_token}" if jwt_token else None,
            "Content-Type": "application/json"
        }
        
    def load_ml_models(self):
        """Load ML models and services"""
        try:
            # Load Annual ML Service
            self.ml_service = MLModelService()
            print("✅ Annual ML Model loaded successfully")
            
            # Load Quarterly ML Service  
            self.quarterly_ml_service = QuarterlyMLModelService()
            print("✅ Quarterly ML Model loaded successfully")
            
            return True
        except Exception as e:
            print(f"❌ Failed to load ML models: {e}")
            return False
            
    def create_realistic_test_data(self, num_rows=5):
        """Create realistic test data for production benchmarking"""
        
        # Real company-like data for annual predictions
        annual_companies = [
            {
                'company_symbol': f'PROD{i:03d}',
                'company_name': f'Production Test Corp {i+1}',
                'market_cap': 1000000000 + (i * 500000000),
                'sector': ['Technology', 'Healthcare', 'Financial Services', 'Energy', 'Consumer Discretionary'][i % 5],
                'reporting_year': 2024,
                'total_debt_to_ebitda': 2.1 + (i * 0.3),
                'sga_margin': 0.18 + (i * 0.025),
                'long_term_debt_to_total_capital': 0.28 + (i * 0.04),
                'return_on_capital': 0.12 + (i * 0.015),
                'net_income_margin': 0.08 + (i * 0.01),
                'ebit_to_interest_expense': 5.2 + (i * 0.8),
                'return_on_assets': 0.06 + (i * 0.01)
            }
            for i in range(num_rows)
        ]
        
        # Real company-like data for quarterly predictions
        quarterly_companies = [
            {
                'company_symbol': f'QPROD{i:03d}',
                'company_name': f'Quarterly Production Corp {i+1}',
                'market_cap': 800000000 + (i * 300000000),
                'sector': ['Technology', 'Healthcare', 'Financial Services', 'Energy', 'Consumer Discretionary'][i % 5],
                'reporting_year': 2024,
                'reporting_quarter': 'Q3',
                'total_debt_to_ebitda': 1.8 + (i * 0.25),
                'sga_margin': 0.16 + (i * 0.02),
                'long_term_debt_to_total_capital': 0.25 + (i * 0.035),
                'return_on_capital': 0.14 + (i * 0.012)
            }
            for i in range(num_rows)
        ]
        
        return annual_companies, quarterly_companies
    
    def create_or_get_company_db(self, db, company_data, user_id):
        """Create or get company in database"""
        try:
            # Check if company exists
            existing = db.query(Company).filter(Company.symbol == company_data['company_symbol']).first()
            if existing:
                return existing
                
            # Create new company
            company = Company(
                symbol=company_data['company_symbol'],
                name=company_data['company_name'],
                market_cap=company_data['market_cap'],
                sector=company_data['sector'],
                access_level="personal",
                created_by=user_id
            )
            db.add(company)
            db.commit()
            db.refresh(company)
            return company
        except Exception as e:
            db.rollback()
            raise e
    
    async def process_annual_prediction_production(self, db, company_data, user_id):
        """Process single annual prediction with full database operations"""
        
        step_times = {}
        total_start = time.time()
        
        try:
            # Step 1: Company creation/lookup in database
            step_start = time.time()
            
            company = self.create_or_get_company_db(db, company_data, user_id)
            
            step_times['company_db'] = (time.time() - step_start) * 1000
            
            # Step 2: Data preprocessing
            step_start = time.time()
            
            financial_ratios = {
                'total_debt_to_ebitda': company_data['total_debt_to_ebitda'],
                'sga_margin': company_data['sga_margin'],
                'long_term_debt_to_total_capital': company_data['long_term_debt_to_total_capital'],
                'return_on_capital': company_data['return_on_capital'],
                'net_income_margin': company_data.get('net_income_margin', 0.08),
                'ebit_to_interest_expense': company_data.get('ebit_to_interest_expense', 5.0),
                'return_on_assets': company_data.get('return_on_assets', 0.06)
            }
            
            step_times['preprocessing'] = (time.time() - step_start) * 1000
            
            # Step 3: ML Prediction
            step_start = time.time()
            
            prediction_result = await self.ml_service.predict_annual(financial_ratios)
            
            step_times['ml_prediction'] = (time.time() - step_start) * 1000
            
            # Step 4: Save prediction to database
            step_start = time.time()
            
            annual_prediction = AnnualPrediction(
                company_id=company.id,
                reporting_year=company_data['reporting_year'],
                probability=prediction_result.get('probability', 0.0),
                risk_level=prediction_result.get('risk_level', 'UNKNOWN'),
                confidence=prediction_result.get('confidence', 0.5),
                total_debt_to_ebitda=financial_ratios['total_debt_to_ebitda'],
                sga_margin=financial_ratios['sga_margin'],
                long_term_debt_to_total_capital=financial_ratios['long_term_debt_to_total_capital'],
                return_on_capital=financial_ratios['return_on_capital'],
                net_income_margin=financial_ratios['net_income_margin'],
                ebit_to_interest_expense=financial_ratios['ebit_to_interest_expense'],
                return_on_assets=financial_ratios['return_on_assets'],
                created_by=user_id
            )
            
            db.add(annual_prediction)
            db.commit()
            db.refresh(annual_prediction)
            
            step_times['db_insert'] = (time.time() - step_start) * 1000
            
            # Total time
            step_times['total'] = (time.time() - total_start) * 1000
            step_times['success'] = True
            step_times['company_symbol'] = company_data['company_symbol']
            step_times['prediction_id'] = str(annual_prediction.id)
            step_times['prediction_score'] = prediction_result.get('probability', 0.0)
            step_times['risk_level'] = prediction_result.get('risk_level', 'Unknown')
            
            return step_times
            
        except Exception as e:
            db.rollback()
            step_times['total'] = (time.time() - total_start) * 1000
            step_times['success'] = False
            step_times['error'] = str(e)
            step_times['company_symbol'] = company_data['company_symbol']
            return step_times
    
    async def process_quarterly_prediction_production(self, db, company_data, user_id):
        """Process single quarterly prediction with full database operations"""
        
        step_times = {}
        total_start = time.time()
        
        try:
            # Step 1: Company creation/lookup in database
            step_start = time.time()
            
            company = self.create_or_get_company_db(db, company_data, user_id)
            
            step_times['company_db'] = (time.time() - step_start) * 1000
            
            # Step 2: Data preprocessing
            step_start = time.time()
            
            financial_ratios = {
                'total_debt_to_ebitda': company_data['total_debt_to_ebitda'],
                'sga_margin': company_data['sga_margin'],
                'long_term_debt_to_total_capital': company_data['long_term_debt_to_total_capital'],
                'return_on_capital': company_data['return_on_capital']
            }
            
            step_times['preprocessing'] = (time.time() - step_start) * 1000
            
            # Step 3: ML Prediction
            step_start = time.time()
            
            prediction_result = await self.quarterly_ml_service.predict_quarterly(financial_ratios)
            
            step_times['ml_prediction'] = (time.time() - step_start) * 1000
            
            # Step 4: Save prediction to database
            step_start = time.time()
            
            quarterly_prediction = QuarterlyPrediction(
                company_id=company.id,
                reporting_year=company_data['reporting_year'],
                reporting_quarter=company_data['reporting_quarter'],
                probability=prediction_result.get('probability', 0.0),
                risk_level=prediction_result.get('risk_level', 'UNKNOWN'),
                confidence=prediction_result.get('confidence', 0.5),
                total_debt_to_ebitda=financial_ratios['total_debt_to_ebitda'],
                sga_margin=financial_ratios['sga_margin'],
                long_term_debt_to_total_capital=financial_ratios['long_term_debt_to_total_capital'],
                return_on_capital=financial_ratios['return_on_capital'],
                created_by=user_id
            )
            
            db.add(quarterly_prediction)
            db.commit()
            db.refresh(quarterly_prediction)
            
            step_times['db_insert'] = (time.time() - step_start) * 1000
            
            # Total time
            step_times['total'] = (time.time() - total_start) * 1000
            step_times['success'] = True
            step_times['company_symbol'] = company_data['company_symbol']
            step_times['prediction_id'] = str(quarterly_prediction.id)
            step_times['prediction_score'] = prediction_result.get('probability', 0.0)
            step_times['risk_level'] = prediction_result.get('risk_level', 'Unknown')
            
            return step_times
            
        except Exception as e:
            db.rollback()
            step_times['total'] = (time.time() - total_start) * 1000
            step_times['success'] = False
            step_times['error'] = str(e)
            step_times['company_symbol'] = company_data['company_symbol']
            return step_times
    
    async def benchmark_annual_production(self, num_rows=5, user_id="1a635897d-17e6-4e3c-bd43-9b5d7f87bf0b"):
        """Benchmark annual predictions with full production database operations"""
        
        print(f"\n🏭 PRODUCTION ANNUAL PREDICTIONS BENCHMARK ({num_rows} rows)")
        print("=" * 70)
        
        # Get database session
        SessionLocal = get_session_local()
        db = SessionLocal()
        
        try:
            # Create realistic test data
            annual_data, _ = self.create_realistic_test_data(num_rows)
            
            results = []
            total_benchmark_start = time.time()
            
            print(f"Processing {num_rows} annual predictions with REAL DATABASE operations...")
            print()
            
            for i, company_data in enumerate(annual_data):
                print(f"🏭 Processing Row {i+1}/{num_rows}: {company_data['company_symbol']}")
                
                row_result = await self.process_annual_prediction_production(db, company_data, user_id)
                results.append(row_result)
                
                if row_result['success']:
                    print(f"   ✅ Success: {row_result['total']:.2f}ms total (ID: {row_result['prediction_id']})")
                    print(f"      • Company DB Lookup: {row_result['company_db']:.2f}ms")
                    print(f"      • Data Preprocessing: {row_result['preprocessing']:.2f}ms")
                    print(f"      • ML Prediction: {row_result['ml_prediction']:.2f}ms")
                    print(f"      • Database Insert: {row_result['db_insert']:.2f}ms")
                    print(f"      • Risk Score: {row_result['prediction_score']:.4f} ({row_result['risk_level']})")
                else:
                    print(f"   ❌ Failed: {row_result['error']}")
                print()
            
            # Calculate statistics
            successful_results = [r for r in results if r['success']]
            
            if successful_results:
                total_times = [r['total'] for r in successful_results]
                company_db_times = [r['company_db'] for r in successful_results]
                ml_times = [r['ml_prediction'] for r in successful_results]
                db_insert_times = [r['db_insert'] for r in successful_results]
                
                total_benchmark_time = (time.time() - total_benchmark_start) * 1000
                
                print(f"📈 ANNUAL PRODUCTION PERFORMANCE SUMMARY:")
                print(f"   • Success Rate: {len(successful_results)}/{num_rows} ({len(successful_results)/num_rows*100:.1f}%)")
                print(f"   • Average Total Time: {statistics.mean(total_times):.2f}ms per row")
                print(f"   • Average Company DB Time: {statistics.mean(company_db_times):.2f}ms per row")
                print(f"   • Average ML Time: {statistics.mean(ml_times):.2f}ms per row")
                print(f"   • Average DB Insert Time: {statistics.mean(db_insert_times):.2f}ms per row")
                print(f"   • Min/Max Total: {min(total_times):.2f}ms / {max(total_times):.2f}ms")
                print(f"   • Total Processing Time: {sum(total_times):.2f}ms for {num_rows} rows")
                print(f"   • Real Benchmark Time: {total_benchmark_time:.2f}ms (includes overhead)")
                
            return results
            
        finally:
            db.close()
    
    async def benchmark_quarterly_production(self, num_rows=5, user_id="1a635897d-17e6-4e3c-bd43-9b5d7f87bf0b"):
        """Benchmark quarterly predictions with full production database operations"""
        
        print(f"\n🏭 PRODUCTION QUARTERLY PREDICTIONS BENCHMARK ({num_rows} rows)")
        print("=" * 70)
        
        # Get database session
        SessionLocal = get_session_local()
        db = SessionLocal()
        
        try:
            # Create realistic test data
            _, quarterly_data = self.create_realistic_test_data(num_rows)
            
            results = []
            total_benchmark_start = time.time()
            
            print(f"Processing {num_rows} quarterly predictions with REAL DATABASE operations...")
            print()
            
            for i, company_data in enumerate(quarterly_data):
                print(f"🏭 Processing Row {i+1}/{num_rows}: {company_data['company_symbol']}")
                
                row_result = await self.process_quarterly_prediction_production(db, company_data, user_id)
                results.append(row_result)
                
                if row_result['success']:
                    print(f"   ✅ Success: {row_result['total']:.2f}ms total (ID: {row_result['prediction_id']})")
                    print(f"      • Company DB Lookup: {row_result['company_db']:.2f}ms")
                    print(f"      • Data Preprocessing: {row_result['preprocessing']:.2f}ms")
                    print(f"      • ML Prediction: {row_result['ml_prediction']:.2f}ms")
                    print(f"      • Database Insert: {row_result['db_insert']:.2f}ms")
                    print(f"      • Risk Score: {row_result['prediction_score']:.4f} ({row_result['risk_level']})")
                else:
                    print(f"   ❌ Failed: {row_result['error']}")
                print()
            
            # Calculate statistics
            successful_results = [r for r in results if r['success']]
            
            if successful_results:
                total_times = [r['total'] for r in successful_results]
                company_db_times = [r['company_db'] for r in successful_results]
                ml_times = [r['ml_prediction'] for r in successful_results]
                db_insert_times = [r['db_insert'] for r in successful_results]
                
                total_benchmark_time = (time.time() - total_benchmark_start) * 1000
                
                print(f"📈 QUARTERLY PRODUCTION PERFORMANCE SUMMARY:")
                print(f"   • Success Rate: {len(successful_results)}/{num_rows} ({len(successful_results)/num_rows*100:.1f}%)")
                print(f"   • Average Total Time: {statistics.mean(total_times):.2f}ms per row")
                print(f"   • Average Company DB Time: {statistics.mean(company_db_times):.2f}ms per row")
                print(f"   • Average ML Time: {statistics.mean(ml_times):.2f}ms per row")
                print(f"   • Average DB Insert Time: {statistics.mean(db_insert_times):.2f}ms per row")
                print(f"   • Min/Max Total: {min(total_times):.2f}ms / {max(total_times):.2f}ms")
                print(f"   • Total Processing Time: {sum(total_times):.2f}ms for {num_rows} rows")
                print(f"   • Real Benchmark Time: {total_benchmark_time:.2f}ms (includes overhead)")
                
            return results
            
        finally:
            db.close()
    
    def calculate_production_estimates(self, annual_results, quarterly_results):
        """Calculate realistic production file processing time estimates"""
        
        print(f"\n🚀 PRODUCTION FILE COMPLETION TIME ESTIMATES")
        print("=" * 70)
        
        # Get successful results
        annual_successful = [r for r in annual_results if r['success']]
        quarterly_successful = [r for r in quarterly_results if r['success']]
        
        if annual_successful:
            avg_annual_time = statistics.mean([r['total'] for r in annual_successful])
            avg_annual_db = statistics.mean([r['company_db'] for r in annual_successful])
            avg_annual_ml = statistics.mean([r['ml_prediction'] for r in annual_successful])
            avg_annual_insert = statistics.mean([r['db_insert'] for r in annual_successful])
            
            print(f"\n📊 ANNUAL PREDICTIONS (Production with Database):")
            print(f"   • Average total time per row: {avg_annual_time:.2f}ms")
            print(f"     - Company DB operations: {avg_annual_db:.2f}ms ({avg_annual_db/avg_annual_time*100:.1f}%)")
            print(f"     - ML prediction: {avg_annual_ml:.2f}ms ({avg_annual_ml/avg_annual_time*100:.1f}%)")
            print(f"     - Database insert: {avg_annual_insert:.2f}ms ({avg_annual_insert/avg_annual_time*100:.1f}%)")
            
            # Calculate estimates for different file sizes
            file_sizes = [5, 10, 50, 100, 500, 1000, 5000, 10000]
            print(f"\n   📈 File Processing Estimates (Sequential):")
            for size in file_sizes:
                total_time_ms = avg_annual_time * size
                total_time_sec = total_time_ms / 1000
                
                if total_time_sec < 60:
                    time_str = f"{total_time_sec:.1f} seconds"
                elif total_time_sec < 3600:
                    time_str = f"{total_time_sec/60:.1f} minutes"
                else:
                    time_str = f"{total_time_sec/3600:.1f} hours"
                
                # Calculate with 8 workers (parallel processing)
                parallel_time_sec = total_time_sec / 8
                if parallel_time_sec < 60:
                    parallel_str = f"{parallel_time_sec:.1f} seconds"
                elif parallel_time_sec < 3600:
                    parallel_str = f"{parallel_time_sec/60:.1f} minutes"
                else:
                    parallel_str = f"{parallel_time_sec/3600:.1f} hours"
                
                print(f"      {size:5d} rows: {time_str} (Sequential) | {parallel_str} (8 Workers)")
        
        if quarterly_successful:
            avg_quarterly_time = statistics.mean([r['total'] for r in quarterly_successful])
            avg_quarterly_db = statistics.mean([r['company_db'] for r in quarterly_successful])
            avg_quarterly_ml = statistics.mean([r['ml_prediction'] for r in quarterly_successful])
            avg_quarterly_insert = statistics.mean([r['db_insert'] for r in quarterly_successful])
            
            print(f"\n📊 QUARTERLY PREDICTIONS (Production with Database):")
            print(f"   • Average total time per row: {avg_quarterly_time:.2f}ms")
            print(f"     - Company DB operations: {avg_quarterly_db:.2f}ms ({avg_quarterly_db/avg_quarterly_time*100:.1f}%)")
            print(f"     - ML prediction: {avg_quarterly_ml:.2f}ms ({avg_quarterly_ml/avg_quarterly_time*100:.1f}%)")
            print(f"     - Database insert: {avg_quarterly_insert:.2f}ms ({avg_quarterly_insert/avg_quarterly_time*100:.1f}%)")
            
            # Calculate estimates for different file sizes
            file_sizes = [5, 10, 50, 100, 500, 1000, 5000, 10000]
            print(f"\n   📈 File Processing Estimates (Sequential):")
            for size in file_sizes:
                total_time_ms = avg_quarterly_time * size
                total_time_sec = total_time_ms / 1000
                
                if total_time_sec < 60:
                    time_str = f"{total_time_sec:.1f} seconds"
                elif total_time_sec < 3600:
                    time_str = f"{total_time_sec/60:.1f} minutes"
                else:
                    time_str = f"{total_time_sec/3600:.1f} hours"
                
                # Calculate with 8 workers (parallel processing)
                parallel_time_sec = total_time_sec / 8
                if parallel_time_sec < 60:
                    parallel_str = f"{parallel_time_sec:.1f} seconds"
                elif parallel_time_sec < 3600:
                    parallel_str = f"{parallel_time_sec/60:.1f} minutes"
                else:
                    parallel_str = f"{parallel_time_sec/3600:.1f} hours"
                
                print(f"      {size:5d} rows: {time_str} (Sequential) | {parallel_str} (8 Workers)")

async def main():
    """Main production benchmark execution"""
    
    print("🏭 PRODUCTION-LEVEL BENCHMARK WITH REAL DATABASE")
    print("=" * 70)
    print("Testing complete end-to-end process including database operations")
    print("Using real JWT token and production database")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # JWT token from user
    jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxYTYzNTg5ZC0xN2U2LTRlM2MtYmQ0My05YjVkN2Y4N2JmMGIiLCJleHAiOjE3NTg4MzExNDB9.f96jeFEqquPgHq1luOBv4nvbnPxhE_tBjnaoU9u6r08"
    user_id = "1a635897d-17e6-4e3c-bd43-9b5d7f87bf0b"  # Extracted from JWT
    
    # Initialize production benchmark
    benchmark = ProductionBenchmark(jwt_token=jwt_token)
    
    # Load ML models
    if not benchmark.load_ml_models():
        print("❌ Cannot proceed without ML models")
        return
    
    print()
    
    # Run production benchmarks with database operations
    annual_results = await benchmark.benchmark_annual_production(5, user_id)
    quarterly_results = await benchmark.benchmark_quarterly_production(5, user_id)
    
    # Calculate realistic production estimates
    benchmark.calculate_production_estimates(annual_results, quarterly_results)
    
    print(f"\n✅ Production benchmark completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n🎯 This benchmark includes:")
    print("   • Real database connections (Neon PostgreSQL)")
    print("   • Company creation/lookup operations")
    print("   • Complete ML prediction processing")
    print("   • Full prediction record storage")
    print("   • Production-level error handling")

if __name__ == "__main__":
    asyncio.run(main())
