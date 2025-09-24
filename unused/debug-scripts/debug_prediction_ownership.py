#!/usr/bin/env python3
"""
Quick permission debug script to check the specific prediction
"""
import sys
import os

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.database import User, AnnualPrediction, QuarterlyPrediction
import uuid

# Database connection (update if your DB URL is different)
DATABASE_URL = "postgresql://postgres:123456789@localhost/default_rate_predictions"

try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    # The problematic prediction ID
    prediction_id = "47697e2c-60ce-4ddf-901f-00a3f3fa5e8b"
    
    print(f"🔍 Analyzing prediction: {prediction_id}")
    print("=" * 60)
    
    # Try to find the prediction
    prediction = db.query(AnnualPrediction).filter(AnnualPrediction.id == prediction_id).first()
    prediction_type = "annual"
    
    if not prediction:
        prediction = db.query(QuarterlyPrediction).filter(QuarterlyPrediction.id == prediction_id).first()
        prediction_type = "quarterly"
    
    if not prediction:
        print("❌ Prediction not found in database!")
        sys.exit(1)
    
    print(f"✅ Found {prediction_type} prediction")
    print(f"📋 Prediction Details:")
    print(f"   - ID: {prediction.id}")
    print(f"   - Access Level: {prediction.access_level}")
    print(f"   - Created By: '{prediction.created_by}' (type: {type(prediction.created_by).__name__})")
    print(f"   - Organization ID: {prediction.organization_id}")
    print(f"   - Company ID: {prediction.company_id}")
    print(f"   - Created At: {prediction.created_at}")
    
    # Get all users to see who might have created this
    print(f"\n👥 Checking all users:")
    print("-" * 40)
    
    users = db.query(User).all()
    for user in users:
        user_id_str = str(user.id)
        matches = user_id_str == prediction.created_by
        print(f"   User: {user.email} (ID: {user.id}, Role: {user.role})")
        print(f"         ID as string: '{user_id_str}'")
        print(f"         Matches created_by: {matches} {'✅' if matches else '❌'}")
        print()
    
    # Check if there are any UUID conversion issues
    print(f"🔧 UUID Analysis:")
    print("-" * 20)
    try:
        prediction_created_by_uuid = uuid.UUID(prediction.created_by)
        print(f"   Prediction created_by as UUID: {prediction_created_by_uuid}")
        print(f"   Is valid UUID: ✅")
        
        # Check if any user ID matches when converted to UUID
        for user in users:
            if str(user.id) == str(prediction_created_by_uuid):
                print(f"   MATCH FOUND: User {user.email} created this prediction! ✅")
                break
    except Exception as e:
        print(f"   Error parsing created_by as UUID: {e}")
        print(f"   created_by might not be a valid UUID: '{prediction.created_by}'")
    
    # Check for string comparison issues
    print(f"\n🔍 String Comparison Analysis:")
    print("-" * 35)
    print(f"   created_by value: '{prediction.created_by}'")
    print(f"   created_by length: {len(prediction.created_by)}")
    print(f"   created_by has whitespace: {prediction.created_by != prediction.created_by.strip()}")
    
    # Check all possible string matches
    for user in users:
        user_id_variations = [
            str(user.id),
            str(user.id).upper(),
            str(user.id).lower(),
            str(user.id).strip(),
        ]
        
        created_by_variations = [
            prediction.created_by,
            prediction.created_by.upper(),
            prediction.created_by.lower(), 
            prediction.created_by.strip(),
        ]
        
        for user_var in user_id_variations:
            for created_var in created_by_variations:
                if user_var == created_var:
                    print(f"   MATCH FOUND with variations!")
                    print(f"     User {user.email}: '{user_var}'")
                    print(f"     created_by: '{created_var}'")
                    print(f"   ✅ This user should be able to edit the prediction")
                    break
    
    db.close()
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
    print("\nMake sure:")
    print("1. Database is running")
    print("2. Database URL is correct")
    print("3. You're in the correct directory")
    
finally:
    if 'db' in locals():
        db.close()
