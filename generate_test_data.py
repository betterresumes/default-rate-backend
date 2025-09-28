#!/usr/bin/env python3
"""Generate test data files for performance testing bulk upload APIs"""

import pandas as pd
import numpy as np
import random
from pathlib import Path

# Set random seed for reproducible data
np.random.seed(42)
random.seed(42)

# Sample companies data - Market cap values in millions of dollars
companies_data = [
    ('AAPL', 'Apple Inc', 'Technology', 3000000),           # $3T
    ('MSFT', 'Microsoft Corporation', 'Technology', 2800000), # $2.8T
    ('GOOGL', 'Alphabet Inc', 'Technology', 1800000),       # $1.8T
    ('AMZN', 'Amazon.com Inc', 'Consumer Discretionary', 1600000), # $1.6T
    ('TSLA', 'Tesla Inc', 'Consumer Discretionary', 800000), # $800B
    ('META', 'Meta Platforms Inc', 'Technology', 750000),   # $750B
    ('NVDA', 'NVIDIA Corporation', 'Technology', 1200000),  # $1.2T
    ('JPM', 'JPMorgan Chase & Co', 'Financials', 450000),   # $450B
    ('JNJ', 'Johnson & Johnson', 'Healthcare', 420000),     # $420B
    ('V', 'Visa Inc', 'Financials', 480000),                # $480B
    ('WMT', 'Walmart Inc', 'Consumer Staples', 400000),     # $400B
    ('PG', 'Procter & Gamble', 'Consumer Staples', 360000), # $360B
    ('UNH', 'UnitedHealth Group', 'Healthcare', 500000),    # $500B
    ('HD', 'Home Depot Inc', 'Consumer Discretionary', 320000), # $320B
    ('MA', 'Mastercard Inc', 'Financials', 350000),         # $350B
    ('BAC', 'Bank of America', 'Financials', 280000),       # $280B
    ('ABBV', 'AbbVie Inc', 'Healthcare', 260000),           # $260B
    ('PFE', 'Pfizer Inc', 'Healthcare', 240000),            # $240B
    ('KO', 'Coca-Cola Company', 'Consumer Staples', 250000), # $250B
    ('PEP', 'PepsiCo Inc', 'Consumer Staples', 230000),     # $230B
    ('TMO', 'Thermo Fisher Scientific', 'Healthcare', 220000), # $220B
    ('COST', 'Costco Wholesale', 'Consumer Staples', 210000), # $210B
    ('AVGO', 'Broadcom Inc', 'Technology', 290000),         # $290B
    ('XOM', 'Exxon Mobil Corporation', 'Energy', 200000),   # $200B
    ('NKE', 'Nike Inc', 'Consumer Discretionary', 190000),  # $190B
]

def generate_quarterly_data(num_rows: int) -> pd.DataFrame:
    """Generate quarterly data with specified number of rows"""
    data = []
    
    for i in range(num_rows):
        # Select random company
        company = random.choice(companies_data)
        ticker, name, sector, market_cap_millions = company
        
        # Generate quarterly data
        quarter = random.choice(['Q1', 'Q2', 'Q3', 'Q4'])
        year = random.choice([2023, 2024])
        
        row = {
            'ticker': ticker,
            'company_name': name,
            'sector': sector,
            'market_cap': market_cap_millions,  # Already in millions
            'quarter': quarter,
            'year': year,
            'revenue': round(random.uniform(1000, 50000), 2),  # Millions
            'total_debt': round(random.uniform(500, 10000), 2),  # Millions
            'current_assets': round(random.uniform(5000, 100000), 2),  # Millions
            'current_liabilities': round(random.uniform(3000, 80000), 2),  # Millions
            'total_assets': round(random.uniform(10000, 500000), 2),  # Millions
            'total_liabilities': round(random.uniform(8000, 400000), 2),  # Millions
            'cash_and_equivalents': round(random.uniform(1000, 50000), 2),  # Millions
            'operating_cash_flow': round(random.uniform(-5000, 30000), 2),  # Millions
            'free_cash_flow': round(random.uniform(-3000, 25000), 2),  # Millions
        }
        data.append(row)
    
    return pd.DataFrame(data)

def generate_annual_data(num_rows: int) -> pd.DataFrame:
    """Generate annual data with specified number of rows"""
    data = []
    
    for i in range(num_rows):
        # Select random company
        company = random.choice(companies_data)
        ticker, name, sector, market_cap_millions = company
        
        # Generate annual data
        year = random.choice([2022, 2023, 2024])
        
        row = {
            'ticker': ticker,
            'company_name': name,
            'sector': sector,
            'market_cap': market_cap_millions,  # Already in millions
            'year': year,
            'revenue': round(random.uniform(5000, 200000), 2),  # Millions
            'total_debt': round(random.uniform(2000, 40000), 2),  # Millions
            'current_assets': round(random.uniform(10000, 200000), 2),  # Millions
            'current_liabilities': round(random.uniform(8000, 150000), 2),  # Millions
            'total_assets': round(random.uniform(20000, 1000000), 2),  # Millions
            'total_liabilities': round(random.uniform(15000, 800000), 2),  # Millions
            'cash_and_equivalents': round(random.uniform(2000, 100000), 2),  # Millions
            'operating_cash_flow': round(random.uniform(-10000, 100000), 2),  # Millions
            'free_cash_flow': round(random.uniform(-8000, 80000), 2),  # Millions
        }
        data.append(row)
    
    return pd.DataFrame(data)

