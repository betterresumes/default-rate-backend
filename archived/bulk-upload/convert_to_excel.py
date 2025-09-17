#!/usr/bin/env python3
"""
Convert annual_step.pkl to Excel files for bulk-upload-async endpoint
Creates 4 Excel files with ~2,500 records each
"""

import os
import sys
import pickle
import pandas as pd
import numpy as np
from pathlib import Path

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

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

def convert_annual_step_to_excel():
    """Convert annual_step.pkl to Excel files for bulk upload"""
    
    print("🔄 Converting annual_step.pkl to Excel files...")
    
    # Load data
    print("📊 Loading annual_step.pkl...")
    with open('src/models/annual_step.pkl', 'rb') as f:
        data = pickle.load(f)
    
    print(f"✅ Loaded {len(data):,} records")
    
    # Create output directory
    output_dir = Path('bulk_upload_files')
    output_dir.mkdir(exist_ok=True)
    
    # Convert to required format for annual predictions
    print("🔄 Converting to bulk upload format...")
    
    converted_data = []
    skipped = 0
    
    for idx, (_, row) in enumerate(data.iterrows()):
        try:
            # Get basic company info
            ticker = str(row.get('ticker', '')).strip().upper()
            company_name = str(row.get('company name', '')).strip()
            industry = str(row.get('Industry', '')).strip()
            fiscal_year = row.get('fy')
            
            # Skip if no ticker
            if not ticker or ticker in ['NAN', '']:
                skipped += 1
                continue
            
            # Clean company name
            if not company_name or company_name in ['NAN', '']:
                company_name = ticker
            
            # Clean sector - use "Other" if null or empty
            sector = industry if industry and industry.lower() not in ['', 'nan', 'none', 'null'] else "Other"
            
            # Clean financial ratios
            long_term_debt_to_total_capital = clean_financial_value(row.get('long-term debt / total capital (%)'))
            total_debt_to_ebitda = clean_financial_value(row.get('total debt / ebitda'))
            net_income_margin = clean_financial_value(row.get('net income margin'))
            ebit_to_interest_expense = clean_financial_value(row.get('ebit / interest expense'))
            return_on_assets = clean_financial_value(row.get('return on assets'))
            
            # Check if we have at least one valid ratio
            valid_ratios = sum(1 for v in [long_term_debt_to_total_capital, total_debt_to_ebitda, 
                                         net_income_margin, ebit_to_interest_expense, return_on_assets] 
                             if v is not None)
            
            if valid_ratios == 0:
                skipped += 1
                continue
            
            # Create record in required format
            record = {
                'stock_symbol': ticker,
                'company_name': company_name,
                'market_cap': 100,  # $100 million as requested
                'sector': sector,
                'reporting_year': str(int(fiscal_year)) if not pd.isna(fiscal_year) else "2024",
                'reporting_quarter': "Q4",  # Fixed as requested
                'long_term_debt_to_total_capital': long_term_debt_to_total_capital,
                'total_debt_to_ebitda': total_debt_to_ebitda,
                'net_income_margin': net_income_margin,
                'ebit_to_interest_expense': ebit_to_interest_expense,
                'return_on_assets': return_on_assets
            }
            
            converted_data.append(record)
            
        except Exception as e:
            print(f"⚠️ Error processing record {idx}: {e}")
            skipped += 1
            continue
    
    print(f"✅ Converted {len(converted_data):,} records, skipped {skipped:,}")
    
    # Create DataFrame
    df = pd.DataFrame(converted_data)
    
    # Split into 4 equal parts
    total_records = len(df)
    records_per_file = total_records // 4
    
    print(f"📄 Splitting into 4 files (~{records_per_file:,} records each)...")
    
    files_created = []
    
    for i in range(4):
        start_idx = i * records_per_file
        if i == 3:  # Last file gets remaining records
            end_idx = total_records
        else:
            end_idx = (i + 1) * records_per_file
        
        chunk_df = df.iloc[start_idx:end_idx].copy()
        
        # Create filename
        filename = f"annual_predictions_part_{i+1}.xlsx"
        filepath = output_dir / filename
        
        # Save to Excel
        chunk_df.to_excel(filepath, index=False)
        
        files_created.append(filepath)
        
        print(f"✅ Created {filename}: {len(chunk_df):,} records")
        
        # Show sample of data
        print(f"   Sample companies: {', '.join(chunk_df['stock_symbol'].head(3).tolist())}")
        print(f"   Year range: {chunk_df['reporting_year'].min()} - {chunk_df['reporting_year'].max()}")
        print(f"   Sectors: {len(chunk_df['sector'].unique())} unique")
    
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    print(f"✅ Total records processed: {len(converted_data):,}")
    print(f"📄 Files created: {len(files_created)}")
    print(f"📁 Output directory: {output_dir.absolute()}")
    print()
    
    for i, filepath in enumerate(files_created, 1):
        file_size = filepath.stat().st_size / 1024 / 1024  # MB
        print(f"📄 {filepath.name}: {file_size:.1f} MB")
    
    print("\n🚀 NEXT STEPS:")
    print("="*60)
    print("1. Start your FastAPI server:")
    print("   uvicorn src.app:app --reload")
    print()
    print("2. Upload files using the bulk-upload-async endpoint:")
    print("   POST /api/predictions/bulk-predict-async")
    print("   - File: Select one of the Excel files")
    print("   - prediction_type: annual")
    print()
    print("3. Upload files in sequence with delays:")
    print("   - Upload part_1.xlsx")
    print("   - Wait 30 seconds")
    print("   - Upload part_2.xlsx")
    print("   - Wait 30 seconds")
    print("   - Upload part_3.xlsx")
    print("   - Wait 30 seconds")
    print("   - Upload part_4.xlsx")
    print()
    print("✅ All files ready for bulk upload!")
    
    return files_created

