#!/usr/bin/env python3
"""
Simple test to validate quarterly data without authentication
"""

import pandas as pd
import io

def test_quarterly_data_validation():
    print("🔍 Testing quarterly data validation...")
    
    # Load the quarterly test file
    try:
        df = pd.read_excel('quarterly_upload_files/quarterly_test_10_records.xlsx')
        print(f"✅ File loaded successfully: {df.shape[0]} rows, {df.shape[1]} columns")
        
        # Check required columns for quarterly
        base_required = ['stock_symbol', 'company_name']
        quarterly_required = base_required + [
            'reporting_year', 'reporting_quarter', 'total_debt_to_ebitda', 
            'sga_margin', 'long_term_debt_to_total_capital', 'return_on_capital'
        ]
        
        print(f"📋 Required columns: {quarterly_required}")
        print(f"📋 Actual columns: {list(df.columns)}")
        
        missing_columns = [col for col in quarterly_required if col not in df.columns]
        if missing_columns:
            print(f"❌ Missing columns: {missing_columns}")
            return False
        else:
            print("✅ All required columns present")
        
        # Check data types and values
        print("\n📊 Data validation:")
        print(f"  Stock symbols: {df['stock_symbol'].nunique()} unique")
        print(f"  Companies: {df['company_name'].nunique()} unique")
        print(f"  Years: {sorted(df['reporting_year'].unique())}")
        print(f"  Quarters: {sorted(df['reporting_quarter'].unique())}")
        
        # Check for missing values
        missing_values = df[quarterly_required].isnull().sum()
        if missing_values.any():
            print(f"⚠️  Missing values found:")
            for col, count in missing_values[missing_values > 0].items():
                print(f"    {col}: {count} missing")
        else:
            print("✅ No missing values in required columns")
        
        # Test that we can serialize to the same format as the API
        print("\n🔄 Testing data serialization...")
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)
        
        # Read back to ensure it's the same
        df_test = pd.read_excel(buffer)
        if df_test.shape == df.shape:
            print("✅ Data serialization successful")
        else:
            print("❌ Data serialization failed")
            
        print("\n📈 Sample data (first 3 rows):")
        print(df.head(3)[quarterly_required].to_string())
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_quarterly_data_validation()
    if success:
        print("\n✅ Quarterly data validation passed!")
    else:
        print("\n❌ Quarterly data validation failed!")
