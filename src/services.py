from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import and_, or_, desc
from .database import Company, User, OTPToken, UserSession
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

        query = self.db.query(Company)

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

    def get_company_by_id(self, company_id: str):
        """Get company by ID"""
        return self.db.query(Company).filter(Company.id == company_id).first()

    def get_company_by_symbol(self, symbol: str):
        """Get company by symbol"""
        return self.db.query(Company).filter(Company.symbol == symbol.upper()).first()

    def get_company_by_name(self, name: str):
        """Get company by name"""
        return self.db.query(Company).filter(Company.name == name).first()

    def create_company(self, company_data: CompanyCreate, prediction_data: dict):
        """Create a new company with prediction data"""
        company = Company(
            symbol=company_data.symbol.upper(),
            name=company_data.name,
            market_cap=company_data.market_cap,
            sector=company_data.sector,
            reporting_year=company_data.reporting_year,
            reporting_quarter=company_data.reporting_quarter,
            long_term_debt_to_total_capital=company_data.long_term_debt_to_total_capital,
            total_debt_to_ebitda=company_data.total_debt_to_ebitda,
            net_income_margin=company_data.net_income_margin,
            ebit_to_interest_expense=company_data.ebit_to_interest_expense,
            return_on_assets=company_data.return_on_assets,
            risk_level=prediction_data["risk_level"],
            confidence=prediction_data["confidence"],
            probability=prediction_data.get("probability"),
            predicted_at=datetime.utcnow()
        )
        
        self.db.add(company)
        self.db.commit()
        self.db.refresh(company)
        
        return company

    def upsert_company(self, company_data: CompanyCreate, prediction_data: dict):
        """Create a new company or update existing one if symbol already exists"""
        existing_company = self.get_company_by_symbol(company_data.symbol)
        
        if existing_company:
            # Update existing company
            existing_company.name = company_data.name
            existing_company.market_cap = company_data.market_cap
            existing_company.sector = company_data.sector
            existing_company.reporting_year = company_data.reporting_year
            existing_company.reporting_quarter = company_data.reporting_quarter
            existing_company.long_term_debt_to_total_capital = company_data.long_term_debt_to_total_capital
            existing_company.total_debt_to_ebitda = company_data.total_debt_to_ebitda
            existing_company.net_income_margin = company_data.net_income_margin
            existing_company.ebit_to_interest_expense = company_data.ebit_to_interest_expense
            existing_company.return_on_assets = company_data.return_on_assets
            existing_company.risk_level = prediction_data["risk_level"]
            existing_company.confidence = prediction_data["confidence"]
            existing_company.probability = prediction_data.get("probability")
            existing_company.predicted_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(existing_company)
            return existing_company
        else:
            # Create new company
            return self.create_company(company_data, prediction_data)

    def update_company(self, company_id: str, update_data: dict, prediction_data: dict = None):
        """Update company information and optionally recalculate prediction"""
        company = self.get_company_by_id(company_id)
        if not company:
            return None
        
        for field, value in update_data.items():
            if value is not None and hasattr(company, field):
                if field == 'name':
                    setattr(company, field, value)
                else:
                    setattr(company, field, value)
        
        if prediction_data:
            company.risk_level = prediction_data["risk_level"]
            company.confidence = prediction_data["confidence"]
            company.probability = prediction_data.get("probability")
            company.predicted_at = datetime.utcnow()
        
        company.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(company)
        return company

    def delete_company_data(self, company_id: str):
        """Delete company (all data is in one table now)"""
        company = self.get_company_by_id(company_id)
        if not company:
            return False
        
        self.db.delete(company)
        self.db.commit()
        return True


class PredictionService:
    def __init__(self, db: Session):
        self.db = db

    def save_or_update_company_prediction(self, company_id: str, prediction_data: dict, ratios: dict, reporting_year: Optional[str] = None, reporting_quarter: Optional[str] = None):
        """Update existing company with new prediction and ratios"""
        company = self.db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return None
        
        for key, value in ratios.items():
            if value is not None and hasattr(company, key):
                setattr(company, key, value)
        
        company.risk_level = prediction_data["risk_level"]
        company.confidence = prediction_data["confidence"]
        company.probability = prediction_data.get("probability")
        company.predicted_at = datetime.utcnow()
        
        if reporting_year:
            company.reporting_year = reporting_year
        if reporting_quarter:
            company.reporting_quarter = reporting_quarter
        
        company.updated_at = datetime.utcnow()
        self.db.flush()
        return company

    def commit_transaction(self):
        """Commit the current transaction"""
        self.db.commit()


class DatabaseService:
    def __init__(self, db: Session):
        self.db = db

    def reset_table(self, table_name: str = None):
        """Reset specific table or all tables"""
        from .database import Base, Company, User, OTPToken, UserSession
        
        tables_reset = []
        affected_records = 0
        
        if table_name:
            if table_name.lower() == "companies":
                count = self.db.query(Company).count()
                self.db.query(Company).delete()
                tables_reset.append("companies")
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
            count_companies = self.db.query(Company).count()
            count_otp = self.db.query(OTPToken).count()
            count_sessions = self.db.query(UserSession).count()
            count_users = self.db.query(User).count()
            
            self.db.query(Company).delete()
            self.db.query(OTPToken).delete()
            self.db.query(UserSession).delete()
            self.db.query(User).delete()
            
            tables_reset = ["companies", "otp_tokens", "user_sessions", "users"]
            affected_records = count_companies + count_otp + count_sessions + count_users
        
        self.db.commit()
        return {
            "tables_reset": tables_reset,
            "affected_records": affected_records
        }
