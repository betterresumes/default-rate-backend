#!/usr/bin/env python3
import os
import pandas as pd
from .database import get_session_local
from .services import CompanyService, PredictionService
from .ml_service import ml_service


def process_bulk_predictions(file_path: str) -> dict:
    """Worker function to process an Excel file and create predictions.
    Returns summary dict with counts.
    """
    session_factory = get_session_local()
    db = session_factory()
    processed = 0
    succeeded = 0
    failed = 0
    errors = []  # Track errors for debugging
    try:
        df = pd.read_excel(file_path)
        required_cols = {"stock_symbol", "company_name"}
        if not required_cols.issubset(set(c.lower() for c in df.columns)):
            raise ValueError("Excel must contain stock_symbol and company_name columns")
        df.columns = [c.lower() for c in df.columns]

        company_service = CompanyService(db)
        prediction_service = PredictionService(db)

        for _, row in df.iterrows():
            processed += 1
            try:
                symbol = str(row.get("stock_symbol"))
                name = str(row.get("company_name"))
                market_cap = row.get("market_cap")
                sector = row.get("sector")

                company = company_service.get_company_by_symbol(symbol)
                if not company:
                    from .schemas import CompanyCreate
                    company = company_service.create_company(CompanyCreate(
                        symbol=symbol,
                        name=name,
                        market_cap=market_cap,
                        sector=sector
                    ))

                ratios = {
                    "debt_to_equity_ratio": row.get("debt_to_equity_ratio"),
                    "current_ratio": row.get("current_ratio"),
                    "quick_ratio": row.get("quick_ratio"),
                    "return_on_equity": row.get("return_on_equity"),
                    "return_on_assets": row.get("return_on_assets"),
                    "profit_margin": row.get("profit_margin"),
                    "interest_coverage": row.get("interest_coverage"),
                    "fixed_asset_turnover": row.get("fixed_asset_turnover"),
                    "total_debt_ebitda": row.get("total_debt_ebitda"),
                }

                prediction_result = ml_service.predict_default_probability(ratios)
                prediction_service.save_prediction(company.id, prediction_result, ratios)
                prediction_service.save_financial_ratios(company.id, ratios)
                prediction_service.commit_transaction()
                succeeded += 1
            except Exception as e:
                db.rollback()
                failed += 1
                errors.append(f"Row {processed}: {str(e)}")
                print(f"Error processing row {processed}: {e}")  # Debug logging

        return {
            "processed": processed, 
            "succeeded": succeeded, 
            "failed": failed,
            "errors": errors[:5]  # Return first 5 errors for debugging
        }
    finally:
        try:
            db.close()
        except Exception:
            pass
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass


