#!/usr/bin/env python3
"""
Performance Testing Script for Prediction Processing
Tests processing time for single rows to estimate bulk upload performance
"""

import asyncio
import time
import statistics
import pandas as pd
import uuid
from datetime import datetime
import sys
import os

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.ml_service import ml_model
from app.services.quarterly_ml_service import quarterly_ml_model

class PerformanceTester:
    def __init__(self):
        self.results = {
            'annual': [],
            'quarterly': []
        }
    
    async def test_annual_prediction(self, iterations=10):
        """Test annual prediction processing time"""
        print(f"\n🧪 Testing Annual Predictions ({iterations} iterations)")
        print("=" * 50)
        
        # Sample annual data
        annual_data = {
            'long_term_debt_to_total_capital': 0.35,
            'total_debt_to_ebitda': 2.5,
            'net_income_margin': 0.08,
            'ebit_to_interest_expense': 4.2,
            'return_on_assets': 0.06
        }
        
        times = []
        
        for i in range(iterations):
            start_time = time.time()
            
            try:
                result = await ml_model.predict_annual(annual_data)
                end_time = time.time()
                
                processing_time = (end_time - start_time) * 1000  # Convert to milliseconds
                times.append(processing_time)
                
                print(f"  Iteration {i+1:2d}: {processing_time:6.2f}ms - {result['risk_level']} ({result['probability']:.3f})")
                
            except Exception as e:
                print(f"  Iteration {i+1:2d}: ERROR - {str(e)}")
                continue
        
        if times:
            avg_time = statistics.mean(times)
            median_time = statistics.median(times)
            min_time = min(times)
            max_time = max(times)
            std_dev = statistics.stdev(times) if len(times) > 1 else 0
            
            self.results['annual'] = {
                'times': times,
                'avg_ms': avg_time,
                'median_ms': median_time,
                'min_ms': min_time,
                'max_ms': max_time,
                'std_dev_ms': std_dev,
                'iterations': len(times)
            }
            
            print(f"\n📊 Annual Prediction Statistics:")
            print(f"  Average Time: {avg_time:6.2f}ms")
            print(f"  Median Time:  {median_time:6.2f}ms")
            print(f"  Min Time:     {min_time:6.2f}ms")
            print(f"  Max Time:     {max_time:6.2f}ms")
            print(f"  Std Dev:      {std_dev:6.2f}ms")
            print(f"  Rows/Second:  {1000/avg_time:.2f}")
    
    async def test_quarterly_prediction(self, iterations=10):
        """Test quarterly prediction processing time"""
        print(f"\n🧪 Testing Quarterly Predictions ({iterations} iterations)")
        print("=" * 50)
        
        # Sample quarterly data
        quarterly_data = {
            'total_debt_to_ebitda': 3.2,
            'sga_margin': 0.25,
            'long_term_debt_to_total_capital': 0.40,
            'return_on_capital': 0.12
        }
        
        times = []
        
        for i in range(iterations):
            start_time = time.time()
            
            try:
                result = await quarterly_ml_model.predict_quarterly(quarterly_data)
                end_time = time.time()
                
                processing_time = (end_time - start_time) * 1000  # Convert to milliseconds
                times.append(processing_time)
                
                print(f"  Iteration {i+1:2d}: {processing_time:6.2f}ms - {result['risk_level']} (ensemble: {result.get('ensemble_probability', 0):.3f})")
                
            except Exception as e:
                print(f"  Iteration {i+1:2d}: ERROR - {str(e)}")
                continue
        
        if times:
            avg_time = statistics.mean(times)
            median_time = statistics.median(times)
            min_time = min(times)
            max_time = max(times)
            std_dev = statistics.stdev(times) if len(times) > 1 else 0
            
            self.results['quarterly'] = {
                'times': times,
                'avg_ms': avg_time,
                'median_ms': median_time,
                'min_ms': min_time,
                'max_ms': max_time,
                'std_dev_ms': std_dev,
                'iterations': len(times)
            }
            
            print(f"\n📊 Quarterly Prediction Statistics:")
            print(f"  Average Time: {avg_time:6.2f}ms")
            print(f"  Median Time:  {median_time:6.2f}ms")
            print(f"  Min Time:     {min_time:6.2f}ms")
            print(f"  Max Time:     {max_time:6.2f}ms")
            print(f"  Std Dev:      {std_dev:6.2f}ms")
            print(f"  Rows/Second:  {1000/avg_time:.2f}")
    
    def calculate_bulk_estimates(self):
        """Calculate estimates for bulk processing"""
        print(f"\n🚀 BULK PROCESSING ESTIMATES")
        print("=" * 60)
        
        file_sizes = [1000, 5000, 10000]
        
        for pred_type in ['annual', 'quarterly']:
            if pred_type not in self.results or not self.results[pred_type]:
                continue
                
            result = self.results[pred_type]
            avg_time_ms = result['avg_ms']
            rows_per_second = 1000 / avg_time_ms
            
            print(f"\n📈 {pred_type.title()} Prediction Estimates:")
            print(f"  Single Row Processing: {avg_time_ms:.2f}ms ({rows_per_second:.2f} rows/sec)")
            
            for file_size in file_sizes:
                # Sequential processing time
                sequential_time_seconds = (file_size * avg_time_ms) / 1000
                sequential_minutes = sequential_time_seconds / 60
                
                # Parallel processing with different worker counts
                worker_configs = [1, 4, 8, 16]
                
                print(f"\n  📁 File Size: {file_size:,} rows")
                print(f"    Sequential: {sequential_minutes:.1f} minutes ({sequential_time_seconds:.1f}s)")
                
                for workers in worker_configs:
                    # Assume 90% efficiency due to overhead
                    parallel_time_seconds = (sequential_time_seconds / workers) * 1.1
                    parallel_minutes = parallel_time_seconds / 60
                    
                    if parallel_minutes < 1:
                        time_str = f"{parallel_time_seconds:.1f}s"
                    else:
                        time_str = f"{parallel_minutes:.1f}min"
                    
                    effective_rps = file_size / parallel_time_seconds
                    
                    print(f"    {workers:2d} Workers: {time_str:>8} ({effective_rps:.1f} rows/sec)")
    
    def generate_performance_report(self):
        """Generate comprehensive performance report"""
        print(f"\n📋 PERFORMANCE SUMMARY REPORT")
        print("=" * 60)
        
        report_data = []
        
        for pred_type in ['annual', 'quarterly']:
            if pred_type in self.results and self.results[pred_type]:
                result = self.results[pred_type]
                report_data.append({
                    'Type': pred_type.title(),
                    'Avg Time (ms)': f"{result['avg_ms']:.2f}",
                    'Rows/Second': f"{1000/result['avg_ms']:.2f}",
                    'Min Time (ms)': f"{result['min_ms']:.2f}",
                    'Max Time (ms)': f"{result['max_ms']:.2f}",
                    'Std Dev (ms)': f"{result['std_dev_ms']:.2f}",
                    'Iterations': result['iterations']
                })
        
        if report_data:
            df = pd.DataFrame(report_data)
            print(df.to_string(index=False))
            
            # Save to CSV for analysis
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_filename = f"performance_results_{timestamp}.csv"
            df.to_csv(csv_filename, index=False)
            print(f"\n💾 Results saved to: {csv_filename}")
    
    async def run_full_test(self, iterations=20):
        """Run complete performance test suite"""
        print("🚀 PREDICTION PERFORMANCE TESTING")
        print("=" * 60)
        print(f"Testing with {iterations} iterations each")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Test annual predictions
        await self.test_annual_prediction(iterations)
        
        # Test quarterly predictions  
        await self.test_quarterly_prediction(iterations)
        
        # Calculate bulk estimates
        self.calculate_bulk_estimates()
        
        # Generate report
        self.generate_performance_report()
        
        print(f"\n✅ Testing completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

async def main():
    """Main function to run performance tests"""
    tester = PerformanceTester()
    
    # Run with 20 iterations for good statistical significance
    await tester.run_full_test(iterations=20)

if __name__ == "__main__":
    asyncio.run(main())
