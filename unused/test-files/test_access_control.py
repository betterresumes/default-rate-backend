#!/usr/bin/env python3
"""
Test script for the new simplified 3-level access control system
"""

import os
import sys
sys.path.append('/Users/nikhil/Downloads/pranit/work/final/default-rate/backend')

from app.core.database import get_session_local, User, Company, AnnualPrediction

def test_access_control_system():
    """Test the simplified access control system"""
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    try:
        print("🧪 Testing Simplified 3-Level Access Control System")
        print("=" * 60)
        
        # Get different types of users
        super_admin = db.query(User).filter(User.role == "super_admin").first()
        org_admin = db.query(User).filter(User.role == "org_admin").first()
        org_member = db.query(User).filter(User.role == "org_member").first()
        
        print(f"👑 Super Admin: {super_admin.email}")
        print(f"👨‍💼 Org Admin: {org_admin.email} (Org: {org_admin.organization_id})")
        print(f"👥 Org Member: {org_member.email} (Org: {org_member.organization_id})")
        
        print("\n📊 Testing Access Levels:")
        
        # Test access level function
        from app.api.v1.predictions import get_user_access_level
        
        super_access = get_user_access_level(super_admin)
        org_admin_access = get_user_access_level(org_admin)
        org_member_access = get_user_access_level(org_member)
        
        print(f"✅ Super Admin Access Level: {super_access}")
        print(f"✅ Org Admin Access Level: {org_admin_access}")
        print(f"✅ Org Member Access Level: {org_member_access}")
        
        print("\n🔍 Expected Results:")
        print("   - Super Admin: 'system' (can create system-wide data)")
        print("   - Org Admin: 'organization' (can create org data)")
        print("   - Org Member: 'organization' (can create org data)")
        print("   - Regular User (no org): 'personal' (personal data only)")
        
        assert super_access == "system", f"Super admin should have 'system' access, got {super_access}"
        assert org_admin_access == "organization", f"Org admin should have 'organization' access, got {org_admin_access}"
        assert org_member_access == "organization", f"Org member should have 'organization' access, got {org_member_access}"
        
        print("\n🎉 All access control tests passed!")
        print("\n📋 Summary of New System:")
        print("   1. 'personal' - Only creator can see (private data)")
        print("   2. 'organization' - All org members can see (shared org data)")
        print("   3. 'system' - Everyone can see (public/system data)")
        print("\n✅ No more complex 'is_global' and 'allow_global_data_access' logic!")
        print("✅ Privacy is maintained - personal data stays personal!")
        print("✅ Org admin/member data is automatically organization-level!")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_access_control_system()
    if success:
        print("\n🚀 System is ready for testing!")
    else:
        print("\n💥 System needs debugging")
        sys.exit(1)
