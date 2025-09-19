#!/usr/bin/env python3
"""
Generate Quarterly Sample Data for Bulk Upload Testing

This script creates sample quarterly financial data and saves it in Excel files
for testing the quarterly bulk upload system.
"""

import pandas as pd
import numpy as np
import random
from datetime import datetime

def generate_quarterly_sample_data():
    """Generate sample quarterly financial data"""
    
    # Sample companies
    companies = [
        {"symbol": "AAPL", "name": "Apple Inc.", "sector": "Technology"},
        {"symbol": "MSFT", "name": "Microsoft Corporation", "sector": "Technology"},
        {"symbol": "GOOGL", "name": "Alphabet Inc.", "sector": "Technology"},
        {"symbol": "AMZN", "name": "Amazon.com Inc.", "sector": "Consumer Discretionary"},
        {"symbol": "TSLA", "name": "Tesla Inc.", "sector": "Consumer Discretionary"},
        {"symbol": "META", "name": "Meta Platforms Inc.", "sector": "Technology"},
        {"symbol": "NVDA", "name": "NVIDIA Corporation", "sector": "Technology"},
        {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "sector": "Financials"},
        {"symbol": "BAC", "name": "Bank of America Corp.", "sector": "Financials"},
        {"symbol": "WMT", "name": "Walmart Inc.", "sector": "Consumer Staples"},
        {"symbol": "JNJ", "name": "Johnson & Johnson", "sector": "Healthcare"},
        {"symbol": "PG", "name": "Procter & Gamble Co.", "sector": "Consumer Staples"},
        {"symbol": "V", "name": "Visa Inc.", "sector": "Financials"},
        {"symbol": "HD", "name": "Home Depot Inc.", "sector": "Consumer Discretionary"},
        {"symbol": "UNH", "name": "UnitedHealth Group Inc.", "sector": "Healthcare"},
        {"symbol": "DIS", "name": "Walt Disney Co.", "sector": "Communication Services"},
        {"symbol": "MA", "name": "Mastercard Inc.", "sector": "Financials"},
        {"symbol": "PYPL", "name": "PayPal Holdings Inc.", "sector": "Financials"},
        {"symbol": "ADBE", "name": "Adobe Inc.", "sector": "Technology"},
        {"symbol": "NFLX", "name": "Netflix Inc.", "sector": "Communication Services"},
        {"symbol": "CRM", "name": "Salesforce Inc.", "sector": "Technology"},
        {"symbol": "INTC", "name": "Intel Corporation", "sector": "Technology"},
        {"symbol": "AMD", "name": "Advanced Micro Devices Inc.", "sector": "Technology"},
        {"symbol": "CSCO", "name": "Cisco Systems Inc.", "sector": "Technology"},
        {"symbol": "PFE", "name": "Pfizer Inc.", "sector": "Healthcare"},
        {"symbol": "KO", "name": "Coca-Cola Co.", "sector": "Consumer Staples"},
        {"symbol": "PEP", "name": "PepsiCo Inc.", "sector": "Consumer Staples"},
        {"symbol": "XOM", "name": "Exxon Mobil Corporation", "sector": "Energy"},
        {"symbol": "CVX", "name": "Chevron Corporation", "sector": "Energy"},
        {"symbol": "ABBV", "name": "AbbVie Inc.", "sector": "Healthcare"},
    ]
    
    # Generate data for multiple years and quarters
    years = [2020, 2021, 2022, 2023, 2024]
    quarters = ["Q1", "Q2", "Q3", "Q4"]
    
    data = []
    
    for company in companies:
        for year in years:
            for quarter in quarters:
                # Generate realistic quarterly financial ratios
                # These ranges are based on typical values for healthy companies
                
                record = {
                    "stock_symbol": company["symbol"],
                    "company_name": company["name"],
                    "sector": company["sector"],
                    "market_cap": random.uniform(10e9, 500e9),  # 10B to 500B
                    "reporting_year": str(year),
                    "reporting_quarter": quarter,
                    
                    # Quarterly financial ratios (4 required features)
                    "total_debt_to_ebitda": round(random.uniform(0.5, 8.0), 3),  # Lower is better
                    "sga_margin": round(random.uniform(5.0, 40.0), 3),  # SG&A as % of revenue
                    "long_term_debt_to_total_capital": round(random.uniform(10.0, 70.0), 3),  # % debt in capital structure
                    "return_on_capital": round(random.uniform(2.0, 25.0), 3),  # % return on capital
                }
                
                # Add some variation based on sector
                if company["sector"] == "Technology":
                    record["sga_margin"] = round(random.uniform(15.0, 35.0), 3)  # Higher SG&A for tech
                    record["return_on_capital"] = round(random.uniform(10.0, 30.0), 3)  # Higher returns
                elif company["sector"] == "Financials":
                    record["total_debt_to_ebitda"] = round(random.uniform(1.0, 6.0), 3)  # Different for banks
                    record["long_term_debt_to_total_capital"] = round(random.uniform(20.0, 60.0), 3)
                elif company["sector"] == "Energy":
                    record["total_debt_to_ebitda"] = round(random.uniform(1.0, 10.0), 3)  # More volatile
                    record["return_on_capital"] = round(random.uniform(5.0, 20.0), 3)
                
                data.append(record)
    
    return pd.DataFrame(data)

def split_data_into_files(df, num_files=4):
    """Split the dataframe into multiple files"""
    chunk_size = len(df) // num_files
    files_data = []
    
    for i in range(num_files):
        start_idx = i * chunk_size
        if i == num_files - 1:  # Last file gets remaining records
            end_idx = len(df)
        else:
            end_idx = (i + 1) * chunk_size
        
        chunk = df.iloc[start_idx:end_idx].copy()
        files_data.append(chunk)
    
    return files_data

def main():
    """Generate quarterly sample data and save to Excel files"""
    
    print("🏭 Generating quarterly sample data...")
    
    # Generate the sample data
    df = generate_quarterly_sample_data()
    
    print(f"✅ Generated {len(df)} quarterly records")
    print(f"📊 Companies: {df['stock_symbol'].nunique()}")
    print(f"📅 Years: {sorted(df['reporting_year'].unique())}")
    print(f"📆 Quarters: {sorted(df['reporting_quarter'].unique())}")
    print(f"🏢 Sectors: {sorted(df['sector'].unique())}")
    
    # Split into 4 files
    print("\n📁 Splitting data into 4 files...")
    files_data = split_data_into_files(df, 4)
    
    # Save to Excel files
    for i, chunk in enumerate(files_data, 1):
        filename = f"quarterly_upload_files/quarterly_predictions_part_{i}.xlsx"
        chunk.to_excel(filename, index=False)
        print(f"💾 Saved {len(chunk)} records to {filename}")
        
        # Show sample of this file
        print(f"   Sample quarters: {sorted(chunk['reporting_quarter'].unique())}")
        print(f"   Sample companies: {list(chunk['stock_symbol'].unique()[:5])}")
    
    # Save a small test file too
    test_data = df.head(10).copy()
    test_data.to_excel("quarterly_upload_files/quarterly_test_10_records.xlsx", index=False)
    print(f"\n🧪 Created test file with 10 records: quarterly_test_10_records.xlsx")
    
    print("\n📈 Sample data preview:")
    print(df[['stock_symbol', 'reporting_year', 'reporting_quarter', 
              'total_debt_to_ebitda', 'sga_margin', 'long_term_debt_to_total_capital', 
              'return_on_capital']].head())
    
    print(f"\n✅ Quarterly sample data generation complete!")
    print(f"📂 Files saved in: quarterly_upload_files/")

if __name__ == "__main__":
    main()
