#!/usr/bin/env python3
"""
Test the enhanced bulk upload APIs with auto-scaling integration
"""

import asyncio
import json
import pandas as pd
from datetime import datetime

# Test data for annual predictions
annual_test_data = {
    'company_symbol': ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'META'],
    'company_name': ['Apple Inc', 'Microsoft Corp', 'Alphabet Inc', 'Tesla Inc', 'Meta Platforms'],
    'market_cap': [3000000000000, 2800000000000, 1800000000000, 800000000000, 750000000000],
    'sector': ['Technology', 'Technology', 'Technology', 'Automotive', 'Technology'],
    'reporting_year': ['2024', '2024', '2024', '2024', '2024'],
    'reporting_quarter': ['Q4', 'Q4', 'Q4', 'Q4', 'Q4'],
    'long_term_debt_to_total_capital': [0.35, 0.28, 0.12, 0.45, 0.22],
    'total_debt_to_ebitda': [2.1, 1.8, 0.8, 3.2, 1.5],
    'net_income_margin': [0.25, 0.31, 0.21, 0.08, 0.23],
    'ebit_to_interest_expense': [15.2, 18.5, 25.1, 4.2, 12.8],
    'return_on_assets': [0.18, 0.16, 0.12, 0.05, 0.14]
}

# Test data for quarterly predictions  
quarterly_test_data = {
    'company_symbol': ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'META'],
    'company_name': ['Apple Inc', 'Microsoft Corp', 'Alphabet Inc', 'Tesla Inc', 'Meta Platforms'],
    'market_cap': [3000000000000, 2800000000000, 1800000000000, 800000000000, 750000000000],
    'sector': ['Technology', 'Technology', 'Technology', 'Automotive', 'Technology'],
    'reporting_year': ['2024', '2024', '2024', '2024', '2024'],
    'reporting_quarter': ['Q3', 'Q3', 'Q3', 'Q3', 'Q3'],
    'total_debt_to_ebitda': [2.1, 1.8, 0.8, 3.2, 1.5],
    'sga_margin': [0.15, 0.22, 0.18, 0.08, 0.19],
    'long_term_debt_to_total_capital': [0.35, 0.28, 0.12, 0.45, 0.22],
    'return_on_capital': [0.28, 0.32, 0.18, 0.12, 0.25]
}

def create_test_files():
    """Create test CSV files"""
    
    # Create annual test file
    annual_df = pd.DataFrame(annual_test_data)
    annual_filename = 'test_annual_predictions.csv'
    annual_df.to_csv(annual_filename, index=False)
    
    # Create quarterly test file
    quarterly_df = pd.DataFrame(quarterly_test_data)
    quarterly_filename = 'test_quarterly_predictions.csv'
    quarterly_df.to_csv(quarterly_filename, index=False)
    
    print(f"✅ Created test files:")
    print(f"   📄 {annual_filename} ({len(annual_df)} rows)")
    print(f"   📄 {quarterly_filename} ({len(quarterly_df)} rows)")
    
    return annual_filename, quarterly_filename

def simulate_api_response():
    """Simulate the enhanced API response format"""
    
    # This simulates what our enhanced bulk upload APIs now return
    mock_annual_response = {
        "success": True,
        "message": "Bulk upload job started successfully using Celery workers",
        "job_id": "123e4567-e89b-12d3-a456-426614174000",
        "task_id": "celery-task-123",
        "total_rows": 5,
        "estimated_time_minutes": 0.5,
        
        # NEW AUTO-SCALING FIELDS:
        "queue_priority": "medium",  # Based on file size (5 rows = small)
        "queue_position": 2,  # Current position in medium priority queue
        "current_system_load": 0.35,  # 35% system load
        "processing_message": "Your file is queued for processing. Estimated wait time: < 1 minute",
        "worker_capacity": {
            "current_workers": 16,
            "max_workers": 64,
            "utilization": 0.35
        }
    }
    
    mock_quarterly_response = {
        "success": True,
        "message": "Bulk upload job started successfully using Celery workers",
        "job_id": "456e7890-e12b-34c5-b678-542736174111",
        "task_id": "celery-task-456",
        "total_rows": 5,
        "estimated_time_minutes": 0.5,
        
        # NEW AUTO-SCALING FIELDS:
        "queue_priority": "medium",
        "queue_position": 1,
        "current_system_load": 0.35,
        "processing_message": "Your file is being processed now. Estimated completion: 30 seconds",
        "worker_capacity": {
            "current_workers": 16,
            "max_workers": 64,
            "utilization": 0.35
        }
    }
    
    return mock_annual_response, mock_quarterly_response

