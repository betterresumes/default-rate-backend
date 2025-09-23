#!/usr/bin/env python3

import sys
import os
sys.path.append('.')

from app.services.ml_service import ml_model

print("Available methods on ml_model:")
for attr in dir(ml_model):
    if not attr.startswith('_'):
        print(f"  - {attr}")

print(f"\nType of ml_model: {type(ml_model)}")

# Test the correct method
try:
    test_data = {
        'debt_to_equity_ratio': 0.5,
        'current_ratio': 1.2,
        'quick_ratio': 0.8,
        'return_on_equity': 0.15,
        'return_on_assets': 0.08,
        'profit_margin': 0.1,
        'interest_coverage': 3.0,
        'fixed_asset_turnover': 1.5,
        'total_debt_ebitda': 2.0
    }
    result = ml_model.predict_default_probability(test_data)
    print(f"\n✅ predict_default_probability works: {type(result)}")
except Exception as e:
    print(f"\n❌ Error with predict_default_probability: {e}")

# Test if the wrong method exists
try:
    result = ml_model.predict_annual_default_probability(test_data)
    print(f"\n✅ predict_annual_default_probability works: {type(result)}")
except AttributeError as e:
    print(f"\n✅ Confirmed: predict_annual_default_probability does NOT exist: {e}")
except Exception as e:
    print(f"\n❌ Other error with predict_annual_default_probability: {e}")
