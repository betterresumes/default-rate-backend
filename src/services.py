from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import and_, or_, desc
from .database import Company, User, OTPToken, UserSession, AnnualPrediction, QuarterlyPrediction
from .schemas import CompanyCreate, PredictionRequest
from typing import Optional, List
from datetime import datetime, timedelta

from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import and_, or_, desc
from .database import Company, User, OTPToken, UserSession, AnnualPrediction, QuarterlyPrediction
from .schemas import CompanyCreate, PredictionRequest
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

class CompanyService:
    def __init__(self, db: Session):
        self.db = db

    def get_companies_with_predictions(
        self,
        page: int = 1,
        limit: int = 10,
        sector: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "name",
        sort_order: str = "asc"
    ):
        """Get paginated list of companies with their predictions"""
        skip = (page - 1) * limit
        take = min(limit, 100)

        query = self.db.query(Company).options(
            joinedload(Company.annual_predictions),
            joinedload(Company.quarterly_predictions)
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

        # Count query
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

    def get_company_by_id(self, company_id: str):
        """Get company by ID with all predictions"""
        return self.db.query(Company).options(
            joinedload(Company.annual_predictions),
            joinedload(Company.quarterly_predictions)
        ).filter(Company.id == company_id).first()

    def get_company_by_symbol(self, symbol: str):
        """Get company by symbol with all predictions"""
        return self.db.query(Company).options(
            joinedload(Company.annual_predictions),
            joinedload(Company.quarterly_predictions)
        ).filter(Company.symbol == symbol.upper()).first()

    def get_all_companies(self):
        """Get all companies with predictions for testing"""
        return self.db.query(Company).options(
            joinedload(Company.annual_predictions),
            joinedload(Company.quarterly_predictions)
        ).all()

    def create_company(self, symbol: str, name: str, market_cap: float, sector: str):
        """Create a new company (for router compatibility)"""
        return self.create_or_get_company(symbol, name, market_cap, sector)

    def get_company_by_symbol_and_type(self, symbol: str, prediction_type: str):
        """Get company by symbol if it has the specified prediction type"""
        company = self.get_company_by_symbol(symbol)
        if not company:
            return None
            
        if prediction_type == "annual" and company.annual_predictions:
            return company
        elif prediction_type == "quarterly" and company.quarterly_predictions:
            return company
        else:
            return None

    def create_or_get_company(self, symbol: str, name: str, market_cap: float, sector: str):
        """Create a new company or get existing one by symbol"""
        existing_company = self.get_company_by_symbol(symbol)
        
        if existing_company:
            # Update company info if needed
            existing_company.name = name
            existing_company.market_cap = market_cap
            existing_company.sector = sector
            existing_company.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing_company)
            return existing_company
        else:
            # Create new company
            company = Company(
                symbol=symbol.upper(),
                name=name,
                market_cap=market_cap,
                sector=sector
            )
            self.db.add(company)
            self.db.commit()
            self.db.refresh(company)
            return company

    def create_annual_prediction(
        self, 
        company: Company, 
        financial_data: Dict[str, Any], 
        prediction_results: Dict[str, Any],
        reporting_year: Optional[str] = None,
        reporting_quarter: Optional[str] = None
    ):
        """Create annual prediction for a company"""
        annual_prediction = AnnualPrediction(
            company_id=company.id,
            reporting_year=reporting_year,
            reporting_quarter=reporting_quarter,
            long_term_debt_to_total_capital=financial_data['long_term_debt_to_total_capital'],
            total_debt_to_ebitda=financial_data['total_debt_to_ebitda'],
            net_income_margin=financial_data['net_income_margin'],
            ebit_to_interest_expense=financial_data['ebit_to_interest_expense'],
            return_on_assets=financial_data['return_on_assets'],
            probability=prediction_results['probability'],
            risk_level=prediction_results['risk_level'],
            confidence=prediction_results['confidence']
        )
        
        self.db.add(annual_prediction)
        self.db.commit()
        self.db.refresh(annual_prediction)
        return annual_prediction

    def create_quarterly_prediction(
        self,
        company: Company,
        financial_data: Dict[str, Any],
        prediction_results: Dict[str, Any],
        reporting_year: str,
        reporting_quarter: str
    ):
        """Create quarterly prediction for a company"""
        quarterly_prediction = QuarterlyPrediction(
            company_id=company.id,
            reporting_year=reporting_year,
            reporting_quarter=reporting_quarter,
            total_debt_to_ebitda=financial_data['total_debt_to_ebitda'],
            sga_margin=financial_data['sga_margin'],
            long_term_debt_to_total_capital=financial_data['long_term_debt_to_total_capital'],
            return_on_capital=financial_data['return_on_capital'],
            logistic_probability=prediction_results['logistic_probability'],
            gbm_probability=prediction_results['gbm_probability'],
            ensemble_probability=prediction_results['ensemble_probability'],
            risk_level=prediction_results['risk_level'],
            confidence=prediction_results['confidence']
        )
        
        self.db.add(quarterly_prediction)
        self.db.commit()
        self.db.refresh(quarterly_prediction)
        return quarterly_prediction

    def get_annual_prediction(self, company_id: str, reporting_year: Optional[str] = None):
        """Get annual prediction for a company"""
        query = self.db.query(AnnualPrediction).filter(AnnualPrediction.company_id == company_id)
        if reporting_year:
            query = query.filter(AnnualPrediction.reporting_year == reporting_year)
        return query.order_by(desc(AnnualPrediction.created_at)).first()

    def get_quarterly_prediction(self, company_id: str, reporting_year: str, reporting_quarter: str):
        """Get specific quarterly prediction for a company"""
        return self.db.query(QuarterlyPrediction).filter(
            QuarterlyPrediction.company_id == company_id,
            QuarterlyPrediction.reporting_year == reporting_year,
            QuarterlyPrediction.reporting_quarter == reporting_quarter
        ).first()

    def update_annual_prediction(
        self,
        prediction_id: str,
        financial_data: Dict[str, Any],
        prediction_results: Dict[str, Any]
    ):
        """Update existing annual prediction"""
        prediction = self.db.query(AnnualPrediction).filter(AnnualPrediction.id == prediction_id).first()
        if not prediction:
            return None

        # Update financial data
        for field, value in financial_data.items():
            if hasattr(prediction, field) and value is not None:
                setattr(prediction, field, value)

        # Update prediction results
        prediction.probability = prediction_results['probability']
        prediction.risk_level = prediction_results['risk_level']
        prediction.confidence = prediction_results['confidence']
        prediction.predicted_at = datetime.utcnow()
        prediction.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(prediction)
        return prediction

    def update_quarterly_prediction(
        self,
        prediction_id: str,
        financial_data: Dict[str, Any],
        prediction_results: Dict[str, Any]
    ):
        """Update existing quarterly prediction"""
        prediction = self.db.query(QuarterlyPrediction).filter(QuarterlyPrediction.id == prediction_id).first()
        if not prediction:
            return None

        # Update financial data
        for field, value in financial_data.items():
            if hasattr(prediction, field) and value is not None:
                setattr(prediction, field, value)

        # Update prediction results
        prediction.logistic_probability = prediction_results['logistic_probability']
        prediction.gbm_probability = prediction_results['gbm_probability']
        prediction.ensemble_probability = prediction_results['ensemble_probability']
        prediction.risk_level = prediction_results['risk_level']
        prediction.confidence = prediction_results['confidence']
        prediction.predicted_at = datetime.utcnow()
        prediction.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(prediction)
        return prediction

    def delete_company_and_predictions(self, company_id: str):
        """Delete company and all its predictions"""
        company = self.get_company_by_id(company_id)
        if not company:
            return False

        self.db.delete(company)  # Cascade will delete predictions
        self.db.commit()
        return True


