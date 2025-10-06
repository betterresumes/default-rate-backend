#!/usr/bin/env python3
"""
Email Service Test Script

This script tests the email service functionality in isolation.
Run this to verify email configuration and test sending emails.
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.email_service import email_service

async def test_email_configuration():
    """Test email service configuration"""
    print("🔧 Testing Email Service Configuration")
    print("=" * 50)
    
    # Test connection
    result = await email_service.test_connection()
    
    print(f"✅ Connection Test: {'PASSED' if result['success'] else 'FAILED'}")
    if not result['success']:
        print(f"❌ Error: {result['error']}")
    
    print("\n📋 Configuration Details:")
    details = result.get('details', {})
    for key, value in details.items():
        print(f"   {key}: {value}")
    
    return result['success']

async def test_send_email():
    """Test sending an email"""
    print("\n📧 Testing Email Sending")
    print("=" * 50)
    
    try:
        success = await email_service.send_contact_form_email(
            name="Test User",
            email="test@example.com",
            subject="Email Service Test",
            message="This is a test email from the AccuNode email service.\n\nIf you receive this, the email service is working correctly!",
            user_ip="127.0.0.1",
            user_agent="Email Service Test Script"
        )
        
        print(f"✅ Email Send Test: {'PASSED' if success else 'FAILED'}")
        return success
        
    except Exception as e:
        print(f"❌ Email Send Test: FAILED")
        print(f"   Error: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 AccuNode Email Service Test")
    print("=" * 50)
    
    # Check if SMTP credentials are configured
    config = email_service.config
    
    print("📝 Current Configuration:")
    print(f"   SMTP Host: {config.SMTP_HOST}")
    print(f"   SMTP Port: {config.SMTP_PORT}")
    print(f"   SMTP Username: {'***' + config.SMTP_USERNAME[-5:] if config.SMTP_USERNAME else 'NOT SET'}")
    print(f"   SMTP Password: {'SET' if config.SMTP_PASSWORD else 'NOT SET'}")
    print(f"   Email From: {config.EMAIL_FROM}")
    print(f"   Email To: {config.EMAIL_TO}")
    
    if not config.SMTP_USERNAME or not config.SMTP_PASSWORD:
        print("\n⚠️  WARNING: SMTP credentials not configured!")
        print("   Please set the following environment variables:")
        print("   - SMTP_USERNAME (your GoDaddy email)")
        print("   - SMTP_PASSWORD (your app-specific password)")
        print("\n   Or add them to your .env file")
        return False
    
    print("\n" + "="*50)
    
    # Test configuration
    config_ok = await test_email_configuration()
    
    if not config_ok:
        print("\n❌ Configuration test failed. Cannot proceed with email test.")
        return False
    
    # Test sending email
    email_ok = await test_send_email()
    
    print("\n" + "="*50)
    print("📊 TEST SUMMARY")
    print("="*50)
    print(f"Configuration Test: {'✅ PASSED' if config_ok else '❌ FAILED'}")
    print(f"Email Send Test: {'✅ PASSED' if email_ok else '❌ FAILED'}")
    
    if config_ok and email_ok:
        print("\n🎉 All tests passed! Email service is working correctly.")
        print(f"   Check your inbox at: {config.EMAIL_TO}")
    else:
        print("\n⚠️  Some tests failed. Check your configuration.")
    
    return config_ok and email_ok

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run tests
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
