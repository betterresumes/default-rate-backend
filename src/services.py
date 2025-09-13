from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import and_, or_, desc
from .database import Company, FinancialRatio, DefaultRatePrediction
from .schemas import CompanyCreate, PredictionRequest
from typing import Optional, List
from datetime import datetime, timedelta

class CompanyService:
    def __init__(self, db: Session):
        self.db = db

    def get_companies(
        self,
        page: int = 1,
        limit: int = 10,
        sector: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "name",
        sort_order: str = "asc"
    ):
        """Get paginated list of companies with filtering and sorting"""
        skip = (page - 1) * limit
        take = min(limit, 100) 

        query = self.db.query(Company).options(
            selectinload(Company.ratios),
            selectinload(Company.predictions)
        )

        if sector:
            query = query.filter(Company.sector.ilike(f"%{sector}%"))

        if search:
            search_filter = or_(
                Company.name.ilike(f"%{search}%"),
                Company.symbol.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)

        valid_sort_fields = ["name", "symbol", "market_cap", "created_at"]
        if sort_by in valid_sort_fields:
            sort_column = getattr(Company, sort_by)
            if sort_order == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(sort_column)
        else:
            query = query.order_by(Company.name)

        count_query = self.db.query(Company)
        if sector:
            count_query = count_query.filter(Company.sector.ilike(f"%{sector}%"))
        if search:
            search_filter = or_(
                Company.name.ilike(f"%{search}%"),
                Company.symbol.ilike(f"%{search}%")
            )
            count_query = count_query.filter(search_filter)
        total = count_query.count()

        companies = query.offset(skip).limit(take).all()

        return {
            "companies": companies,
            "pagination": {
                "page": page,
                "limit": take,
                "total": total,
                "pages": (total + take - 1) // take,
                "has_next": skip + take < total,
                "has_prev": page > 1
            }
        }

    def get_company_by_id(self, company_id: int):
        """Get company by ID with related data"""
        return self.db.query(Company).options(
            selectinload(Company.ratios),
            selectinload(Company.predictions)
        ).filter(Company.id == company_id).first()

    def get_company_by_symbol(self, symbol: str):
        """Get company by symbol (lightweight for predictions)"""
        return self.db.query(Company).filter(Company.symbol == symbol.upper()).first()

    def get_company_by_name(self, name: str):
        """Get company by name (lightweight for predictions)"""
        return self.db.query(Company).filter(Company.name == name).first()

    def create_company(self, company_data: CompanyCreate):
        """Create a new company"""
        company = Company(
            symbol=company_data.symbol.upper(),
            name=company_data.name,
            market_cap=company_data.market_cap,
            sector=company_data.sector,
            reporting_year=company_data.reporting_year,
            reporting_quarter=company_data.reporting_quarter
        )
        
        self.db.add(company)
        self.db.commit()
        self.db.refresh(company)
        
        return company