class PredictionService:
    def __init__(self, db: Session):
        self.db = db

    def get_prediction_summary(self, company_id: str):
        """Get summary of all predictions for a company"""
        annual_predictions = self.db.query(AnnualPrediction).filter(
            AnnualPrediction.company_id == company_id
        ).order_by(desc(AnnualPrediction.created_at)).all()
        
        quarterly_predictions = self.db.query(QuarterlyPrediction).filter(
            QuarterlyPrediction.company_id == company_id
        ).order_by(desc(QuarterlyPrediction.created_at)).all()
        
        return {
            "annual_predictions": annual_predictions,
            "quarterly_predictions": quarterly_predictions
        }


class DatabaseService:
    def __init__(self, db: Session):
        self.db = db

    def reset_table(self, table_name: str = None):
        """Reset specific table or all tables"""
        from .database import Base, Company, AnnualPrediction, QuarterlyPrediction, User, OTPToken, UserSession
        
        tables_reset = []
        affected_records = 0
        
        if table_name:
            if table_name.lower() == "companies":
                count = self.db.query(Company).count()
                self.db.query(Company).delete()
                tables_reset.append("companies")
                affected_records += count
                
            elif table_name.lower() == "annual_predictions":
                count = self.db.query(AnnualPrediction).count()
                self.db.query(AnnualPrediction).delete()
                tables_reset.append("annual_predictions")
                affected_records += count
                
            elif table_name.lower() == "quarterly_predictions":
                count = self.db.query(QuarterlyPrediction).count()
                self.db.query(QuarterlyPrediction).delete()
                tables_reset.append("quarterly_predictions")
                affected_records += count
                
            elif table_name.lower() == "users":
                count = self.db.query(User).count()
                self.db.query(User).delete()
                tables_reset.append("users")
                affected_records += count
                
            elif table_name.lower() == "otp_tokens":
                count = self.db.query(OTPToken).count()
                self.db.query(OTPToken).delete()
                tables_reset.append("otp_tokens")
                affected_records += count
                
            elif table_name.lower() == "user_sessions":
                count = self.db.query(UserSession).count()
                self.db.query(UserSession).delete()
                tables_reset.append("user_sessions")
                affected_records += count
            else:
                raise ValueError(f"Unknown table: {table_name}")
        else:
            # Reset all tables
            count_companies = self.db.query(Company).count()
            count_annual = self.db.query(AnnualPrediction).count()
            count_quarterly = self.db.query(QuarterlyPrediction).count()
            count_otp = self.db.query(OTPToken).count()
            count_sessions = self.db.query(UserSession).count()
            count_users = self.db.query(User).count()
            
            self.db.query(AnnualPrediction).delete()
            self.db.query(QuarterlyPrediction).delete()
            self.db.query(Company).delete()
            self.db.query(OTPToken).delete()
            self.db.query(UserSession).delete()
            self.db.query(User).delete()
            
            tables_reset = ["annual_predictions", "quarterly_predictions", "companies", "otp_tokens", "user_sessions", "users"]
            affected_records = count_companies + count_annual + count_quarterly + count_otp + count_sessions + count_users
        
        self.db.commit()
        return {
            "tables_reset": tables_reset,
            "affected_records": affected_records
        }
