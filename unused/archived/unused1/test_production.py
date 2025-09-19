#!/usr/bin/env python3
"""
Test Production Mode - Verify predictions are saved to database
"""

import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from src.database import SessionLocal
from src.ml_service import MLModelService
from bulk_annual_predictions import BulkAnnualPredictionProcessor

def test_production():
    """Test production mode with actual database saves"""
    
    print("🚀 PRODUCTION MODE TEST")
    print("=" * 50)
    print("⚠️  This will create REAL predictions in the database!")
    print("=" * 50)
    
    # Use small chunk for testing
    processor = BulkAnnualPredictionProcessor(
        chunk_size=10,    # Very small chunk for testing
        batch_size=5      # Small batch for testing
    )
    
    try:
        start_time = time.time()
        
        # Run in PRODUCTION mode (not dry-run)
        successful, failed, total = processor.process_bulk_predictions(
            run_id=f"production_test_{int(start_time)}",
            dry_run=False  # THIS IS THE KEY - False = PRODUCTION MODE
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print("\n" + "=" * 50)
        print("🎯 PRODUCTION TEST RESULTS")
        print("=" * 50)
        print(f"⏱️  Duration: {duration:.2f} seconds")
        print(f"📊 Total processed: {total}")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        
        if successful > 0:
            print(f"🎉 SUCCESS! {successful} predictions saved to database!")
            
            # Verify database
            print("\n🔍 Verifying database...")
            db = SessionLocal()
            try:
                from src.database import AnnualPrediction
                count = db.query(AnnualPrediction).count()
                print(f"📊 Total AnnualPredictions in database: {count}")
                
                # Show latest predictions
                latest = db.query(AnnualPrediction).order_by(AnnualPrediction.created_at.desc()).limit(5).all()
                print(f"🔍 Latest 5 predictions:")
                for pred in latest:
                    print(f"  - ID: {pred.id}, Company: {pred.company_id}, Probability: {pred.predicted_default_probability}")
            finally:
                db.close()
                
        else:
            print("❌ No predictions were saved to database!")
            
    except Exception as e:
        print(f"💥 Error during production test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_production()
