#!/usr/bin/env python3
"""
Generate test data files for performance testing bulk upload APIs
"""

import pandas as pd
import numpy as np
import random
from pathlib import Path

# Set random seed for reproducible data
np.random.seed(42)
random.seed(42)

# Sample companies data
companies_data = [
    ('AAPL', 'Apple Inc', 'Technology', 3000000000000),
    ('MSFT', 'Microsoft Corporation', 'Technology', 2800000000000),
    ('GOOGL', 'Alphabet Inc', 'Technology', 1800000000000),
    ('AMZN', 'Amazon.com Inc', 'Consumer Discretionary', 1600000000000),
    ('TSLA', 'Tesla Inc', 'Consumer Discretionary', 800000000000),
    ('META', 'Meta Platforms Inc', 'Technology', 750000000000),
    ('NVDA', 'NVIDIA Corporation', 'Technology', 1200000000000),
    ('JPM', 'JPMorgan Chase & Co', 'Financials', 450000000000),
    ('JNJ', 'Johnson & Johnson', 'Healthcare', 420000000000),
    ('V', 'Visa Inc', 'Financials', 480000000000),
    ('WMT', 'Walmart Inc', 'Consumer Staples', 400000000000),
    ('PG', 'Procter & Gamble', 'Consumer Staples', 360000000000),
    ('UNH', 'UnitedHealth Group', 'Healthcare', 500000000000),
    ('HD', 'Home Depot Inc', 'Consumer Discretionary', 320000000000),
    ('MA', 'Mastercard Inc', 'Financials', 350000000000),
    ('BAC', 'Bank of America', 'Financials', 280000000000),
    ('ABBV', 'AbbVie Inc', 'Healthcare', 260000000000),
    ('PFE', 'Pfizer Inc', 'Healthcare', 240000000000),
    ('KO', 'Coca-Cola Company', 'Consumer Staples', 250000000000),
    ('PEP', 'PepsiCo Inc', 'Consumer Staples', 230000000000),
    ('TMO', 'Thermo Fisher Scientific', 'Healthcare', 220000000000),
    ('COST', 'Costco Wholesale', 'Consumer Staples', 210000000000),
    ('AVGO', 'Broadcom Inc', 'Technology', 290000000000),
    ('XOM', 'Exxon Mobil Corporation', 'Energy', 200000000000),
    ('NKE', 'Nike Inc', 'Consumer Discretionary', 190000000000),
]

def generate_financial_metrics():
    """Generate realistic financial metrics"""
    return {
        'long_term_debt_to_total_capital': np.random.uniform(0.1, 0.6),
        'total_debt_to_ebitda': np.random.uniform(0.5, 4.0),
        'net_income_margin': np.random.uniform(0.02, 0.25),
        'ebit_to_interest_expense': np.random.uniform(2.0, 15.0),
        'return_on_assets': np.random.uniform(0.02, 0.20),
    }

def generate_quarterly_metrics():
    """Generate realistic quarterly financial metrics"""
    return {
        'total_debt_to_ebitda': np.random.uniform(0.5, 4.0),
        'sga_margin': np.random.uniform(0.05, 0.30),
        'long_term_debt_to_total_capital': np.random.uniform(0.1, 0.6),
        'return_on_capital': np.random.uniform(0.05, 0.25),
    }

def create_annual_test_data(num_rows: int, filename: str):
    """Create annual predictions test data"""
    data = []
    
    for i in range(num_rows):
        company = random.choice(companies_data)
        metrics = generate_financial_metrics()
        
        row = {
            'company_symbol': company[0],
            'company_name': company[1],
            'sector': company[2],
            'market_cap': company[3] + random.randint(-50000000000, 50000000000),  # Add some variation
            'reporting_year': random.choice([2022, 2023, 2024]),
            **metrics
        }
        data.append(row)
    
    df = pd.DataFrame(data)
    output_path = f"test_data/{filename}"
    df.to_excel(output_path, index=False)
    print(f"Created {output_path} with {num_rows} rows")
    return output_path

def create_quarterly_test_data(num_rows: int, filename: str):
    """Create quarterly predictions test data"""
    data = []
    
    for i in range(num_rows):
        company = random.choice(companies_data)
        metrics = generate_quarterly_metrics()
        
        row = {
            'company_symbol': company[0],
            'company_name': company[1],
            'sector': company[2],
            'market_cap': company[3] + random.randint(-50000000000, 50000000000),  # Add some variation
            'reporting_year': random.choice([2022, 2023, 2024]),
            'reporting_quarter': random.choice([1, 2, 3, 4]),
            **metrics
        }
        data.append(row)
    
    df = pd.DataFrame(data)
    output_path = f"test_data/{filename}"
    df.to_excel(output_path, index=False)
    print(f"Created {output_path} with {num_rows} rows")
    return output_path

def main():
    """Generate all test data files"""
    print("Generating test data files for performance testing...")
    
    # Create test data directory
    Path("test_data").mkdir(exist_ok=True)
    
    # Generate annual test files
    annual_files = [
        (10, "annual_test_10_rows.xlsx"),
        (20, "annual_test_20_rows.xlsx"),
        (50, "annual_test_50_rows.xlsx"),
        (100, "annual_test_100_rows.xlsx"),
    ]
    
    # Generate quarterly test files
    quarterly_files = [
        (10, "quarterly_test_10_rows.xlsx"),
        (20, "quarterly_test_20_rows.xlsx"),
        (50, "quarterly_test_50_rows.xlsx"),
        (100, "quarterly_test_100_rows.xlsx"),
    ]
    
    print("\n=== GENERATING ANNUAL TEST DATA ===")
    annual_paths = []
    for rows, filename in annual_files:
        path = create_annual_test_data(rows, filename)
        annual_paths.append((rows, path))
    
    print("\n=== GENERATING QUARTERLY TEST DATA ===")
    quarterly_paths = []
    for rows, filename in quarterly_files:
        path = create_quarterly_test_data(rows, filename)
        quarterly_paths.append((rows, path))
    
    print(f"\n=== SUMMARY ===")
    print("Annual test files created:")
    for rows, path in annual_paths:
        print(f"  - {path} ({rows} rows)")
    
    print("Quarterly test files created:")
    for rows, path in quarterly_paths:
        print(f"  - {path} ({rows} rows)")
    
    print(f"\nTotal test files created: {len(annual_paths) + len(quarterly_paths)}")

if __name__ == "__main__":
    main()
