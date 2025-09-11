import os
import pandas as pd
import time
import traceback
import io
import base64
from typing import Dict, Any
from celery import current_task
from .celery_app import celery_app
from .database import get_session_local
from .services import CompanyService, PredictionService
from .ml_service import ml_model
from .email_service import email_service


@celery_app.task(name="src.tasks.send_verification_email_task")
def send_verification_email_task(email: str, username: str, otp: str) -> bool:
    """
    Background task to send verification email.
    
    Args:
        email: User's email address
        username: User's username
        otp: Generated OTP code
        
    Returns:
        Boolean indicating success
    """
    try:
        return email_service.send_verification_email(email, username, otp)
    except Exception as e:
        print(f"Failed to send verification email to {email}: {str(e)}")
        return False


@celery_app.task(name="src.tasks.send_password_reset_email_task")
def send_password_reset_email_task(email: str, username: str, otp: str) -> bool:
    """
    Background task to send password reset email.
    
    Args:
        email: User's email address
        username: User's username
        otp: Generated OTP code
        
    Returns:
        Boolean indicating success
    """
    try:
        return email_service.send_password_reset_email(email, username, otp)
    except Exception as e:
        print(f"Failed to send password reset email to {email}: {str(e)}")
        return False


@celery_app.task(bind=True, name="src.tasks.process_bulk_excel_task")
def process_bulk_excel_task(self, file_content_b64: str, original_filename: str) -> Dict[str, Any]:
    """
    Background task to process Excel file with multiple companies for bulk predictions.
    
    Args:
        file_content_b64: Base64 encoded content of the uploaded Excel file
        original_filename: Original name of the uploaded file
        
    Returns:
        Dictionary with processing results
    """
    task_id = self.request.id
    start_time = time.time()
    
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
        file_content = base64.b64decode(file_content_b64)
        df = pd.read_excel(io.BytesIO(file_content))
        total_companies = len(df)
        
        column_mapping = {
            'long-term debt / total capital (%)': 'long_term_debt_to_total_capital',
            'long_term_debt_to_total_capital': 'long_term_debt_to_total_capital',
            'total debt / ebitda': 'total_debt_to_ebitda', 
            'total_debt_to_ebitda': 'total_debt_to_ebitda',
            'net income margin': 'net_income_margin',
            'net_income_margin': 'net_income_margin', 
            'ebit / interest expense': 'ebit_to_interest_expense',
            'ebit_to_interest_expense': 'ebit_to_interest_expense',
            'return on assets': 'return_on_assets',
            'return_on_assets': 'return_on_assets'
        }
        
        required_columns = [
            'company_name',
            'stock_symbol',
            'market_cap',
            'sector'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        ratio_columns_found = False
        for excel_col, api_col in column_mapping.items():
            if excel_col in df.columns:
                ratio_columns_found = True
                break
                
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
            
        if not ratio_columns_found:
            raise ValueError(f"Missing financial ratio columns. Expected one of: {', '.join(column_mapping.keys())}")
        
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
        
        company_service = CompanyService(db)
        prediction_service = PredictionService(db)
        
        for index, row in df.iterrows():
            try:
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
                
                company_name = str(row['company_name']).strip()
                stock_symbol = str(row['stock_symbol']).strip().upper()
                market_cap = float(row['market_cap'])
                sector = str(row['sector']).strip()
                
                if not company_name:
                    raise ValueError("Company name is required")
                if not stock_symbol:
                    raise ValueError("Stock symbol is required")
                if not sector:
                    raise ValueError("Sector is required")
                
                # Get or create company with all required fields
                company = company_service.get_company_by_symbol(stock_symbol)
                
                if not company:
                    from .schemas import CompanyCreate
                    company_data = CompanyCreate(
                        name=company_name,
                        symbol=stock_symbol,
                        market_cap=market_cap,
                        sector=sector,
                        reporting_year=str(row.get('reporting_year', '')).strip() if pd.notna(row.get('reporting_year')) else None,
                        reporting_quarter=str(row.get('reporting_quarter', '')).strip() if pd.notna(row.get('reporting_quarter')) else None
                    )
                    company = company_service.create_company(company_data)
                
                # Extract financial ratios (5 required ratios) using column mapping
                ratios = {}
                try:
                    # Use column mapping to handle different naming conventions
                    if 'long-term debt / total capital (%)' in df.columns:
                        ratios['long_term_debt_to_total_capital'] = float(row['long-term debt / total capital (%)'])
                    elif 'long_term_debt_to_total_capital' in df.columns:
                        ratios['long_term_debt_to_total_capital'] = float(row['long_term_debt_to_total_capital'])
                    
                    if 'total debt / ebitda' in df.columns:
                        ratios['total_debt_to_ebitda'] = float(row['total debt / ebitda'])
                    elif 'total_debt_to_ebitda' in df.columns:
                        ratios['total_debt_to_ebitda'] = float(row['total_debt_to_ebitda'])
                    
                    if 'net income margin' in df.columns:
                        ratios['net_income_margin'] = float(row['net income margin'])
                    elif 'net_income_margin' in df.columns:
                        ratios['net_income_margin'] = float(row['net_income_margin'])
                    
                    if 'ebit / interest expense' in df.columns:
                        ratios['ebit_to_interest_expense'] = float(row['ebit / interest expense'])
                    elif 'ebit_to_interest_expense' in df.columns:
                        ratios['ebit_to_interest_expense'] = float(row['ebit_to_interest_expense'])
                    
                    if 'return on assets' in df.columns:
                        ratios['return_on_assets'] = float(row['return on assets'])
                    elif 'return_on_assets' in df.columns:
                        ratios['return_on_assets'] = float(row['return_on_assets'])
                        
                except (ValueError, TypeError, KeyError) as e:
                    raise ValueError(f"Invalid or missing financial ratio values: {str(e)}")
                
                # Ensure all 5 ratios are present
                required_ratios = ['long_term_debt_to_total_capital', 'total_debt_to_ebitda', 
                                 'net_income_margin', 'ebit_to_interest_expense', 'return_on_assets']
                missing_ratios = [ratio for ratio in required_ratios if ratio not in ratios]
                if missing_ratios:
                    raise ValueError(f"Missing financial ratios: {', '.join(missing_ratios)}")
                
                # Check for missing values
                if any(pd.isna(val) for val in ratios.values()):
                    raise ValueError("One or more financial ratios are missing")
                
                # Make prediction using new ML service
                prediction_result = ml_model.predict_default_probability(ratios)
                
                # Check for prediction errors
                if "error" in prediction_result:
                    raise ValueError(f"Prediction failed: {prediction_result['error']}")
                
                # Get reporting info from Excel or use defaults
                reporting_year = str(row.get('reporting_year', '')).strip() if pd.notna(row.get('reporting_year')) else None
                reporting_quarter = str(row.get('reporting_quarter', '')).strip() if pd.notna(row.get('reporting_quarter')) else None
                
                saved_prediction = prediction_service.save_prediction(
                    company.id, 
                    prediction_result, 
                    ratios,
                    reporting_year,
                    reporting_quarter
                )
                
                result_item = {
                    "company_name": company_name,
                    "stock_symbol": stock_symbol,
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
                result_item = {
                    "company_name": str(row.get('company_name', 'Unknown')),
                    "stock_symbol": str(row.get('stock_symbol', 'Unknown')),
                    "sector": str(row.get('sector', '')) if pd.notna(row.get('sector')) else None,
                    "market_cap": float(row.get('market_cap', 0)) if pd.notna(row.get('market_cap')) else None,
                    "prediction": {},
                    "status": "error",
                    "error_message": str(e)
                }
                
                results.append(result_item)
                failed_predictions += 1
                print(f"Error processing row {index + 1}: {e}")
                
                db.rollback()
        
        prediction_service.commit_transaction()
        
        processing_time = time.time() - start_time
        
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
        db.rollback()
        error_message = str(e)
        error_traceback = traceback.format_exc()
        
        print(f"Bulk prediction task failed: {error_message}")
        print(f"Traceback: {error_traceback}")
        
        # Fix Celery exception serialization issue
        self.update_state(
            state="FAILURE",
            meta={
                "error": error_message,
                "traceback": error_traceback,
                "filename": original_filename,
                "processed": successful_predictions + failed_predictions,
                "exc_type": type(e).__name__,
                "exc_message": error_message
            }
        )
        
        # Re-raise with proper exception type
        raise type(e)(error_message)
        
    finally:
        try:
            db.close()
        except Exception:
            pass
