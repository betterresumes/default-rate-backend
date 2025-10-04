#!/usr/bin/env python3
"""
Complete Local Development Setup Script

This script sets up everything needed for local development:
1. Creates database schema and super admin
2. Sets up sample tenant with organizations via API

Usage:
    python scripts/local/complete_local_setup.py
"""

import os
import sys
import time
import logging
import subprocess
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_docker_services():
    """Check if Docker services are running"""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}", "--filter", "status=running"],
            capture_output=True,
            text=True,
            check=True
        )
        
        running_services = result.stdout.strip().split('\n')
        required_services = ['accunode-postgres-dev', 'accunode-api-dev']
        
        missing_services = []
        for service in required_services:
            if service not in running_services:
                missing_services.append(service)
        
        if missing_services:
            logger.error(f"❌ Missing Docker services: {', '.join(missing_services)}")
            logger.info("💡 Start services with: make start")
            return False
        
        logger.info("✅ All required Docker services are running")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Error checking Docker services: {e}")
        return False

def wait_for_api(max_attempts=30, delay=2):
    """Wait for API to be ready"""
    import requests
    
    api_url = "http://localhost:8000/health"
    
    for attempt in range(max_attempts):
        try:
            response = requests.get(api_url, timeout=5)
            if response.status_code == 200:
                logger.info("✅ API is ready")
                return True
        except:
            pass
        
        logger.info(f"⏳ Waiting for API... (attempt {attempt + 1}/{max_attempts})")
        time.sleep(delay)
    
    logger.error("❌ API is not responding after maximum attempts")
    return False

def run_database_setup():
    """Run database setup script"""
    script_path = Path(__file__).parent / "setup_super_admin_local.py"
    
    try:
        logger.info("🗄️ Running database setup...")
        result = subprocess.run([sys.executable, str(script_path)], 
                              check=True, capture_output=True, text=True)
        logger.info("✅ Database setup completed")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Database setup failed: {e}")
        if e.stdout:
            logger.error(f"Output: {e.stdout}")
        if e.stderr:
            logger.error(f"Error: {e.stderr}")
        return False

def run_tenant_setup():
    """Run tenant setup script"""
    script_path = Path(__file__).parent / "setup_tenant_local.py"
    
    try:
        logger.info("🏢 Running tenant setup...")
        result = subprocess.run([sys.executable, str(script_path)], 
                              check=True, capture_output=True, text=True)
        logger.info("✅ Tenant setup completed")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Tenant setup failed: {e}")
        if e.stdout:
            logger.error(f"Output: {e.stdout}")
        if e.stderr:
            logger.error(f"Error: {e.stderr}")
        return False

def display_final_summary():
    """Display final setup summary"""
    logger.info("\n" + "🎉" * 30)
    logger.info("🚀 LOCAL DEVELOPMENT SETUP COMPLETE!")
    logger.info("🎉" * 30)
    
    logger.info("\n📋 WHAT'S BEEN SET UP:")
    logger.info("✅ PostgreSQL database with schema")
    logger.info("✅ Super admin account")
    logger.info("✅ Sample tenant (Test Bank Local)")
    logger.info("✅ 3 Sample organizations")
    logger.info("✅ Admin accounts for all levels")
    
    logger.info("\n🌐 ACCESS POINTS:")
    logger.info("🔗 API: http://localhost:8000")
    logger.info("📚 API Docs: http://localhost:8000/docs")
    logger.info("🔍 ReDoc: http://localhost:8000/redoc")
    
    logger.info("\n🔑 KEY CREDENTIALS:")
    logger.info("👑 Super Admin: admin@accunode.local / LocalAdmin2024!")
    logger.info("🏢 Tenant Admin: tenant_admin@testbank.local / TenantAdmin2024!")
    logger.info("🏬 Org Admins: See previous output for details")
    
    logger.info("\n💡 NEXT STEPS:")
    logger.info("1. Test API endpoints with the created accounts")
    logger.info("2. Use TablePlus to explore the database")
    logger.info("3. Start building and testing your features")
    
    logger.info("\n" + "🎯" * 30)
    logger.info("READY FOR DEVELOPMENT!")
    logger.info("🎯" * 30 + "\n")

def main():
    """Main setup function"""
    logger.info("🔧 Complete Local Development Setup")
    logger.info("=" * 60)
    
    try:
        # Step 1: Check Docker services
        logger.info("🐳 Checking Docker services...")
        if not check_docker_services():
            logger.error("❌ Docker services are not running properly")
            logger.info("💡 Run 'make start' to start all services")
            return False
        
        # Step 2: Wait for API
        logger.info("⏳ Waiting for API to be ready...")
        if not wait_for_api():
            logger.error("❌ API is not responding")
            return False
        
        # Step 3: Run database setup
        logger.info("🗄️ Setting up database and super admin...")
        if not run_database_setup():
            logger.error("❌ Database setup failed")
            return False
        
        # Step 4: Wait a bit for database changes to propagate
        logger.info("⏳ Waiting for database changes to propagate...")
        time.sleep(3)
        
        # Step 5: Run tenant setup
        logger.info("🏢 Setting up tenant and organizations...")
        if not run_tenant_setup():
            logger.error("❌ Tenant setup failed")
            return False
        
        # Step 6: Display final summary
        display_final_summary()
        
        logger.info("✅ Complete local setup finished successfully!")
        return True
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ Setup cancelled by user")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
