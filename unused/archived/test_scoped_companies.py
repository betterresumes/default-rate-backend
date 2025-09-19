#!/usr/bin/env python3
"""
Test script to demonstrate scoped company creation

This script shows how the new system allows multiple organizations
to create companies with the same symbol independently.
"""

def demonstrate_scoped_companies():
    """
    Demonstrate how companies are now scoped by organization
    """
    
    print("🏢 Financial Risk API - Scoped Company Creation Demo")
    print("=" * 60)
    
    print("\n📋 NEW BEHAVIOR: Scoped Company Creation")
    print("-" * 40)
    
    scenarios = [
        {
            "user": "Super Admin",
            "role": "super_admin",
            "org_id": None,
            "company_symbol": "HDFC",
            "scope": "Global",
            "result": "✅ Creates GLOBAL HDFC company (organization_id=NULL, is_global=true)"
        },
        {
            "user": "Bank A User",
            "role": "org_member", 
            "org_id": "bank-a-123",
            "company_symbol": "HDFC",
            "scope": "Organization A",
            "result": "✅ Creates BANK A's HDFC company (organization_id=bank-a-123, is_global=false)"
        },
        {
            "user": "Bank B User",
            "role": "org_member",
            "org_id": "bank-b-456", 
            "company_symbol": "HDFC",
            "scope": "Organization B",
            "result": "✅ Creates BANK B's HDFC company (organization_id=bank-b-456, is_global=false)"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. {scenario['user']} ({scenario['role']}):")
        print(f"   Symbol: {scenario['company_symbol']}")
        print(f"   Scope: {scenario['scope']}")
        print(f"   {scenario['result']}")
    
    print(f"\n🎯 RESULT: 3 separate HDFC companies coexist!")
    print("   - 1 Global HDFC (accessible based on org settings)")
    print("   - 1 Bank A HDFC (only accessible to Bank A)")
    print("   - 1 Bank B HDFC (only accessible to Bank B)")
    
    print(f"\n📊 Database Structure:")
    print("   companies table:")
    print("   ┌─────────┬─────────────────┬───────────┬──────────────┐")
    print("   │ symbol  │ organization_id │ is_global │ accessible_by│")
    print("   ├─────────┼─────────────────┼───────────┼──────────────┤")
    print("   │ HDFC    │ NULL            │ true      │ Global*      │")
    print("   │ HDFC    │ bank-a-123      │ false     │ Bank A only  │")
    print("   │ HDFC    │ bank-b-456      │ false     │ Bank B only  │")
    print("   └─────────┴─────────────────┴───────────┴──────────────┘")
    print("   * Global access depends on organization's allow_global_data_access setting")
    
    print(f"\n💡 BENEFITS:")
    print("   ✅ No symbol conflicts between organizations")
    print("   ✅ Each organization owns their company data")
    print("   ✅ Independent financial analysis")
    print("   ✅ Real-world business logic")
    
    print(f"\n🔧 UPDATED CURL EXAMPLES:")
    print("   # Bank A creating HDFC (will work now):")
    print("   curl -X POST {{base_url}}/api/v1/predictions/annual \\")
    print("     -H 'Authorization: Bearer BANK_A_USER_TOKEN' \\")
    print("     -d '{\"company_symbol\": \"HDFC\", ...}'")
    print()
    print("   # Bank B creating HDFC (will also work):")
    print("   curl -X POST {{base_url}}/api/v1/predictions/annual \\")
    print("     -H 'Authorization: Bearer BANK_B_USER_TOKEN' \\")
    print("     -d '{\"company_symbol\": \"HDFC\", ...}'")

if __name__ == "__main__":
    demonstrate_scoped_companies()
