#!/usr/bin/env python3
"""
Production Bulk Annual Predictions Runner
Enhanced with dry-run mode, validation, and production safety checks.
"""

import os
import sys
import time
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

# Import after path setup
from src.database import SessionLocal
from src.ml_service import MLModelService
from bulk_annual_predictions import BulkAnnualPredictionProcessor

def validate_environment():
    """Validate environment before running"""
    try:
        # Test database connection
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        print("✅ Database connection verified")
        
        # Test ML service initialization  
        ml_service = MLModelService()
        print("✅ ML service verified")
        
        # Check data file exists
        annual_step_path = os.path.join('src', 'models', 'annual_step.pkl')
        if not os.path.exists(annual_step_path):
            print(f"❌ Data file not found: {annual_step_path}")
            return False
        print("✅ Data file found")
        
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def run_bulk_predictions(mode='production', chunk_size=None, batch_size=None):
    """Run bulk predictions with specified mode and parameters"""
    
    # Validate environment first
    if not validate_environment():
        print("💥 Environment validation failed. Please fix issues before proceeding.")
        return False
    
    # Calculate optimal settings
    import multiprocessing
    cpu_count = multiprocessing.cpu_count()
    
    if chunk_size is None:
        chunk_size = min(5000, max(1000, cpu_count * 500))
    if batch_size is None:
        batch_size = min(500, max(100, cpu_count * 50))
    
    # Adjust for dry run (smaller batches for faster feedback)
    if mode == 'dry-run':
        chunk_size = min(100, chunk_size)
        batch_size = min(50, batch_size)
    
    print(f"🖥️  System: {cpu_count} CPU cores")
    print(f"⚙️  Chunk size: {chunk_size:,}")
    print(f"⚙️  Batch size: {batch_size:,}")
    print(f"🎯 Mode: {mode.upper()}")
    print("=" * 60)
    
    # Create processor
    processor = BulkAnnualPredictionProcessor(
        chunk_size=chunk_size,
        batch_size=batch_size
    )
    
    # Run processing
    start_time = time.time()
    
    try:
        dry_run = (mode == 'dry-run')
        successful, failed, total = processor.process_bulk_predictions(
            run_id=f"bulk_run_{int(start_time)}",
            dry_run=dry_run
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Final report
        print("\n" + "=" * 60)
        print(f"🏁 FINAL RESULTS ({mode.upper()})")
        print("=" * 60)
        print(f"⏱️  Total Time: {duration/60:.2f} minutes")
        print(f"📊 Total Processed: {total:,}")
        print(f"✅ Successful: {successful:,}")
        print(f"❌ Failed: {failed:,}")
        
        if total > 0:
            success_rate = (successful / total) * 100
            rate = total / duration
            print(f"📈 Success Rate: {success_rate:.1f}%")
            print(f"⚡ Processing Rate: {rate:.1f} records/second")
            
            if mode == 'dry-run':
                # Estimate full run time
                estimated_full_time = (10726 / rate) / 60 if rate > 0 else 0
                print(f"🔮 Estimated Full Run Time: {estimated_full_time:.1f} minutes")
        
        if mode == 'production' and successful > 0:
            print(f"🎉 Production run completed successfully!")
            print(f"💾 Database updated with {successful:,} new predictions")
        elif mode == 'dry-run':
            print(f"🧪 Dry run completed - no data was saved to database")
        
        return successful > 0
        
    except Exception as e:
        print(f"� Critical error during {mode} run: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function with command line arguments"""
    parser = argparse.ArgumentParser(description='Bulk Annual Predictions Runner')
    parser.add_argument('--mode', choices=['production', 'dry-run'], default='dry-run',
                       help='Run mode: production or dry-run (default: dry-run)')
    parser.add_argument('--chunk-size', type=int, help='Chunk size for processing')
    parser.add_argument('--batch-size', type=int, help='Batch size for database operations')
    parser.add_argument('--force', action='store_true', 
                       help='Skip confirmation prompt for production mode')
    
    args = parser.parse_args()
    
    # Safety check for production mode
    if args.mode == 'production' and not args.force:
        print("⚠️  PRODUCTION MODE DETECTED")
        print("This will create/update records in the production database.")
        confirmation = input("Type 'YES' to proceed with production run: ")
        if confirmation != 'YES':
            print("❌ Production run cancelled.")
            return
    
    # Run the bulk predictions
    success = run_bulk_predictions(
        mode=args.mode,
        chunk_size=args.chunk_size,
        batch_size=args.batch_size
    )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
