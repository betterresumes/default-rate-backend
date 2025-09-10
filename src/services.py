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

    def create_company(self, company_data: CompanyCreate, created_by_id: Optional[int] = None):
        """Create a new company"""
        company = Company(
            symbol=company_data.symbol.upper(),
            name=company_data.name,
            market_cap=company_data.market_cap,
            sector=company_data.sector,
            created_by_id=created_by_id
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

    def save_prediction(self, company_id: int, prediction_data: dict, ratios: dict):
        """Save prediction results to database (optimized - no immediate commit)"""
        prediction = DefaultRatePrediction(
            company_id=company_id,
            risk_level=prediction_data["risk_level"],
            confidence=prediction_data["confidence"],
            probability=prediction_data.get("probability"),
            debt_to_equity_ratio=ratios.get("debt_to_equity_ratio"),
            current_ratio=ratios.get("current_ratio"),
            quick_ratio=ratios.get("quick_ratio"),
            return_on_equity=ratios.get("return_on_equity"),
            return_on_assets=ratios.get("return_on_assets"),
            profit_margin=ratios.get("profit_margin"),
            interest_coverage=ratios.get("interest_coverage")
        )
        
        self.db.add(prediction)
        self.db.flush()
        return prediction

    def save_financial_ratios(self, company_id: int, ratios: dict):
        """Save or update financial ratios for a company (optimized - no immediate commit)"""
        existing_ratio = self.db.query(FinancialRatio).filter(
            FinancialRatio.company_id == company_id
        ).first()

        if existing_ratio:
            for key, value in ratios.items():
                if value is not None and hasattr(existing_ratio, key):
                    setattr(existing_ratio, key, value)
            existing_ratio.updated_at = datetime.utcnow()
            return existing_ratio
        else:
            financial_ratio = FinancialRatio(
                company_id=company_id,
                **{k: v for k, v in ratios.items() if v is not None}
            )
            self.db.add(financial_ratio)
            self.db.flush() 
            return financial_ratio

    def commit_transaction(self):
        """Commit the current transaction"""
        self.db.commit()
