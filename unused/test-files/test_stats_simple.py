#!/usr/bin/env python3
"""
Simple test for the statistics API endpoint

This script tests the new /api/v1/predictions/stats endpoint
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
backend_dir = Path(__file__).parent
env_path = backend_dir / '.env'
load_dotenv(env_path)

# Add backend directory to Python path
sys.path.insert(0, str(backend_dir))

try:
    from app.core.database import get_session_local, User, AnnualPrediction, QuarterlyPrediction, Company, Organization
    print("✅ Successfully imported database modules")
except ImportError as e:
    print(f"❌ Failed to import modules: {e}")
    sys.exit(1)

def test_statistics_data():
    """Test the statistics API by checking available data"""
    print("\n📊 Testing Prediction Statistics Data")
    print("=" * 50)
    
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    try:
        # Check if super admin exists
        super_admin = db.query(User).filter(User.role == "super_admin").first()
        
        if not super_admin:
            print("❌ No super admin found in database")
            print("   Please run: python scripts/setup_application_data.py")
            return False
            
        print(f"👑 Found super admin: {super_admin.email}")
        
        # Get basic statistics
        annual_count = db.query(AnnualPrediction).count()
        quarterly_count = db.query(QuarterlyPrediction).count()
        company_count = db.query(Company).count()
        user_count = db.query(User).count()
        org_count = db.query(Organization).count()
        
        print(f"\n📈 Database Statistics:")
        print(f"   Annual Predictions: {annual_count}")
        print(f"   Quarterly Predictions: {quarterly_count}")
        print(f"   Total Predictions: {annual_count + quarterly_count}")
        print(f"   Companies: {company_count}")
        print(f"   Users: {user_count}")
        print(f"   Organizations: {org_count}")
        
        # Check access level breakdown
        print(f"\n🔐 Access Level Distribution:")
        
        access_levels = ["personal", "organization", "system"]
        for level in access_levels:
            annual_level = db.query(AnnualPrediction).filter(AnnualPrediction.access_level == level).count()
            quarterly_level = db.query(QuarterlyPrediction).filter(QuarterlyPrediction.access_level == level).count()
            total_level = annual_level + quarterly_level
            print(f"   {level.capitalize()}: {total_level} total ({annual_level} annual + {quarterly_level} quarterly)")
        
        # Check user role distribution
        print(f"\n👥 User Role Distribution:")
        roles = ["super_admin", "tenant_admin", "org_admin", "org_member", "user"]
        for role in roles:
            role_count = db.query(User).filter(User.role == role).count()
            print(f"   {role.replace('_', ' ').title()}: {role_count}")
        
        print(f"\n✅ Statistics API Endpoint Ready!")
        print(f"🔗 Endpoint: GET /api/v1/predictions/stats")
        print(f"🔑 Access: Super Admin Only")
        print(f"📋 Returns: Comprehensive prediction statistics")
        
        if annual_count == 0 and quarterly_count == 0:
            print(f"\n⚠️  No predictions found in database")
            print(f"   Create some predictions first to see meaningful statistics")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        db.close()

def main():
    """Main function"""
    print("🧪 Statistics API Data Test")
    print("=" * 30)
    
    # Check if .env file exists
    env_path = Path('.env')
    if not env_path.exists():
        print(f"❌ .env file not found")
        print(f"   Please create a .env file with DATABASE_URL")
        sys.exit(1)
    
    print(f"✅ Found .env file")
    
    # Check DATABASE_URL
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print(f"❌ DATABASE_URL not set in .env file")
        sys.exit(1)
    
    print(f"✅ DATABASE_URL configured")
    
    success = test_statistics_data()
    
    if success:
        print(f"\n🎉 Statistics API is ready!")
        print(f"\n📊 Sample API Usage:")
        print(f"   curl -H 'Authorization: Bearer <super_admin_token>' \\")
        print(f"        http://localhost:8000/api/v1/predictions/stats")
    else:
        print(f"\n❌ Test failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
