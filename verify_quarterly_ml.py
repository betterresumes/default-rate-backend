#!/usr/bin/env python3
"""
Verification script to check if quarterly ML models are working in production
This should be run at container startup to verify everything is working
"""

import sys
import os

def verify_quarterly_ml():
    """Verify quarterly ML models can be loaded and used"""
    
    print("🔍 Verifying Quarterly ML Models...")
    
    try:
        # Add app to path
        sys.path.insert(0, '/app')
        
        # Test model loading
        from app.services.quarterly_ml_service import quarterly_ml_model
        print("✅ Quarterly ML service imported successfully")
        
        # Test prediction with sample data
        test_data = {
            'total_debt_to_ebitda': 7.933,
            'sga_margin': 7.474,
            'long_term_debt_to_total_capital': 36.912,
            'return_on_capital': 9.948
        }
        
        print(f"🧪 Testing prediction with: {test_data}")
        
        # This is the exact call that hangs in production
        result = quarterly_ml_model.predict_quarterly_default_probability(test_data)
        
        print(f"✅ Prediction successful: {result.get('risk_level', 'Unknown')}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("   This might be a missing dependency issue")
        return False
        
    except Exception as e:
        print(f"❌ Prediction Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_dependencies():
    """Check if all required dependencies are available"""
    
    print("\n📦 Checking Dependencies...")
    
    required_packages = [
        'lightgbm',
        'pandas', 
        'numpy',
        'scikit-learn',
        'joblib'
    ]
    
    missing = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} - MISSING")
            missing.append(package)
    
    if missing:
        print(f"\n❌ Missing packages: {missing}")
        return False
    else:
        print("\n✅ All dependencies available")
        return True

if __name__ == "__main__":
    print("🚀 Railway Production Environment Verification")
    print("=" * 50)
    
    deps_ok = verify_dependencies()
    ml_ok = verify_quarterly_ml()
    
    if deps_ok and ml_ok:
        print("\n🎉 SUCCESS: Quarterly ML models are working!")
        print("   The quarterly bulk upload should work in this environment.")
        sys.exit(0)
    else:
        print("\n💥 FAILURE: Issues detected!")
        print("   The quarterly bulk upload will fail in this environment.")
        sys.exit(1)
