#!/usr/bin/env python3
"""
Complete Tenant Setup via API
Usage: python scripts/setup_tenant_via_api.py
"""

import requests
import json
import time
import logging
from typing import Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = "https://d3tytmnn6rkqkb.cloudfront.net"
SUPER_ADMIN_EMAIL = "admin@accunode.ai"
SUPER_ADMIN_PASSWORD = "AccuNode2024!Admin"

# Tenant and Organization Configuration
TENANT_CONFIG = {
    "name": "HDFC Bank Limited",
    "slug": "hdfc-bank", 
    "domain": "hdfcbank.com",
    "description": "India's leading private sector bank for advanced credit risk management"
}

TENANT_ADMIN_CONFIG = {
    "email": "tenant.admin@hdfcbank.com",
    "username": "hdfc_tenant_admin",
    "password": "TenantAdmin2024!",
    "full_name": "HDFC Tenant Administrator"
}

ORGANIZATIONS_CONFIG = [
    {
        "name": "Credit Risk Management Division",
        "slug": "credit-risk-mgmt",
        "domain": "risk-hdfc.com", 
        "description": "Advanced credit risk assessment and default prediction analytics",
        "admin": {
            "email": "risk.head@hdfcbank.com",
            "username": "risk_head",
            "password": "RiskHead2024!",
            "full_name": "Dr. Amit Krishnamurthy"
        },
        "members": [
            {
                "email": "senior.analyst@hdfcbank.com",
                "username": "senior_analyst",
                "password": "Analyst2024!",
                "full_name": "Sneha Raghavan Nair"
            },
            {
                "email": "quant.analyst@hdfcbank.com", 
                "username": "quant_analyst",
                "password": "Quant2024!",
                "full_name": "Arjun Vikram Singh"
            }
        ]
    },
    {
        "name": "Data Analytics & Machine Learning",
        "slug": "data-ml",
        "domain": "analytics-hdfc.com",
        "description": "ML models and statistical analysis for financial risk prediction", 
        "admin": {
            "email": "analytics.head@hdfcbank.com",
            "username": "analytics_head", 
            "password": "MLHead2024!",
            "full_name": "Dr. Kavitha Subramanian"
        },
        "members": [
            {
                "email": "data.scientist@hdfcbank.com",
                "username": "data_scientist",
                "password": "DataSci2024!",
                "full_name": "Rohit Agarwal Joshi"
            },
            {
                "email": "ml.engineer@hdfcbank.com",
                "username": "ml_engineer", 
                "password": "MLEng2024!",
                "full_name": "Ananya Sharma Reddy"
            }
        ]
    }
]

