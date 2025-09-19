#!/usr/bin/env python3
"""
Script to populate missing data after multi-tenant migration
"""

import os
import sys
import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import secrets
import string

# Load environment variables
load_dotenv()

def get_database_url():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    return database_url

def generate_join_token():
    """Generate secure join token"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(32))

def populate_missing_data():
    """Populate missing data after migration"""
    print("🔧 Populating missing data after migration...")
    
    engine = create_engine(get_database_url())
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # Update organizations without join_token
        print("📝 Updating organizations with missing join tokens...")
        orgs_without_token = db.execute(text("""
            SELECT id, name FROM organizations 
            WHERE join_token IS NULL OR join_token = ''
        """)).fetchall()
        
        for org in orgs_without_token:
            join_token = generate_join_token()
            db.execute(text("""
                UPDATE organizations 
                SET join_token = :token, 
                    join_created_at = NOW(),
                    updated_at = NOW()
                WHERE id = :org_id
            """), {"token": join_token, "org_id": org.id})
            print(f"✅ Added join token for organization: {org.name}")
        
        # Update users without proper default values
        print("📝 Updating users with missing default values...")
        db.execute(text("""
            UPDATE users 
            SET updated_at = NOW()
            WHERE updated_at IS NULL
        """))
        
        # Update organizations with missing updated_at
        db.execute(text("""
            UPDATE organizations 
            SET updated_at = created_at
            WHERE updated_at IS NULL
        """))
        
        db.commit()
        print("✅ Data population completed successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Data population failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    try:
        populate_missing_data()
    except Exception as e:
        print(f"💥 Error: {e}")
        sys.exit(1)