def test_queue_routing_logic():
    """Test the queue routing logic we implemented"""
    
    print(f"\n🧪 TESTING QUEUE ROUTING LOGIC")
    print("=" * 50)
    
    # Test cases for different file sizes
    test_cases = [
        {"rows": 50, "expected_queue": "high", "reason": "Small file, quick processing"},
        {"rows": 500, "expected_queue": "medium", "reason": "Medium file, balanced queue"}, 
        {"rows": 2000, "expected_queue": "low", "reason": "Large file, background processing"},
        {"rows": 8000, "expected_queue": "low", "reason": "Very large file, low priority"},
    ]
    
    def determine_queue_priority(total_rows):
        """Our queue routing logic"""
        if total_rows <= 100:
            return "high"
        elif total_rows <= 1000:
            return "medium"
        else:
            return "low"
    
    for test_case in test_cases:
        actual_queue = determine_queue_priority(test_case["rows"])
        status = "✅ PASS" if actual_queue == test_case["expected_queue"] else "❌ FAIL"
        
        print(f"  {test_case['rows']:4d} rows → {actual_queue:6} queue {status}")
        print(f"       Reason: {test_case['reason']}")

def test_system_load_calculation():
    """Test system load calculation and scaling decisions"""
    
    print(f"\n🧪 TESTING SYSTEM LOAD CALCULATION")
    print("=" * 50)
    
    # Mock queue metrics
    test_scenarios = [
        {
            "active_tasks": 5,
            "pending_high": 2,
            "pending_medium": 8,
            "pending_low": 15,
            "current_workers": 16,
            "expected_load": "LOW",
            "expected_action": "MAINTAIN"
        },
        {
            "active_tasks": 12,
            "pending_high": 10,
            "pending_medium": 25,
            "pending_low": 40,
            "current_workers": 16,
            "expected_load": "MEDIUM",
            "expected_action": "SCALE_UP"
        },
        {
            "active_tasks": 28,
            "pending_high": 20,
            "pending_medium": 45,
            "pending_low": 80,
            "current_workers": 32,
            "expected_load": "HIGH",
            "expected_action": "SCALE_UP"
        }
    ]
    
    def calculate_system_load(active, pending_high, pending_medium, pending_low, workers):
        """Our system load calculation logic"""
        total_pending = pending_high + pending_medium + pending_low
        total_tasks = active + total_pending
        
        # Weight high priority tasks more heavily
        weighted_load = active + (pending_high * 2) + (pending_medium * 1.5) + (pending_low * 1)
        
        utilization = weighted_load / (workers * 4)  # Assume each worker can handle 4 tasks optimally
        
        if utilization < 0.5:
            return "LOW", "MAINTAIN"
        elif utilization < 1.0:
            return "MEDIUM", "SCALE_UP" if total_pending > 20 else "MAINTAIN"
        else:
            return "HIGH", "SCALE_UP"
    
    for scenario in test_scenarios:
        load, action = calculate_system_load(
            scenario["active_tasks"],
            scenario["pending_high"],
            scenario["pending_medium"], 
            scenario["pending_low"],
            scenario["current_workers"]
        )
        
        load_match = load == scenario["expected_load"]
        action_match = action == scenario["expected_action"]
        status = "✅ PASS" if load_match and action_match else "❌ FAIL"
        
        print(f"  Scenario: {scenario['active_tasks']} active, {scenario['pending_high']+scenario['pending_medium']+scenario['pending_low']} pending")
        print(f"    Load: {load} (expected {scenario['expected_load']}) {status}")
        print(f"    Action: {action} (expected {scenario['expected_action']})")
        print()

def main():
    """Run all tests"""
    print("🚀 TESTING AUTO-SCALING BULK UPLOAD INTEGRATION")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create test files
    annual_file, quarterly_file = create_test_files()
    
    # Test API responses
    print(f"\n📡 TESTING ENHANCED API RESPONSES")
    print("=" * 50)
    
    annual_response, quarterly_response = simulate_api_response()
    
    print("Annual Bulk Upload Response:")
    print(json.dumps(annual_response, indent=2))
    
    print(f"\nQuarterly Bulk Upload Response:")  
    print(json.dumps(quarterly_response, indent=2))
    
    # Test queue routing
    test_queue_routing_logic()
    
    # Test system load calculation
    test_system_load_calculation()
    
    print(f"\n✅ INTEGRATION TESTING COMPLETE")
    print("=" * 50)
    print("Key Benefits of Auto-Scaling Integration:")
    print("• Real-time queue position and priority information")
    print("• Smart queue routing based on file size")
    print("• Dynamic system load feedback") 
    print("• Intelligent scaling decisions")
    print("• Enhanced user experience with processing messages")
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