def verify_excel_format():
    """Verify the Excel files have the correct format"""
    print("\n🔍 VERIFYING EXCEL FORMAT...")
    
    required_columns = [
        'stock_symbol', 'company_name', 'long_term_debt_to_total_capital',
        'total_debt_to_ebitda', 'net_income_margin', 'ebit_to_interest_expense', 'return_on_assets'
    ]
    
    output_dir = Path('bulk_upload_files')
    excel_files = list(output_dir.glob('*.xlsx'))
    
    for filepath in excel_files:
        print(f"\n📄 Checking {filepath.name}:")
        
        try:
            df = pd.read_excel(filepath)
            
            # Check columns
            missing_cols = [col for col in required_columns if col not in df.columns]
            if missing_cols:
                print(f"   ❌ Missing columns: {missing_cols}")
            else:
                print(f"   ✅ All required columns present")
            
            # Check data
            print(f"   📊 Records: {len(df):,}")
            print(f"   🏢 Unique companies: {df['stock_symbol'].nunique()}")
            print(f"   📅 Years: {df['reporting_year'].nunique()} unique")
            print(f"   🏭 Sectors: {df['sector'].nunique()} unique")
            
            # Check for null values in required fields
            null_symbols = df['stock_symbol'].isna().sum()
            null_names = df['company_name'].isna().sum()
            
            if null_symbols > 0:
                print(f"   ⚠️ Null stock_symbols: {null_symbols}")
            if null_names > 0:
                print(f"   ⚠️ Null company_names: {null_names}")
            
            if null_symbols == 0 and null_names == 0:
                print(f"   ✅ No null values in required fields")
            
        except Exception as e:
            print(f"   ❌ Error reading file: {e}")
    
    print("\n✅ Format verification complete!")

if __name__ == "__main__":
    # Convert data
    files_created = convert_annual_step_to_excel()
    
    # Verify format
    verify_excel_format()
    
    print("\n🎉 Conversion complete! Ready for bulk upload!")