class PredictionService:
    def __init__(self, db: Session):
        self.db = db

    def get_recent_prediction(self, company_id: int, hours: int = 24):
        """Check if there's a recent prediction for the company"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        return self.db.query(DefaultRatePrediction).filter(
            and_(
                DefaultRatePrediction.company_id == company_id,
                DefaultRatePrediction.predicted_at > cutoff_time
            )
        ).order_by(desc(DefaultRatePrediction.predicted_at)).first()

    def save_prediction(self, company_id: str, prediction_data: dict, ratios: dict, reporting_year: Optional[str] = None, reporting_quarter: Optional[str] = None):
        """Save or update prediction results to database (one prediction per company)"""
        # First, save/update the financial ratios
        financial_ratio = self.save_financial_ratios(company_id, ratios, reporting_year, reporting_quarter)
        
        # Check if company already has a prediction
        existing_prediction = self.db.query(DefaultRatePrediction).filter(
            DefaultRatePrediction.company_id == company_id
        ).first()
        
        if existing_prediction:
            # Update existing prediction
            existing_prediction.risk_level = prediction_data["risk_level"]
            existing_prediction.confidence = prediction_data["confidence"]
            existing_prediction.probability = prediction_data.get("probability")
            existing_prediction.financial_ratio_id = financial_ratio.id
            existing_prediction.predicted_at = datetime.utcnow()
            existing_prediction.updated_at = datetime.utcnow()
            
            self.db.flush()
            return existing_prediction
        else:
            # Create new prediction
            prediction = DefaultRatePrediction(
                company_id=company_id,
                financial_ratio_id=financial_ratio.id,
                risk_level=prediction_data["risk_level"],
                confidence=prediction_data["confidence"],
                probability=prediction_data.get("probability")
            )
            
            self.db.add(prediction)
            self.db.flush()
            return prediction

    def save_financial_ratios(self, company_id: str, ratios: dict, reporting_year: Optional[str] = None, reporting_quarter: Optional[str] = None):
        """Save or update financial ratios for a company (one ratio record per company)"""
        # Set defaults if not provided
        if not reporting_year:
            reporting_year = str(datetime.utcnow().year)
        if not reporting_quarter:
            # Determine quarter based on current month
            current_month = datetime.utcnow().month
            reporting_quarter = f"Q{(current_month - 1) // 3 + 1}"
        
        existing_ratio = self.db.query(FinancialRatio).filter(
            FinancialRatio.company_id == company_id
        ).first()

        if existing_ratio:
            # Update existing ratios
            for key, value in ratios.items():
                if value is not None and hasattr(existing_ratio, key):
                    setattr(existing_ratio, key, value)
            existing_ratio.updated_at = datetime.utcnow()
            existing_ratio.reporting_year = reporting_year
            existing_ratio.reporting_quarter = reporting_quarter
            self.db.flush()
            return existing_ratio
        else:
            # Create new financial ratios
            ratio_data = {k: v for k, v in ratios.items() if v is not None}
            ratio_data['company_id'] = company_id
            ratio_data['reporting_year'] = reporting_year
            ratio_data['reporting_quarter'] = reporting_quarter
                
            financial_ratio = FinancialRatio(**ratio_data)
            self.db.add(financial_ratio)
            self.db.flush() 
            return financial_ratio

    def update_prediction(self, company_id: str, update_data: dict):
        """Update existing prediction for a company with flexible field updates"""
        # Check if company exists
        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise ValueError(f"Company with ID {company_id} not found")
        
        # Check if prediction exists
        existing_prediction = self.db.query(DefaultRatePrediction).filter(
            DefaultRatePrediction.company_id == company_id
        ).first()
        
        if not existing_prediction:
            raise ValueError(f"No prediction found for company {company_id}")
        
        # Update company information if provided
        if update_data.get("company_name") is not None:
            company.name = update_data["company_name"]
        if update_data.get("market_cap") is not None:
            company.market_cap = update_data["market_cap"]
        if update_data.get("sector") is not None:
            company.sector = update_data["sector"]
        if update_data.get("reporting_year") is not None:
            company.reporting_year = update_data["reporting_year"]
        if update_data.get("reporting_quarter") is not None:
            company.reporting_quarter = update_data["reporting_quarter"]
        
        company.updated_at = datetime.utcnow()
        
        # Check if financial ratios are provided for prediction update
        financial_ratios_provided = any([
            update_data.get("long_term_debt_to_total_capital") is not None,
            update_data.get("total_debt_to_ebitda") is not None,
            update_data.get("net_income_margin") is not None,
            update_data.get("ebit_to_interest_expense") is not None,
            update_data.get("return_on_assets") is not None
        ])
        
        if financial_ratios_provided:
            # Get current financial ratios to use as defaults
            current_ratios = {}
            if existing_prediction and existing_prediction.financial_ratio:
                current_ratio = existing_prediction.financial_ratio
                current_ratios = {
                    "long_term_debt_to_total_capital": float(current_ratio.long_term_debt_to_total_capital),
                    "total_debt_to_ebitda": float(current_ratio.total_debt_to_ebitda),
                    "net_income_margin": float(current_ratio.net_income_margin),
                    "ebit_to_interest_expense": float(current_ratio.ebit_to_interest_expense),
                    "return_on_assets": float(current_ratio.return_on_assets)
                }
            
            # Prepare ratios dict with current values as defaults, updated with new values
            ratios = current_ratios.copy()
            for key in ["long_term_debt_to_total_capital", "total_debt_to_ebitda", 
                       "net_income_margin", "ebit_to_interest_expense", "return_on_assets"]:
                if update_data.get(key) is not None:
                    ratios[key] = update_data[key]
            
            # Update financial ratios
            financial_ratio = self.save_financial_ratios(
                company_id, 
                ratios, 
                update_data.get("reporting_year"), 
                update_data.get("reporting_quarter")
            )
            
            # Recalculate prediction with complete ratios (updated + existing)
            updated_prediction, prediction_result = self.recalculate_prediction(company_id, ratios)
            
            # Update prediction with new financial ratio reference
            if updated_prediction:
                updated_prediction.financial_ratio_id = financial_ratio.id
                existing_prediction = updated_prediction
        
        self.db.flush()
        return existing_prediction, company

    def delete_prediction(self, company_id: str):
        """Delete prediction for a company - deletes both prediction and financial ratios"""
        # Check if company exists
        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise ValueError(f"Company with ID {company_id} not found")
        
        # Check if prediction exists
        existing_prediction = self.db.query(DefaultRatePrediction).filter(
            DefaultRatePrediction.company_id == company_id
        ).first()
        
        if not existing_prediction:
            raise ValueError(f"No prediction found for company {company_id}")
        
        # Get the financial ratio ID before deleting prediction
        financial_ratio_id = existing_prediction.financial_ratio_id
        
        # Delete the prediction first
        print(f"🗑️ Deleting prediction {existing_prediction.id} for company {company_id}")
        self.db.delete(existing_prediction)
        
        # Delete the associated financial ratio
        if financial_ratio_id:
            financial_ratio = self.db.query(FinancialRatio).filter(
                FinancialRatio.id == financial_ratio_id
            ).first()
            if financial_ratio:
                print(f"🗑️ Deleting financial ratio {financial_ratio.id} for company {company_id}")
                self.db.delete(financial_ratio)
        
        self.db.flush()
        print(f"✅ Complete prediction data deleted successfully for company {company_id}")
        
        return company

    def get_prediction_by_company_id(self, company_id: str):
        """Get prediction for a specific company"""
        return self.db.query(DefaultRatePrediction).filter(
            DefaultRatePrediction.company_id == company_id
        ).first()
    
    def recalculate_prediction(self, company_id: str, ratios: dict):
        """Recalculate prediction using ML model with new ratios"""
        from .ml_service import ml_model
        
        # Make prediction using ML model
        prediction_result = ml_model.predict_default_probability(ratios)
        
        if "error" in prediction_result:
            raise ValueError(f"Prediction failed: {prediction_result['error']}")
        
        # Get existing prediction
        existing_prediction = self.db.query(DefaultRatePrediction).filter(
            DefaultRatePrediction.company_id == company_id
        ).first()
        
        if existing_prediction:
            # Update existing prediction
            existing_prediction.risk_level = prediction_result["risk_level"]
            existing_prediction.confidence = prediction_result["confidence"]
            existing_prediction.probability = prediction_result.get("probability")
            existing_prediction.predicted_at = datetime.utcnow()
            existing_prediction.updated_at = datetime.utcnow()
            
            self.db.flush()
            return existing_prediction, prediction_result
        
        return None, prediction_result

    def commit_transaction(self):
        """Commit the current transaction"""
        self.db.commit()