class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.token = None
        
    def login_super_admin(self) -> bool:
        """Login as super admin and store token"""
        logger.info(f"🔐 Logging in as super admin: {SUPER_ADMIN_EMAIL}")
        
        response = self.session.post(
            f"{self.base_url}/api/v1/auth/login",
            json={
                "email": SUPER_ADMIN_EMAIL,
                "password": SUPER_ADMIN_PASSWORD
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            self.session.headers["Authorization"] = f"Bearer {self.token}"
            logger.info("✅ Super admin login successful")
            return True
        else:
            logger.error(f"❌ Super admin login failed: {response.status_code} - {response.text}")
            return False
    
    def create_tenant(self) -> Dict[str, Any]:
        """Create a new tenant"""
        logger.info(f"🏢 Creating tenant: {TENANT_CONFIG['name']}")
        
        response = self.session.post(
            f"{self.base_url}/api/v1/tenants",
            json=TENANT_CONFIG
        )
        
        if response.status_code == 200 or response.status_code == 201:
            tenant_data = response.json()
            logger.info(f"✅ Tenant created successfully: {tenant_data.get('name')}")
            return tenant_data
        else:
            logger.error(f"❌ Tenant creation failed: {response.status_code} - {response.text}")
            raise Exception(f"Failed to create tenant: {response.text}")
    
    def create_tenant_admin(self, tenant_id: str) -> Dict[str, Any]:
        """Create tenant admin user"""
        logger.info(f"👔 Creating tenant admin: {TENANT_ADMIN_CONFIG['email']}")
        
        user_data = {
            "email": TENANT_ADMIN_CONFIG["email"],
            "username": TENANT_ADMIN_CONFIG["username"], 
            "password": TENANT_ADMIN_CONFIG["password"],
            "full_name": TENANT_ADMIN_CONFIG["full_name"],
            "role": "tenant_admin",
            "tenant_id": tenant_id
        }
        
        response = self.session.post(
            f"{self.base_url}/api/v1/users",
            json=user_data
        )
        
        if response.status_code == 200 or response.status_code == 201:
            admin_data = response.json()
            logger.info(f"✅ Tenant admin created: {admin_data.get('email')}")
            return admin_data
        else:
            logger.error(f"❌ Tenant admin creation failed: {response.status_code} - {response.text}")
            raise Exception(f"Failed to create tenant admin: {response.text}")
    
    def create_organization(self, org_config: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        """Create organization"""
        logger.info(f"🏛️ Creating organization: {org_config['name']}")
        
        org_data = {
            "name": org_config["name"],
            "slug": org_config["slug"],
            "domain": org_config["domain"],
            "description": org_config["description"],
            "tenant_id": tenant_id,
            "default_role": "org_member",
            "max_users": 500,
            "allow_global_data_access": False
        }
        
        response = self.session.post(
            f"{self.base_url}/api/v1/organizations",
            json=org_data
        )
        
        if response.status_code == 200 or response.status_code == 201:
            org_response = response.json()
            logger.info(f"✅ Organization created: {org_response.get('name')}")
            return org_response
        else:
            logger.error(f"❌ Organization creation failed: {response.status_code} - {response.text}")
            raise Exception(f"Failed to create organization: {response.text}")
    
    def create_organization_admin(self, admin_config: Dict[str, Any], org_id: str) -> Dict[str, Any]:
        """Create organization admin"""
        logger.info(f"👨‍💼 Creating org admin: {admin_config['email']}")
        
        user_data = {
            "email": admin_config["email"],
            "username": admin_config["username"],
            "password": admin_config["password"],
            "full_name": admin_config["full_name"],
            "organization_id": org_id,
            "role": "org_admin"
        }
        
        response = self.session.post(
            f"{self.base_url}/api/v1/users",
            json=user_data
        )
        
        if response.status_code == 200 or response.status_code == 201:
            admin_data = response.json()
            logger.info(f"✅ Organization admin created: {admin_data.get('email')}")
            return admin_data
        else:
            logger.error(f"❌ Organization admin creation failed: {response.status_code} - {response.text}")
            raise Exception(f"Failed to create org admin: {response.text}")
    
    def create_organization_member(self, member_config: Dict[str, Any], org_id: str) -> Dict[str, Any]:
        """Create organization member"""
        logger.info(f"👥 Creating org member: {member_config['email']}")
        
        user_data = {
            "email": member_config["email"],
            "username": member_config["username"],
            "password": member_config["password"],
            "full_name": member_config["full_name"],
            "organization_id": org_id,
            "role": "org_member"
        }
        
        response = self.session.post(
            f"{self.base_url}/api/v1/users",
            json=user_data
        )
        
        if response.status_code == 200 or response.status_code == 201:
            member_data = response.json()
            logger.info(f"✅ Organization member created: {member_data.get('email')}")
            return member_data
        else:
            logger.error(f"❌ Organization member creation failed: {response.status_code} - {response.text}")
            raise Exception(f"Failed to create org member: {response.text}")
    
    def get_health_status(self) -> bool:
        """Check if the API is healthy"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False
    
    def verify_user_role(self, user_id: str, expected_role: str) -> bool:
        """Verify that a user has the expected role"""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/users/{user_id}")
            if response.status_code == 200:
                user_data = response.json()
                actual_role = user_data.get("role")
                if actual_role == expected_role:
                    logger.info(f"✅ Role verification passed: {user_data.get('email')} has role '{actual_role}'")
                    return True
                else:
                    logger.error(f"❌ Role mismatch: {user_data.get('email')} has role '{actual_role}', expected '{expected_role}'")
                    return False
            return False
        except Exception as e:
            logger.error(f"❌ Role verification failed: {e}")
            return False
    
    def cleanup_existing_tenant(self) -> bool:
        """Clean up existing tenant with same name/slug"""
        logger.info(f"🧹 Cleaning up existing tenant: {TENANT_CONFIG['name']}")
        
        try:
            # Get all tenants
            response = self.session.get(f"{self.base_url}/api/v1/tenants")
            if response.status_code == 200:
                tenants = response.json()
                
                # Find tenant by name or slug
                target_tenant = None
                if isinstance(tenants, list):
                    for tenant in tenants:
                        if (tenant.get('name') == TENANT_CONFIG['name'] or 
                            tenant.get('slug') == TENANT_CONFIG['slug']):
                            target_tenant = tenant
                            break
                elif isinstance(tenants, dict) and 'tenants' in tenants:
                    for tenant in tenants['tenants']:
                        if (tenant.get('name') == TENANT_CONFIG['name'] or 
                            tenant.get('slug') == TENANT_CONFIG['slug']):
                            target_tenant = tenant
                            break
                
                if target_tenant:
                    tenant_id = target_tenant.get('id')
                    logger.info(f"🗑️ Found existing tenant: {target_tenant.get('name')} (ID: {tenant_id})")
                    
                    # Delete the tenant
                    delete_response = self.session.delete(f"{self.base_url}/api/v1/tenants/{tenant_id}")
                    if delete_response.status_code in [200, 204]:
                        logger.info(f"✅ Successfully deleted tenant: {target_tenant.get('name')}")
                        return True
                    else:
                        logger.error(f"❌ Failed to delete tenant: {delete_response.status_code} - {delete_response.text}")
                        return False
                else:
                    logger.info("ℹ️ No existing tenant found with that name/slug")
                    return True
            else:
                logger.error(f"❌ Failed to get tenants: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
            return False

def setup_complete_tenant():
    """Main function to set up complete tenant via API"""
    logger.info("🚀 Starting Complete Tenant Setup via API")
    logger.info("=" * 60)
    logger.info(f"🌐 Backend URL: {BASE_URL}")
    
    # Initialize API client
    client = APIClient(BASE_URL)
    
    # Check API health
    if not client.get_health_status():
        logger.error("❌ API is not healthy. Please check the backend service.")
        return False
    
    logger.info("✅ API health check passed")
    
    try:
        # Step 1: Login as super admin
        if not client.login_super_admin():
            return False
        
        # Step 1.5: Clean up any existing tenant
        if not client.cleanup_existing_tenant():
            logger.warning("⚠️ Cleanup had issues, but continuing...")
        
        # Step 2: Create tenant
        tenant = client.create_tenant()
        tenant_id = tenant.get("id")
        
        # Step 3: Create tenant admin
        tenant_admin = client.create_tenant_admin(tenant_id)
        
        # Step 4: Create organizations with users
        organizations_data = []
        
        for org_config in ORGANIZATIONS_CONFIG:
            # Create organization
            organization = client.create_organization(org_config, tenant_id)
            org_id = organization.get("id")
            
            # Create organization admin
            org_admin = client.create_organization_admin(org_config["admin"], org_id)
            
            # Create organization members
            org_members = []
            for member_config in org_config["members"]:
                member = client.create_organization_member(member_config, org_id)
                org_members.append(member)
            
            organizations_data.append({
                "organization": organization,
                "admin": org_admin,
                "members": org_members
            })
            
            # Small delay between organizations
            time.sleep(1)
        
        # Print comprehensive summary
        print_setup_summary(tenant, tenant_admin, organizations_data)
        
        logger.info("🎉 Complete tenant setup finished successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        return False

def print_setup_summary(tenant: Dict, tenant_admin: Dict, organizations_data: list):
    """Print comprehensive setup summary"""
    print("\n" + "=" * 80)
    print("🎉 COMPLETE TENANT SETUP SUMMARY")
    print("=" * 80)
    
    print(f"\n🏢 TENANT: {tenant.get('name')}")
    print(f"   🆔 ID: {tenant.get('id')}")
    print(f"   🌐 Domain: {tenant.get('domain')}")
    print(f"   📝 Description: {tenant.get('description')}")
    
    print(f"\n👔 TENANT ADMIN:")
    print(f"   📧 Email: {TENANT_ADMIN_CONFIG['email']}")
    print(f"   👤 Username: {TENANT_ADMIN_CONFIG['username']}")
    print(f"   🔑 Password: {TENANT_ADMIN_CONFIG['password']}")
    print(f"   👨‍💼 Full Name: {TENANT_ADMIN_CONFIG['full_name']}")
    print(f"   🆔 User ID: {tenant_admin.get('id')}")
    
    for i, org_data in enumerate(organizations_data, 1):
        org = org_data["organization"]
        admin = org_data["admin"] 
        members = org_data["members"]
        org_config = ORGANIZATIONS_CONFIG[i-1]
        
        print(f"\n🏛️ ORGANIZATION {i}: {org.get('name')}")
        print(f"   🆔 ID: {org.get('id')}")
        print(f"   🌐 Domain: {org.get('domain')}")
        print(f"   🔗 Join Token: {org.get('join_token', 'N/A')}")
        
        print(f"\n   👨‍💼 ORG ADMIN:")
        print(f"      📧 Email: {org_config['admin']['email']}")
        print(f"      👤 Username: {org_config['admin']['username']}")
        print(f"      🔑 Password: {org_config['admin']['password']}")
        print(f"      👨‍💼 Full Name: {org_config['admin']['full_name']}")
        print(f"      🆔 User ID: {admin.get('id')}")
        
        print(f"\n   👥 ORG MEMBERS ({len(members)}):")
        for j, member in enumerate(members):
            member_config = org_config['members'][j]
            print(f"      {j+1}. {member_config['full_name']}")
            print(f"         📧 Email: {member_config['email']}")
            print(f"         👤 Username: {member_config['username']}")
            print(f"         🔑 Password: {member_config['password']}")
            print(f"         🆔 User ID: {member.get('id')}")
    
    print(f"\n📊 SUMMARY STATISTICS:")
    print(f"   🏢 Tenants: 1")
    print(f"   🏛️ Organizations: {len(organizations_data)}")
    print(f"   👥 Total Users: {1 + len(organizations_data) * 3}")  # tenant_admin + (admin + 2 members) per org
    print(f"   🌐 Backend URL: {BASE_URL}")
    
    print(f"\n🔐 LOGIN CREDENTIALS:")
    print(f"   Super Admin: {SUPER_ADMIN_EMAIL} / {SUPER_ADMIN_PASSWORD}")
    print(f"   Tenant Admin: {TENANT_ADMIN_CONFIG['email']} / {TENANT_ADMIN_CONFIG['password']}")
    
    print("\n🎯 NEXT STEPS:")
    print("1. Test login with any of the created users")
    print("2. Upload company data for predictions")
    print("3. Configure organization settings")
    print("4. Set up ML model access permissions")

def main():
    """Main entry point"""
    print("🏗️ AccuNode Complete Tenant Setup")
    print("=" * 50)
    print(f"🎯 Setting up complete tenant via API calls")
    print(f"🌐 Backend: {BASE_URL}")
    print(f"👑 Super Admin: {SUPER_ADMIN_EMAIL}")
    
    success = setup_complete_tenant()
    
    if not success:
        print("\n❌ Setup failed. Please check the logs above.")
        exit(1)
    else:
        print("\n✅ Setup completed successfully!")

if __name__ == "__main__":
    main()
