import os
import pandas as pd
import time
import traceback
import io
import base64
import math
from typing import Dict, Any
from celery import current_task
from .celery_app import celery_app
from .database import get_session_local
from .services import CompanyService
from .schemas import CompanyCreate
from .ml_service import ml_model
from .email_service import email_service


def safe_float(value):
    """Convert value to float, handling None and NaN values"""
    if value is None:
        return None
    try:
        float_val = float(value)
        # Check if it's NaN or infinite
        if math.isnan(float_val) or math.isinf(float_val):
            return None
        return float_val
    except (ValueError, TypeError):
        return None


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
            'stock_symbol', 'company_name',
            'long_term_debt_to_total_capital', 'total_debt_to_ebitda', 
            'net_income_margin', 'ebit_to_interest_expense', 'return_on_assets'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
        
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
                
                stock_symbol = str(row['stock_symbol']).strip()
                company_name = str(row['company_name']).strip()
                
                if not stock_symbol or not company_name:
                    raise ValueError("Stock symbol and company name are required")
                
                market_cap = row.get('market_cap', 1000000000)  
                if pd.isna(market_cap):
                    market_cap = 1000000000
                else:
                    market_cap = safe_float(market_cap)
                
                sector = row.get('sector', 'Unknown')
                if pd.isna(sector):
                    sector = 'Unknown'
                else:
                    sector = str(sector).strip()
                
                reporting_year = row.get('reporting_year')
                if pd.isna(reporting_year):
                    reporting_year = None
                else:
                    reporting_year = str(reporting_year).strip()
                
                reporting_quarter = row.get('reporting_quarter')
                if pd.isna(reporting_quarter):
                    reporting_quarter = None
                else:
                    reporting_quarter = str(reporting_quarter).strip()
                
                ratios = {
                    'long_term_debt_to_total_capital': safe_float(row['long_term_debt_to_total_capital']),
                    'total_debt_to_ebitda': safe_float(row['total_debt_to_ebitda']),
                    'net_income_margin': safe_float(row['net_income_margin']),
                    'ebit_to_interest_expense': safe_float(row['ebit_to_interest_expense']),
                    'return_on_assets': safe_float(row['return_on_assets'])
                }
                
                prediction_result = ml_model.predict_default_probability(ratios)
                
                if "error" in prediction_result:
                    raise ValueError(f"Prediction failed: {prediction_result['error']}")
                
                company_data = CompanyCreate(
                    symbol=stock_symbol,
                    name=company_name,
                    market_cap=market_cap,
                    sector=sector,
                    reporting_year=reporting_year,
                    reporting_quarter=reporting_quarter,
                    long_term_debt_to_total_capital=ratios['long_term_debt_to_total_capital'],
                    total_debt_to_ebitda=ratios['total_debt_to_ebitda'],
                    net_income_margin=ratios['net_income_margin'],
                    ebit_to_interest_expense=ratios['ebit_to_interest_expense'],
                    return_on_assets=ratios['return_on_assets']
                )
                
                # Save to database using single table structure with upsert
                company = company_service.upsert_company(company_data, prediction_result)
                
                result_item = {
                    "company_name": company_name,
                    "stock_symbol": stock_symbol,
                    "sector": company.sector,
                    "market_cap": safe_float(company.market_cap),
                    "prediction": {
                        "id": str(company.id),
                        "risk_level": company.risk_level,
                        "confidence": safe_float(company.confidence),
                        "probability": safe_float(company.probability) if company.probability else None,
                        "predicted_at": company.predicted_at.isoformat() if company.predicted_at else None,
                        "financial_ratios": {
                            "long_term_debt_to_total_capital": safe_float(company.long_term_debt_to_total_capital),
                            "total_debt_to_ebitda": safe_float(company.total_debt_to_ebitda),
                            "net_income_margin": safe_float(company.net_income_margin),
                            "ebit_to_interest_expense": safe_float(company.ebit_to_interest_expense),
                            "return_on_assets": safe_float(company.return_on_assets)
                        }
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
                    "market_cap": safe_float(row.get('market_cap', 0)) if pd.notna(row.get('market_cap')) else None,
                    "prediction": {},
                    "status": "error",
                    "error_message": str(e)
                }
                
                results.append(result_item)
                failed_predictions += 1
                print(f"Error processing row {index + 1}: {e}")
                
                db.rollback()
        
        db.commit()  
        
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
        
        raise type(e)(error_message)
        
    finally:
        try:
            db.close()
        except Exception:
            pass


@celery_app.task(bind=True, name="src.tasks.process_bulk_normalized_task")
def process_bulk_normalized_task(self, file_content_b64: str, original_filename: str, prediction_type: str = "annual") -> Dict[str, Any]:
    """
    Background task to process CSV/Excel file with multiple companies for bulk predictions.
    Uses the new normalized database schema (companies, annual_predictions, quarterly_predictions).
    
    Args:
        file_content_b64: Base64 encoded content of the uploaded file
        original_filename: Original name of the uploaded file
        prediction_type: "annual" or "quarterly"
        
    Returns:
        Dictionary with processing results
    """
    task_id = self.request.id
    start_time = time.time()
    
    self.update_state(
        state="PROGRESS",
        meta={
            "status": f"Starting {prediction_type} bulk prediction processing...",
            "current": 0,
            "total": 0,
            "filename": original_filename,
            "prediction_type": prediction_type
        }
    )
    
    session_factory = get_session_local()
    db = session_factory()
    
    results = []
    successful_predictions = 0
    failed_predictions = 0
    total_companies = 0
    
    try:
        # Decode and read file
        file_content = base64.b64decode(file_content_b64)
        
        if original_filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(file_content.decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(file_content))
        
        total_companies = len(df)
        
        # Validate required columns based on prediction type
        if prediction_type == "annual":
            required_columns = [
                'stock_symbol', 'company_name',
                'long_term_debt_to_total_capital', 'total_debt_to_ebitda', 
                'net_income_margin', 'ebit_to_interest_expense', 'return_on_assets'
            ]
        else:  # quarterly
            required_columns = [
                'stock_symbol', 'company_name', 'reporting_year', 'reporting_quarter',
                'total_debt_to_ebitda', 'sga_margin', 
                'long_term_debt_to_total_capital', 'return_on_capital'
            ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
        
        # Optional columns with defaults
        optional_columns = {
            'market_cap': 1000000000,
            'sector': 'Unknown',
            'reporting_year': '2024',
        }
        
        if prediction_type == "quarterly":
            optional_columns['reporting_quarter'] = 'Q4'
        
        # Add missing optional columns
        for col, default_value in optional_columns.items():
            if col not in df.columns:
                df[col] = default_value
        
        company_service = CompanyService(db)
        
        # Process each company
        for index, row in df.iterrows():
            try:
                # Update progress
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "status": f"Processing company {index + 1} of {total_companies}...",
                        "current": index + 1,
                        "total": total_companies,
                        "filename": original_filename,
                        "successful": successful_predictions,
                        "failed": failed_predictions,
                        "prediction_type": prediction_type
                    }
                )
                
                # Validate required data
                stock_symbol = str(row['stock_symbol']).strip().upper()
                company_name = str(row['company_name']).strip()
                
                if not stock_symbol or not company_name or stock_symbol.lower() == 'nan' or company_name.lower() == 'nan':
                    raise ValueError("Stock symbol and company name are required")
                
                # Handle optional fields
                market_cap = row.get('market_cap', 1000000000)
                if pd.isna(market_cap):
                    market_cap = 1000000000
                else:
                    market_cap = safe_float(market_cap)
                
                sector = row.get('sector', 'Unknown')
                if pd.isna(sector):
                    sector = 'Unknown'
                else:
                    sector = str(sector).strip()
                
                reporting_year = str(row.get('reporting_year', '2024')).strip()
                
                # Create or get company
                company = company_service.create_company(
                    symbol=stock_symbol,
                    name=company_name,
                    market_cap=market_cap,
                    sector=sector
                )
                
                if prediction_type == "annual":
                    # Annual prediction
                    ratios = {
                        'long_term_debt_to_total_capital': safe_float(row['long_term_debt_to_total_capital']),
                        'total_debt_to_ebitda': safe_float(row['total_debt_to_ebitda']),
                        'net_income_margin': safe_float(row['net_income_margin']),
                        'ebit_to_interest_expense': safe_float(row['ebit_to_interest_expense']),
                        'return_on_assets': safe_float(row['return_on_assets'])
                    }
                    
                    prediction_result = ml_model.predict_default_probability(ratios)
                    
                    if "error" in prediction_result:
                        raise ValueError(f"Annual prediction failed: {prediction_result['error']}")
                    
                    # Create annual prediction
                    annual_prediction = company_service.create_annual_prediction(
                        company=company,
                        financial_data=ratios,
                        prediction_results=prediction_result,
                        reporting_year=reporting_year
                    )
                    
                    result_item = {
                        "stock_symbol": stock_symbol,
                        "company_name": company_name,
                        "sector": sector,
                        "market_cap": market_cap,
                        "prediction": {
                            "id": str(annual_prediction.id),
                            "type": "annual",
                            "probability": safe_float(annual_prediction.probability),
                            "primary_probability": safe_float(annual_prediction.probability),
                            "risk_level": annual_prediction.risk_level,
                            "confidence": safe_float(annual_prediction.confidence),
                            "reporting_year": annual_prediction.reporting_year,
                            "financial_ratios": ratios
                        },
                        "status": "success",
                        "error_message": None
                    }
                    
                else:  # quarterly
                    # Quarterly prediction
                    reporting_quarter = str(row['reporting_quarter']).strip()
                    
                    ratios = {
                        'total_debt_to_ebitda': safe_float(row['total_debt_to_ebitda']),
                        'sga_margin': safe_float(row['sga_margin']),
                        'long_term_debt_to_total_capital': safe_float(row['long_term_debt_to_total_capital']),
                        'return_on_capital': safe_float(row['return_on_capital'])
                    }
                    
                    from .quarterly_ml_service import quarterly_ml_model
                    prediction_result = quarterly_ml_model.predict_default_probability(ratios)
                    
                    if "error" in prediction_result:
                        raise ValueError(f"Quarterly prediction failed: {prediction_result['error']}")
                    
                    # Create quarterly prediction
                    quarterly_prediction = company_service.create_quarterly_prediction(
                        company=company,
                        financial_data=ratios,
                        prediction_results=prediction_result,
                        reporting_year=reporting_year,
                        reporting_quarter=reporting_quarter
                    )
                    
                    result_item = {
                        "stock_symbol": stock_symbol,
                        "company_name": company_name,
                        "sector": sector,
                        "market_cap": market_cap,
                        "prediction": {
                            "id": str(quarterly_prediction.id),
                            "type": "quarterly",
                            "probabilities": {
                                "logistic": safe_float(quarterly_prediction.logistic_probability),
                                "gbm": safe_float(quarterly_prediction.gbm_probability),
                                "ensemble": safe_float(quarterly_prediction.ensemble_probability)
                            },
                            "primary_probability": safe_float(quarterly_prediction.ensemble_probability),
                            "risk_level": quarterly_prediction.risk_level,
                            "confidence": safe_float(quarterly_prediction.confidence),
                            "reporting_year": quarterly_prediction.reporting_year,
                            "reporting_quarter": quarterly_prediction.reporting_quarter,
                            "financial_ratios": ratios
                        },
                        "status": "success",
                        "error_message": None
                    }
                
                results.append(result_item)
                successful_predictions += 1
                
            except Exception as e:
                # Handle individual company prediction failure
                result_item = {
                    "stock_symbol": str(row.get('stock_symbol', 'Unknown')),
                    "company_name": str(row.get('company_name', 'Unknown')),
                    "sector": str(row.get('sector', 'Unknown')),
                    "market_cap": safe_float(row.get('market_cap', 0)),
                    "prediction": None,
                    "status": "failed",
                    "error_message": str(e)
                }
                results.append(result_item)
                failed_predictions += 1
                print(f"Error processing row {index + 1}: {e}")
        
        processing_time = time.time() - start_time
        
        # Final result
        result = {
            "success": True,
            "message": f"Bulk {prediction_type} prediction completed. {successful_predictions} successful, {failed_predictions} failed.",
            "total_processed": total_companies,
            "successful_predictions": successful_predictions,
            "failed_predictions": failed_predictions,
            "results": results,
            "processing_time": processing_time,
            "completed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "prediction_type": prediction_type,
            "filename": original_filename
        }
        
        return result
        
    except Exception as e:
        error_msg = f"Bulk processing failed: {str(e)}"
        print(f"Task {task_id} failed: {error_msg}")
        print(f"Traceback: {traceback.format_exc()}")
        
        # Return error result
        return {
            "success": False,
            "message": error_msg,
            "total_processed": total_companies,
            "successful_predictions": successful_predictions,
            "failed_predictions": failed_predictions,
            "results": results,
            "processing_time": time.time() - start_time,
            "error": error_msg,
            "prediction_type": prediction_type,
            "filename": original_filename
        }
    
    finally:
        db.close()
