#!/usr/bin/env python3
"""
Script to promote a user to super admin role
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

from app.core.database import get_db, User

def promote_to_admin(email: str):
    """Promote user to super admin role"""
    db = next(get_db())
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.global_role = 'super_admin'
            db.commit()
            print(f'✅ Successfully promoted {user.email} to super_admin role')
            print(f'   User ID: {user.id}')
            print(f'   Username: {user.username}')
            print(f'   Global Role: {user.global_role}')
        else:
            print(f'❌ User with email {email} not found')
    except Exception as e:
        print(f'❌ Error: {e}')
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    email = "admin@pranit.com"
    promote_to_admin(email)
