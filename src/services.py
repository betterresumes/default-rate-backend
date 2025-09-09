from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import and_, or_, desc
from .database import Company, Sector, FinancialRatio, DefaultRatePrediction
from .schemas import CompanyCreate, SectorCreate, PredictionRequest
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
        take = min(limit, 100)  # Max 100 per page

        # Use eager loading to avoid N+1 queries
        query = self.db.query(Company).options(
            joinedload(Company.sector),
            selectinload(Company.ratios),
            selectinload(Company.predictions)
        )

        # Apply filters
        if sector:
            query = query.join(Sector).filter(Sector.slug == sector)

        if search:
            search_filter = or_(
                Company.name.ilike(f"%{search}%"),
                Company.symbol.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)

        # Apply sorting
        valid_sort_fields = ["name", "symbol", "market_cap", "created_at"]
        if sort_by in valid_sort_fields:
            sort_column = getattr(Company, sort_by)
            if sort_order == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(sort_column)
        else:
            query = query.order_by(Company.name)

        # Get total count (use a separate simpler query for count to avoid loading relationships)
        count_query = self.db.query(Company)
        if sector:
            count_query = count_query.join(Sector).filter(Sector.slug == sector)
        if search:
            search_filter = or_(
                Company.name.ilike(f"%{search}%"),
                Company.symbol.ilike(f"%{search}%")
            )
            count_query = count_query.filter(search_filter)
        total = count_query.count()

        # Apply pagination
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
        """Get paginated list of companies with minimal data (no ratios/predictions)"""
        skip = (page - 1) * limit
        take = min(limit, 100)  # Max 100 per page

        # Only load sector relationship, skip ratios and predictions
        query = self.db.query(Company).options(
            joinedload(Company.sector)
        )

        # Apply filters
        if sector:
            query = query.join(Sector).filter(Sector.slug == sector)

        if search:
            search_filter = or_(
                Company.name.ilike(f"%{search}%"),
                Company.symbol.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)

        # Apply sorting
        valid_sort_fields = ["name", "symbol", "market_cap", "created_at"]
        if sort_by in valid_sort_fields:
            sort_column = getattr(Company, sort_by)
            if sort_order == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(sort_column)
        else:
            query = query.order_by(Company.name)

        # Get total count (use a separate simpler query for count)
        count_query = self.db.query(Company)
        if sector:
            count_query = count_query.join(Sector).filter(Sector.slug == sector)
        if search:
            search_filter = or_(
                Company.name.ilike(f"%{search}%"),
                Company.symbol.ilike(f"%{search}%")
            )
            count_query = count_query.filter(search_filter)
        total = count_query.count()

        # Apply pagination
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
            joinedload(Company.sector),
            selectinload(Company.ratios),
            selectinload(Company.predictions)
        ).filter(Company.id == company_id).first()

    def get_company_by_symbol(self, symbol: str):
        """Get company by symbol (lightweight for predictions)"""
        return self.db.query(Company).options(
            joinedload(Company.sector)
        ).filter(Company.symbol == symbol.upper()).first()

    def create_company(self, company_data: CompanyCreate):
        """Create a new company"""
        # Handle sector
        sector_id = None
        if company_data.sector:
            sector = self.db.query(Sector).filter(
                Sector.name.ilike(f"%{company_data.sector}%")
            ).first()
            
            if not sector:
                # Create new sector
                sector_slug = company_data.sector.lower().replace(" ", "-")
                sector = Sector(
                    name=company_data.sector,
                    slug=sector_slug
                )
                self.db.add(sector)
                self.db.flush()  # Get the ID
            
            sector_id = sector.id

        # Create company
        company = Company(
            symbol=company_data.symbol.upper(),
            name=company_data.name,
            market_cap=company_data.market_cap,
            sector_id=sector_id
        )
        
        self.db.add(company)
        self.db.commit()
        self.db.refresh(company)
        
        return company


class SectorService:
    def __init__(self, db: Session):
        self.db = db

    def get_sectors(self):
        """Get all sectors with company count"""
        return self.db.query(Sector).options(
            selectinload(Sector.companies)
        ).order_by(Sector.name).all()

    def create_sector(self, sector_data: SectorCreate):
        """Create a new sector"""
        # Generate slug
        slug = sector_data.name.lower().replace(" ", "-").replace("_", "-")
        
        # Check if sector already exists
        existing = self.db.query(Sector).filter(
            or_(Sector.name.ilike(sector_data.name), Sector.slug == slug)
        ).first()
        
        if existing:
            raise ValueError("Sector with this name already exists")

        sector = Sector(
            name=sector_data.name.strip(),
            slug=slug,
            description=sector_data.description.strip() if sector_data.description else None
        )
        
        self.db.add(sector)
        self.db.commit()
        self.db.refresh(sector)
        
        return sector


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
        self.db.flush()  # Get ID without full commit
        return prediction

    def save_financial_ratios(self, company_id: int, ratios: dict):
        """Save or update financial ratios for a company (optimized - no immediate commit)"""
        existing_ratio = self.db.query(FinancialRatio).filter(
            FinancialRatio.company_id == company_id
        ).first()

        if existing_ratio:
            # Update existing ratios
            for key, value in ratios.items():
                if value is not None and hasattr(existing_ratio, key):
                    setattr(existing_ratio, key, value)
            existing_ratio.updated_at = datetime.utcnow()
            return existing_ratio
        else:
            # Create new ratios record
            financial_ratio = FinancialRatio(
                company_id=company_id,
                **{k: v for k, v in ratios.items() if v is not None}
            )
            self.db.add(financial_ratio)
            self.db.flush()  # Get ID without full commit
            return financial_ratio

    def commit_transaction(self):
        """Commit the current transaction"""
        self.db.commit()
