import os
import pandas as pd
import time
import traceback
from typing import Dict, Any
from celery import current_task
from .celery_app import celery_app
from .database import get_session_local
from .services import CompanyService, PredictionService
from .ml_service import ml_service


@celery_app.task(bind=True, name="src.tasks.process_bulk_excel_task")
def process_bulk_excel_task(self, file_path: str, original_filename: str) -> Dict[str, Any]:
    """
    Background task to process Excel file with multiple companies for bulk predictions.
    
    Args:
        file_path: Path to the uploaded Excel file
        original_filename: Original name of the uploaded file
        
    Returns:
        Dictionary with processing results
    """
    task_id = self.request.id
    start_time = time.time()
    
    # Update task state to PROGRESS
    self.update_state(
        state="PROGRESS",
        meta={
            "status": "Starting bulk prediction processing...",
            "current": 0,
            "total": 0,
            "filename": original_filename
        }
    )
    
    session_factory = get_session_local()
    db = session_factory()
    
    results = []
    successful_predictions = 0
    failed_predictions = 0
    total_companies = 0
    
    try:
        # Read Excel file
        df = pd.read_excel(file_path)
        total_companies = len(df)
        
        # Validate required columns
        required_columns = [
            'stock_symbol', 'company_name', 'debt_to_equity_ratio', 
            'current_ratio', 'quick_ratio', 'return_on_equity', 
            'return_on_assets', 'profit_margin', 'interest_coverage', 
            'fixed_asset_turnover', 'total_debt_ebitda'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
        
        # Update task state
        self.update_state(
            state="PROGRESS",
            meta={
                "status": f"Processing {total_companies} companies...",
                "current": 0,
                "total": total_companies,
                "filename": original_filename,
                "successful": 0,
                "failed": 0
            }
        )
        
        # Initialize services
        company_service = CompanyService(db)
        prediction_service = PredictionService(db)
        
        # Process each company
        for index, row in df.iterrows():
            try:
                # Update progress every 10 companies or for the first/last few
                if index % 10 == 0 or index < 5 or index >= total_companies - 5:
                    self.update_state(
                        state="PROGRESS",
                        meta={
                            "status": f"Processing company {index + 1} of {total_companies}",
                            "current": index + 1,
                            "total": total_companies,
                            "filename": original_filename,
                            "successful": successful_predictions,
                            "failed": failed_predictions
                        }
                    )
                
                # Extract company data
                stock_symbol = str(row['stock_symbol']).strip()
                company_name = str(row['company_name']).strip()
                
                if not stock_symbol or not company_name:
                    raise ValueError("Stock symbol and company name are required")
                
                # Check if company exists
                company = company_service.get_company_by_symbol(stock_symbol)
                
                if not company:
                    # Create new company
                    from .schemas import CompanyCreate
                    company_data = CompanyCreate(
                        symbol=stock_symbol,
                        name=company_name,
                        market_cap=float(row.get('market_cap', 0)) if pd.notna(row.get('market_cap')) else None,
                        sector=str(row.get('sector', '')).strip() if pd.notna(row.get('sector')) else None
                    )
                    company = company_service.create_company(company_data)
                
                # Prepare financial ratios
                ratios = {}
                ratio_columns = [
                    'debt_to_equity_ratio', 'current_ratio', 'quick_ratio',
                    'return_on_equity', 'return_on_assets', 'profit_margin',
                    'interest_coverage', 'fixed_asset_turnover', 'total_debt_ebitda'
                ]
                
                for col in ratio_columns:
                    value = row.get(col)
                    if pd.notna(value):
                        ratios[col] = float(value)
                    else:
                        raise ValueError(f"Missing value for {col}")
                
                # Make prediction
                prediction_result = ml_service.predict_default_probability(ratios)
                
                # Save prediction and ratios
                saved_prediction = prediction_service.save_prediction(
                    company.id, 
                    prediction_result, 
                    ratios
                )
                prediction_service.save_financial_ratios(company.id, ratios)
                
                # Create result item
                result_item = {
                    "stock_symbol": stock_symbol,
                    "company_name": company_name,
                    "sector": company.sector,
                    "market_cap": company.market_cap,
                    "prediction": {
                        "risk_level": prediction_result["risk_level"],
                        "confidence": prediction_result["confidence"],
                        "probability": prediction_result["probability"],
                        "predicted_at": saved_prediction.predicted_at.isoformat() if saved_prediction.predicted_at else None
                    },
                    "status": "success",
                    "error_message": None
                }
                
                results.append(result_item)
                successful_predictions += 1
                
            except Exception as e:
                # Handle individual company errors
                result_item = {
                    "stock_symbol": str(row.get('stock_symbol', f'Row {index + 1}')),
                    "company_name": str(row.get('company_name', 'Unknown')),
                    "sector": str(row.get('sector', '')) if pd.notna(row.get('sector')) else None,
                    "market_cap": float(row.get('market_cap', 0)) if pd.notna(row.get('market_cap')) else None,
                    "prediction": {},
                    "status": "error",
                    "error_message": str(e)
                }
                
                results.append(result_item)
                failed_predictions += 1
                print(f"Error processing row {index + 1}: {e}")
                
                # Rollback the failed transaction
                db.rollback()
        
        # Commit all successful transactions
        prediction_service.commit_transaction()
        
        processing_time = time.time() - start_time
        
        # Final result
        final_result = {
            "task_id": task_id,
            "success": True,
            "message": f"Processed {total_companies} companies successfully",
            "filename": original_filename,
            "total_companies": total_companies,
            "successful_predictions": successful_predictions,
            "failed_predictions": failed_predictions,
            "results": results,
            "processing_time": round(processing_time, 2),
            "completed_at": time.time()
        }
        
        return final_result
        
    except Exception as e:
        # Major error occurred
        db.rollback()
        error_message = str(e)
        error_traceback = traceback.format_exc()
        
        print(f"Bulk prediction task failed: {error_message}")
        print(f"Traceback: {error_traceback}")
        
        # Update task state to FAILURE
        self.update_state(
            state="FAILURE",
            meta={
                "error": error_message,
                "traceback": error_traceback,
                "filename": original_filename,
                "processed": successful_predictions + failed_predictions
            }
        )
        
        raise Exception(error_message)
        
    finally:
        # Cleanup
        try:
            db.close()
        except Exception:
            pass
            
        # Remove uploaded file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Cleaned up file: {file_path}")
        except Exception as e:
            print(f"Failed to cleanup file {file_path}: {e}")


@celery_app.task(name="src.tasks.cleanup_old_files")
def cleanup_old_files():
    """Periodic task to cleanup old uploaded files (if any remain)"""
    upload_dir = "/tmp/bulk_uploads"
    if os.path.exists(upload_dir):
        try:
            for filename in os.listdir(upload_dir):
                file_path = os.path.join(upload_dir, filename)
                if os.path.isfile(file_path):
                    # Remove files older than 1 hour
                    if time.time() - os.path.getctime(file_path) > 3600:
                        os.remove(file_path)
                        print(f"Cleaned up old file: {file_path}")
        except Exception as e:
            print(f"Error during cleanup: {e}")
    
    return {"status": "cleanup_completed"}
