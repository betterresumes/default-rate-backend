#!/usr/bin/env python3
"""
Create test Excel files for bulk upload testing
"""

import pandas as pd
import random

def create_annual_prediction_data(num_stocks):
    """Create test data for annual predictions"""
    
    # Sample companies data
    companies = [
        {"symbol": "AAPL", "name": "Apple Inc.", "sector": "Technology"},
        {"symbol": "MSFT", "name": "Microsoft Corporation", "sector": "Technology"},
        {"symbol": "GOOGL", "name": "Alphabet Inc.", "sector": "Technology"},
        {"symbol": "AMZN", "name": "Amazon.com Inc.", "sector": "E-commerce"},
        {"symbol": "TSLA", "name": "Tesla Inc.", "sector": "Automotive"},
        {"symbol": "META", "name": "Meta Platforms Inc.", "sector": "Technology"},
        {"symbol": "NVDA", "name": "NVIDIA Corporation", "sector": "Technology"},
        {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "sector": "Financial"},
        {"symbol": "JNJ", "name": "Johnson & Johnson", "sector": "Healthcare"},
        {"symbol": "V", "name": "Visa Inc.", "sector": "Financial"},
        {"symbol": "PG", "name": "Procter & Gamble Co.", "sector": "Consumer Goods"},
        {"symbol": "HD", "name": "The Home Depot Inc.", "sector": "Retail"},
        {"symbol": "UNH", "name": "UnitedHealth Group Inc.", "sector": "Healthcare"},
        {"symbol": "MA", "name": "Mastercard Inc.", "sector": "Financial"},
        {"symbol": "BAC", "name": "Bank of America Corp.", "sector": "Financial"}
    ]
    
    data = []
    for i in range(num_stocks):
        company = companies[i % len(companies)]
        
        # Generate realistic financial ratios
        row = {
            "company_symbol": company["symbol"],
            "company_name": company["name"],
            "market_cap": round(random.uniform(10000, 3000000), 2),  # 10B to 3T
            "sector": company["sector"],
            "reporting_year": "2024",
            "reporting_quarter": None,  # Annual prediction
            "long_term_debt_to_total_capital": round(random.uniform(5.0, 60.0), 2),
            "total_debt_to_ebitda": round(random.uniform(0.5, 8.0), 2),
            "net_income_margin": round(random.uniform(-5.0, 35.0), 2),
            "ebit_to_interest_expense": round(random.uniform(2.0, 25.0), 2),
            "return_on_assets": round(random.uniform(-2.0, 20.0), 2)
        }
        data.append(row)
    
    return data

def main():
    """Create test Excel files"""
    
    # Create 5-stock file
    print("📊 Creating 5-stock test file...")
    data_5 = create_annual_prediction_data(5)
    df_5 = pd.DataFrame(data_5)
    df_5.to_excel("annual_predictions_5_stocks.xlsx", index=False)
    print("✅ Created: annual_predictions_5_stocks.xlsx")
    
    # Create 10-stock file  
    print("📊 Creating 10-stock test file...")
    data_10 = create_annual_prediction_data(10)
    df_10 = pd.DataFrame(data_10)
    df_10.to_excel("annual_predictions_10_stocks.xlsx", index=False)
    print("✅ Created: annual_predictions_10_stocks.xlsx")
    
    # Display sample data
    print("\n📋 Sample data (first 3 rows):")
    print(df_5.head(3).to_string())
    
    print("\n📝 Column Summary:")
    print(f"Total columns: {len(df_5.columns)}")
    print("Columns:", list(df_5.columns))

if __name__ == "__main__":
    main()
