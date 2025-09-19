#!/usr/bin/env python3
"""
Real-time Database Monitor
Shows exactly what's being created in the database during bulk processing.
"""

import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from src.database import SessionLocal, Company, AnnualPrediction
from sqlalchemy import func, desc

def monitor_database():
    """Monitor database changes in real-time"""
    print("🔍 Real-time Database Monitor")
    print("=" * 50)
    
    db = SessionLocal()
    
    try:
        # Get initial counts
        initial_companies = db.query(Company).count()
        initial_predictions = db.query(AnnualPrediction).count()
        
        print(f"📊 Initial state:")
        print(f"   Companies: {initial_companies:,}")
        print(f"   Predictions: {initial_predictions:,}")
        print()
        
        print("🔄 Monitoring changes every 5 seconds...")
        print("=" * 50)
        
        while True:
            # Get current counts
            current_companies = db.query(Company).count()
            current_predictions = db.query(AnnualPrediction).count()
            
            # Calculate changes
            company_change = current_companies - initial_companies
            prediction_change = current_predictions - initial_predictions
            
            # Get latest entries
            latest_company = db.query(Company).order_by(desc(Company.created_at)).first()
            latest_prediction = db.query(AnnualPrediction).order_by(desc(AnnualPrediction.created_at)).first()
            
            # Display current status
            now = datetime.now().strftime("%H:%M:%S")
            print(f"[{now}] Companies: {current_companies:,} (+{company_change}) | Predictions: {current_predictions:,} (+{prediction_change})")
            
            if latest_company:
                print(f"         Latest Company: {latest_company.symbol} - {latest_company.name}")
            
            if latest_prediction:
                company = db.query(Company).filter(Company.id == latest_prediction.company_id).first()
                print(f"         Latest Prediction: {company.symbol if company else 'Unknown'} FY{latest_prediction.reporting_year} (prob: {latest_prediction.probability:.3f})")
            
            # Check if predictions are being created for companies
            if company_change > 0 and prediction_change == 0:
                print("         ⚠️  WARNING: Companies created but NO predictions!")
            elif prediction_change > 0:
                print("         ✅ Both companies and predictions being created")
            
            print("-" * 50)
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped")
    finally:
        db.close()

if __name__ == "__main__":
    monitor_database()