def main():
    """Generate all test data files"""
    test_sizes = [10, 20, 50, 100]
    
    # Create test_data directory if it doesn't exist
    test_data_dir = Path('test_data')
    test_data_dir.mkdir(exist_ok=True)
    
    # Generate quarterly test files
    for size in test_sizes:
        df = generate_quarterly_data(size)
        filename = f'quarterly_test_{size}_rows.xlsx'
        filepath = test_data_dir / filename
        df.to_excel(filepath, index=False)
        print(f'Generated {filename} with {len(df)} rows')
    
    # Generate annual test files  
    for size in test_sizes:
        df = generate_annual_data(size)
        filename = f'annual_test_{size}_rows.xlsx'
        filepath = test_data_dir / filename
        df.to_excel(filepath, index=False)
        print(f'Generated {filename} with {len(df)} rows')
    
    print('\nAll test data files generated successfully!')
    print('Market cap values are stored in millions of dollars format.')

if __name__ == '__main__':
    main()def generate_financial_metrics():    """Generate realistic financial metrics"""    return {        'long_term_debt_to_total_capital': np.random.uniform(0.1, 0.6),        'total_debt_to_ebitda': np.random.uniform(0.5, 4.0),        'net_income_margin': np.random.uniform(0.02, 0.25),        'ebit_to_interest_expense': np.random.uniform(2.0, 15.0),        'return_on_assets': np.random.uniform(0.02, 0.20),    }def generate_quarterly_metrics():    """Generate realistic quarterly financial metrics"""    return {        'total_debt_to_ebitda': np.random.uniform(0.5, 4.0),        'sga_margin': np.random.uniform(0.05, 0.30),        'long_term_debt_to_total_capital': np.random.uniform(0.1, 0.6),        'return_on_capital': np.random.uniform(0.05, 0.25),    }def create_annual_test_data(num_rows: int, filename: str):    """Create annual predictions test data"""    data = []        for i in range(num_rows):        company = random.choice(companies_data)        metrics = generate_financial_metrics()                row = {            'company_symbol': company[0],            'company_name': company[1],            'sector': company[2],            'market_cap': company[3] + random.randint(-50000, 50000),  # Add variation in millions            'reporting_year': random.choice([2022, 2023, 2024]),            **metrics        }        data.append(row)        df = pd.DataFrame(data)    output_path = f"test_data/{filename}"    df.to_excel(output_path, index=False)    print(f"Created {output_path} with {num_rows} rows")    return output_pathdef create_quarterly_test_data(num_rows: int, filename: str):    """Create quarterly predictions test data"""    data = []        for i in range(num_rows):        company = random.choice(companies_data)        metrics = generate_quarterly_metrics()                row = {            'company_symbol': company[0],            'company_name': company[1],            'sector': company[2],            'market_cap': company[3] + random.randint(-50000, 50000),  # Add variation in millions            'reporting_year': random.choice([2022, 2023, 2024]),            'reporting_quarter': random.choice(['Q1', 'Q2', 'Q3', 'Q4']),            **metrics        }        data.append(row)        df = pd.DataFrame(data)    output_path = f"test_data/{filename}"    df.to_excel(output_path, index=False)    print(f"Created {output_path} with {num_rows} rows")    return output_pathdef main():    """Generate all test data files"""    print("🚀 Generating test data files for performance testing...")    print("💡 Market cap values are now in millions of dollars")        # Create test data directory    Path("test_data").mkdir(exist_ok=True)        # Generate annual test files    annual_files = [        (10, "annual_test_10_rows.xlsx"),        (20, "annual_test_20_rows.xlsx"),        (50, "annual_test_50_rows.xlsx"),        (100, "annual_test_100_rows.xlsx"),    ]        # Generate quarterly test files    quarterly_files = [        (10, "quarterly_test_10_rows.xlsx"),        (20, "quarterly_test_20_rows.xlsx"),        (50, "quarterly_test_50_rows.xlsx"),        (100, "quarterly_test_100_rows.xlsx"),    ]        print("\n=== GENERATING ANNUAL TEST DATA ===")    annual_paths = []    for rows, filename in annual_files:        path = create_annual_test_data(rows, filename)        annual_paths.append((rows, path))        print("\n=== GENERATING QUARTERLY TEST DATA ===")    quarterly_paths = []    for rows, filename in quarterly_files:        path = create_quarterly_test_data(rows, filename)        quarterly_paths.append((rows, path))        print(f"\n=== SUMMARY ===")    print("📊 Annual test files created:")    for rows, path in annual_paths:        print(f"   - {path} ({rows} rows)")        print("📊 Quarterly test files created:")    for rows, path in quarterly_paths:        print(f"   - {path} ({rows} rows)")        print(f"\n✅ Total test files created: {len(annual_paths) + len(quarterly_paths)}")    print("🎯 Ready for bulk upload performance testing!")if __name__ == "__main__":    main()