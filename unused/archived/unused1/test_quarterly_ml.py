#!/usr/bin/env python3
"""
Test quarterly ML predictions directly
"""

import pandas as pd
import sys
import os

# Add src to path
sys.path.append('src')

def test_quarterly_ml():
    print("🤖 Testing quarterly ML predictions directly...")
    
    try:
        # Load the quarterly test file
        df = pd.read_excel('quarterly_upload_files/quarterly_test_10_records.xlsx')
        print(f"✅ Loaded {len(df)} records")
        
        # Import quarterly ML service
        from quarterly_ml_service import QuarterlyMLModelService
        
        print("🔮 Initializing Quarterly ML Service...")
        ml_service = QuarterlyMLModelService()
        
        # Test predictions on sample data
        print("📊 Testing predictions on sample records...")
        
        results = []
        for idx, row in df.iterrows():
            try:
                # Create feature dict for quarterly prediction
                quarterly_features = {
                    'total_debt_to_ebitda': row['total_debt_to_ebitda'],
                    'sga_margin': row['sga_margin'],
                    'long_term_debt_to_total_capital': row['long_term_debt_to_total_capital'],
                    'return_on_capital': row['return_on_capital']
                }
                
                # Make prediction
                prediction = ml_service.predict(quarterly_features)
                
                result = {
                    'stock_symbol': row['stock_symbol'],
                    'company_name': row['company_name'],
                    'reporting_year': row['reporting_year'],
                    'reporting_quarter': row['reporting_quarter'],
                    'default_probability': prediction['default_probability'],
                    'risk_category': prediction['risk_category'],
                    'features': quarterly_features
                }
                results.append(result)
                
                print(f"  ✅ {row['stock_symbol']} ({row['reporting_year']} {row['reporting_quarter']}): {prediction['default_probability']:.4f} ({prediction['risk_category']})")
                
            except Exception as e:
                print(f"  ❌ Error predicting {row['stock_symbol']}: {e}")
        
        print(f"\n📈 Successfully predicted {len(results)} out of {len(df)} records")
        
        # Show summary stats
        if results:
            probs = [r['default_probability'] for r in results]
            categories = [r['risk_category'] for r in results]
            
            print(f"\n📊 Prediction Summary:")
            print(f"  Average Default Probability: {sum(probs)/len(probs):.4f}")
            print(f"  Risk Category Distribution:")
            from collections import Counter
            cat_counts = Counter(categories)
            for cat, count in cat_counts.items():
                print(f"    {cat}: {count}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure quarterly_ml_service.py is in the src/ directory")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_quarterly_ml()
    if success:
        print("\n✅ Quarterly ML test completed successfully!")
    else:
        print("\n❌ Quarterly ML test failed!")
