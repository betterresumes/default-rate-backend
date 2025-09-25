#!/usr/bin/env python3
"""
QUICK ML PROCESSING BENCHMARK
Measures ML prediction time without database operations to get accurate processing estimates
"""

import asyncio
import time
import statistics
import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import ML services
from app.services.ml_service import MLModelService
from app.services.quarterly_ml_service import QuarterlyMLModelService

class QuickMLBenchmark:
    def __init__(self):
        self.ml_service = None
        self.quarterly_ml_service = None
        
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
            
    def create_test_data(self, num_rows=5):
        """Create test data for benchmarking"""
        
        # Annual prediction test data
        annual_data = [
            {
                'company_symbol': f'TEST{i:03d}',
                'company_name': f'Test Company {i+1}',
                'market_cap': 1000000000 + (i * 100000000),
                'sector': ['Technology', 'Healthcare', 'Finance', 'Energy', 'Consumer'][i % 5],
                'reporting_year': '2024',
                'total_debt_to_ebitda': 2.5 + (i * 0.4),
                'sga_margin': 0.20 + (i * 0.03),
                'long_term_debt_to_total_capital': 0.30 + (i * 0.05),
                'return_on_capital': 0.15 + (i * 0.02)
            }
            for i in range(num_rows)
        ]
        
        # Quarterly prediction test data
        quarterly_data = [
            {
                'company_symbol': f'QTEST{i:03d}',
                'company_name': f'Quarterly Test Company {i+1}',
                'market_cap': 800000000 + (i * 50000000),
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
        
        return annual_data, quarterly_data
    
    async def process_annual_prediction(self, row_data):
        """Process single annual prediction and measure time"""
        
        step_times = {}
        total_start = time.time()
        
        try:
            # Step 1: Data preprocessing
            step_start = time.time()
            
            # Create input data frame for ML model
            financial_ratios = {
                'total_debt_to_ebitda': row_data['total_debt_to_ebitda'],
                'sga_margin': row_data['sga_margin'], 
                'long_term_debt_to_total_capital': row_data['long_term_debt_to_total_capital'],
                'return_on_capital': row_data['return_on_capital']
            }
            
            step_times['preprocessing'] = (time.time() - step_start) * 1000
            
            # Step 2: ML Prediction
            step_start = time.time()
            
            prediction_result = await self.ml_service.predict_annual(financial_ratios)
            
            step_times['ml_prediction'] = (time.time() - step_start) * 1000
            
            # Step 3: Results processing  
            step_start = time.time()
            
            # Extract prediction results with safe handling
            prediction_score = prediction_result.get('probability', 0.0) if prediction_result else 0.0
            risk_category = prediction_result.get('risk_level', 'Unknown') if prediction_result else 'Unknown'
            
            step_times['result_processing'] = (time.time() - step_start) * 1000
            
            # Total time
            step_times['total'] = (time.time() - total_start) * 1000
            step_times['success'] = True
            step_times['company_symbol'] = row_data['company_symbol']
            step_times['prediction_score'] = prediction_score or 0.0
            step_times['risk_category'] = risk_category or 'Unknown'
            
            return step_times
            
        except Exception as e:
            step_times['total'] = (time.time() - total_start) * 1000
            step_times['success'] = False
            step_times['error'] = str(e)
            step_times['company_symbol'] = row_data['company_symbol']
            return step_times
    
    async def process_quarterly_prediction(self, row_data):
        """Process single quarterly prediction and measure time"""
        
        step_times = {}
        total_start = time.time()
        
        try:
            # Step 1: Data preprocessing
            step_start = time.time()
            
            # Create input data for quarterly model
            financial_ratios = {
                'total_debt_to_ebitda': row_data['total_debt_to_ebitda'],
                'sga_margin': row_data['sga_margin'],
                'long_term_debt_to_total_capital': row_data['long_term_debt_to_total_capital'],
                'return_on_capital': row_data['return_on_capital']
            }
            
            step_times['preprocessing'] = (time.time() - step_start) * 1000
            
            # Step 2: ML Prediction
            step_start = time.time()
            
            prediction_result = await self.quarterly_ml_service.predict_quarterly(financial_ratios)
            
            step_times['ml_prediction'] = (time.time() - step_start) * 1000
            
            # Step 3: Results processing
            step_start = time.time()
            
            # Extract prediction results with safe handling
            prediction_score = prediction_result.get('probability', 0.0) if prediction_result else 0.0
            risk_category = prediction_result.get('risk_level', 'Unknown') if prediction_result else 'Unknown'
            
            step_times['result_processing'] = (time.time() - step_start) * 1000
            
            # Total time
            step_times['total'] = (time.time() - total_start) * 1000
            step_times['success'] = True
            step_times['company_symbol'] = row_data['company_symbol']
            step_times['prediction_score'] = prediction_score or 0.0
            step_times['risk_category'] = risk_category or 'Unknown'
            
            return step_times
            
        except Exception as e:
            step_times['total'] = (time.time() - total_start) * 1000
            step_times['success'] = False
            step_times['error'] = str(e)
            step_times['company_symbol'] = row_data['company_symbol']
            return step_times
    
    async def benchmark_annual_predictions(self, num_rows=5):
        """Benchmark annual predictions"""
        
        print(f"\n🧪 BENCHMARKING ANNUAL PREDICTIONS ({num_rows} rows)")
        print("=" * 70)
        
        # Create test data
        annual_data, _ = self.create_test_data(num_rows)
        
        results = []
        total_start = time.time()
        
        print(f"Processing {num_rows} annual prediction rows...")
        print()
        
        for i, row_data in enumerate(annual_data):
            print(f"📊 Processing Row {i+1}/{num_rows}: {row_data['company_symbol']}")
            
            row_result = await self.process_annual_prediction(row_data)
            results.append(row_result)
            
            if row_result['success']:
                print(f"   ✅ Success: {row_result['total']:.2f}ms total")
                print(f"      • Preprocessing: {row_result['preprocessing']:.2f}ms")
                print(f"      • ML Prediction: {row_result['ml_prediction']:.2f}ms") 
                print(f"      • Result Processing: {row_result['result_processing']:.2f}ms")
                print(f"      • Risk Score: {row_result['prediction_score']:.4f} ({row_result['risk_category']})")
            else:
                print(f"   ❌ Failed: {row_result['error']}")
            print()
        
        # Calculate statistics
        successful_results = [r for r in results if r['success']]
        
        if successful_results:
            total_times = [r['total'] for r in successful_results]
            ml_times = [r['ml_prediction'] for r in successful_results]
            
            print(f"📈 ANNUAL PREDICTIONS PERFORMANCE SUMMARY:")
            print(f"   • Success Rate: {len(successful_results)}/{num_rows} ({len(successful_results)/num_rows*100:.1f}%)")
            print(f"   • Average Total Time: {statistics.mean(total_times):.2f}ms per row")
            print(f"   • Average ML Time: {statistics.mean(ml_times):.2f}ms per row")
            print(f"   • Min/Max Total: {min(total_times):.2f}ms / {max(total_times):.2f}ms")
            print(f"   • Total Processing Time: {sum(total_times):.2f}ms for {num_rows} rows")
            
        return results
    
    async def benchmark_quarterly_predictions(self, num_rows=5):
        """Benchmark quarterly predictions"""
        
        print(f"\n🧪 BENCHMARKING QUARTERLY PREDICTIONS ({num_rows} rows)")
        print("=" * 70)
        
        # Create test data
        _, quarterly_data = self.create_test_data(num_rows)
        
        results = []
        total_start = time.time()
        
        print(f"Processing {num_rows} quarterly prediction rows...")
        print()
        
        for i, row_data in enumerate(quarterly_data):
            print(f"📊 Processing Row {i+1}/{num_rows}: {row_data['company_symbol']}")
            
            row_result = await self.process_quarterly_prediction(row_data)
            results.append(row_result)
            
            if row_result['success']:
                print(f"   ✅ Success: {row_result['total']:.2f}ms total")
                print(f"      • Preprocessing: {row_result['preprocessing']:.2f}ms")
                print(f"      • ML Prediction: {row_result['ml_prediction']:.2f}ms")
                print(f"      • Result Processing: {row_result['result_processing']:.2f}ms")
                print(f"      • Risk Score: {row_result['prediction_score']:.4f} ({row_result['risk_category']})")
            else:
                print(f"   ❌ Failed: {row_result['error']}")
            print()
        
        # Calculate statistics
        successful_results = [r for r in results if r['success']]
        
        if successful_results:
            total_times = [r['total'] for r in successful_results]
            ml_times = [r['ml_prediction'] for r in successful_results]
            
            print(f"📈 QUARTERLY PREDICTIONS PERFORMANCE SUMMARY:")
            print(f"   • Success Rate: {len(successful_results)}/{num_rows} ({len(successful_results)/num_rows*100:.1f}%)")
            print(f"   • Average Total Time: {statistics.mean(total_times):.2f}ms per row")
            print(f"   • Average ML Time: {statistics.mean(ml_times):.2f}ms per row")
            print(f"   • Min/Max Total: {min(total_times):.2f}ms / {max(total_times):.2f}ms")
            print(f"   • Total Processing Time: {sum(total_times):.2f}ms for {num_rows} rows")
            
        return results
    
    def calculate_file_estimates(self, annual_results, quarterly_results):
        """Calculate file processing time estimates based on benchmark results"""
        
        print(f"\n🚀 FILE COMPLETION TIME ESTIMATES")
        print("=" * 70)
        
        # Get successful results
        annual_successful = [r for r in annual_results if r['success']]
        quarterly_successful = [r for r in quarterly_results if r['success']]
        
        if annual_successful:
            avg_annual_time = statistics.mean([r['total'] for r in annual_successful])
            print(f"\n📊 ANNUAL PREDICTIONS:")
            print(f"   • Average time per row: {avg_annual_time:.2f}ms")
            
            # Calculate estimates for different file sizes
            file_sizes = [5, 10, 50, 100, 500, 1000, 5000, 10000]
            for size in file_sizes:
                total_time_ms = avg_annual_time * size
                total_time_sec = total_time_ms / 1000
                
                if total_time_sec < 60:
                    time_str = f"{total_time_sec:.1f} seconds"
                elif total_time_sec < 3600:
                    time_str = f"{total_time_sec/60:.1f} minutes"
                else:
                    time_str = f"{total_time_sec/3600:.1f} hours"
                
                print(f"      {size:5d} rows: {time_str}")
        
        if quarterly_successful:
            avg_quarterly_time = statistics.mean([r['total'] for r in quarterly_successful])
            print(f"\n📊 QUARTERLY PREDICTIONS:")
            print(f"   • Average time per row: {avg_quarterly_time:.2f}ms")
            
            # Calculate estimates for different file sizes
            file_sizes = [5, 10, 50, 100, 500, 1000, 5000, 10000]
            for size in file_sizes:
                total_time_ms = avg_quarterly_time * size
                total_time_sec = total_time_ms / 1000
                
                if total_time_sec < 60:
                    time_str = f"{total_time_sec:.1f} seconds"
                elif total_time_sec < 3600:
                    time_str = f"{total_time_sec/60:.1f} minutes"
                else:
                    time_str = f"{total_time_sec/3600:.1f} hours"
                
                print(f"      {size:5d} rows: {time_str}")

async def main():
    """Main benchmark execution"""
    
    print("🚀 QUICK ML PROCESSING BENCHMARK")
    print("=" * 70)
    print("Testing ML prediction processing time without database operations")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Initialize benchmark
    benchmark = QuickMLBenchmark()
    
    # Load ML models
    if not benchmark.load_ml_models():
        print("❌ Cannot proceed without ML models")
        return
    
    print()
    
    # Run benchmarks
    annual_results = await benchmark.benchmark_annual_predictions(5)
    quarterly_results = await benchmark.benchmark_quarterly_predictions(5)
    
    # Calculate estimates
    benchmark.calculate_file_estimates(annual_results, quarterly_results)
    
    print(f"\n✅ Benchmark completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    asyncio.run(main())
