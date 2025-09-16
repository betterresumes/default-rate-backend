#!/usr/bin/env python3
"""
Easy User Creation Script for Default Rate Prediction API
Creates admin users with proper authentication setup
"""

import os
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.append(str(Path(__file__).parent / "src"))

def create_user():
    try:
        # Set database URL
        os.environ['DATABASE_URL'] = os.getenv('DATABASE_URL', 'postgresql://neondb_owner:npg_HtQ6hvJu8jAb@ep-young-violet-a5jkk9fl.us-east-2.aws.neon.tech/neondb?sslmode=require')
        
        # Import after setting environment
        from src.auth import create_user
        from src.database import SessionLocal
        
        print("🔐 Default Rate API - User Creation")
        print("=" * 40)
        
        # Get user input
        email = input("📧 Enter email: ").strip()
        if not email:
            print("❌ Email cannot be empty")
            return
            
        username = input("👤 Enter username: ").strip()
        if not username:
            print("❌ Username cannot be empty")
            return
            
        full_name = input("📝 Enter full name (optional): ").strip()
        if not full_name:
            full_name = username
            
        password = input("🔒 Enter password: ").strip()
        if not password:
            print("❌ Password cannot be empty")
            return
        
        is_admin = input("🔧 Make admin user? (y/N): ").strip().lower() == 'y'
        is_verified = input("✅ Auto-verify user? (Y/n): ").strip().lower() != 'n'
        
        print("\n🚀 Creating user...")
        
        # Create database session
        db = SessionLocal()
        
        try:
            # Create user
            user = create_user(
                db=db,
                email=email,
                username=username,
                password=password,
                full_name=full_name
            )
            
            # Update admin and verification status after creation
            if is_admin:
                user.is_superuser = True
                user.role = "admin"
            
            if is_verified:
                user.is_verified = True
                user.is_active = True
            
            db.commit()
            db.refresh(user)
            
            print(f"✅ User created successfully!")
            print(f"   📧 Email: {user.email}")
            print(f"   👤 Username: {user.username}")
            print(f"   📝 Full Name: {user.full_name}")
            print(f"   🔧 Admin: {'Yes' if user.is_superuser else 'No'}")
            print(f"   ✅ Verified: {'Yes' if user.is_verified else 'No'}")
            print(f"   👤 Role: {user.role}")
            print(f"   🟢 Active: {'Yes' if user.is_active else 'No'}")
            print(f"   🆔 User ID: {user.id}")
            
            print("\n🧪 Test Login:")
            print(f'curl -X POST "http://localhost:8002/api/auth/login" \\')
            print(f'  -H "Content-Type: application/json" \\')
            print(f'  -d \'{{"email": "{email}", "password": "{password}"}}\'')
            
        except Exception as e:
            print(f"❌ Failed to create user: {str(e)}")
            if "already exists" in str(e).lower():
                print("💡 Try with a different email or username")
        finally:
            db.close()
            
    except ImportError as e:
        print(f"❌ Import error: {str(e)}")
        print("Make sure you're running this from the backend directory")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def create_default_admin():
    """Create default admin user for testing"""
    try:
        os.environ['DATABASE_URL'] = os.getenv('DATABASE_URL', 'postgresql://neondb_owner:npg_HtQ6hvJu8jAb@ep-young-violet-a5jkk9fl.us-east-2.aws.neon.tech/neondb?sslmode=require')
        
        from src.auth import create_user
        from src.database import SessionLocal
        
        print("🚀 Creating default admin user...")
        
        db = SessionLocal()
        
        try:
            user = create_user(
                db=db,
                email="admin@defaultrate.com",
                username="admin",
                password="admin123",
                full_name="Default Admin"
            )
            
            # Make user admin and verified
            user.is_superuser = True
            user.role = "admin"
            user.is_verified = True
            user.is_active = True
            
            db.commit()
            db.refresh(user)
            
            print("✅ Default admin user created!")
            print("   📧 Email: admin@defaultrate.com")
            print("   🔒 Password: admin123")
            print("   🔧 Admin: Yes")
            
        except Exception as e:
            if "already exists" in str(e).lower():
                print("ℹ️  Default admin user already exists")
            else:
                print(f"❌ Error: {str(e)}")
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create users for Default Rate API")
    parser.add_argument("--default", action="store_true", help="Create default admin user")
    parser.add_argument("--interactive", action="store_true", help="Interactive user creation")
    
    args = parser.parse_args()
    
    if args.default:
        create_default_admin()
    elif args.interactive or len(sys.argv) == 1:
        create_user()
    else:
        parser.print_help()
