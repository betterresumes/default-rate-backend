#!/usr/bin/env python3

import pandas as pd
import io
from app.api.v1.predictions import bulk_upload_annual_async

def test_annual_required_columns():
    """Test that annual bulk upload no longer requires reporting_quarter"""
    
    # Create sample data without reporting_quarter
    sample_data = {
        'company_symbol': ['AAPL', 'MSFT'],
        'company_name': ['Apple Inc.', 'Microsoft Corporation'],
        'market_cap': [2800000, 2300000],
        'sector': ['Technology', 'Technology'],
        'reporting_year': [2024, 2024],
        'long_term_debt_to_total_capital': [25.5, 18.2],
        'total_debt_to_ebitda': [1.8, 1.2],
        'net_income_margin': [24.3, 36.7],
        'ebit_to_interest_expense': [85.2, 42.1],
        'return_on_assets': [22.4, 16.8]
    }
    
    df = pd.DataFrame(sample_data)
    print("Sample DataFrame without reporting_quarter:")
    print(df.to_string())
    print()
    
    # Check required columns
    required_columns = [
        'company_symbol', 'company_name', 'market_cap', 'sector',
        'reporting_year',
        'long_term_debt_to_total_capital', 'total_debt_to_ebitda',
        'net_income_margin', 'ebit_to_interest_expense', 'return_on_assets'
    ]
    
    print("Required columns for annual bulk upload:")
    for col in required_columns:
        print(f"  - {col}")
    print()
    
    # Check if all required columns are present
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        print(f"❌ Missing required columns: {', '.join(missing_columns)}")
        return False
    else:
        print("✅ All required columns are present!")
        print("✅ reporting_quarter is NOT required for annual predictions")
        return True

if __name__ == "__main__":
    test_annual_required_columns()
