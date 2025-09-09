#!/usr/bin/env python3

from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.types import Numeric
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
import os

Base = declarative_base()


class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    market_cap = Column(Numeric(precision=20, scale=2), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Direct sector field instead of foreign key
    sector = Column(String, nullable=True)
    ratios = relationship("FinancialRatio", back_populates="company", cascade="all, delete-orphan")
    predictions = relationship("DefaultRatePrediction", back_populates="company", cascade="all, delete-orphan")

class FinancialRatio(Base):
    __tablename__ = "financial_ratios"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    
    debt_to_equity_ratio = Column(Numeric(precision=10, scale=4), nullable=True)
    current_ratio = Column(Numeric(precision=10, scale=4), nullable=True)
    quick_ratio = Column(Numeric(precision=10, scale=4), nullable=True)
    return_on_equity = Column(Numeric(precision=10, scale=4), nullable=True)
    return_on_assets = Column(Numeric(precision=10, scale=4), nullable=True)
    profit_margin = Column(Numeric(precision=10, scale=4), nullable=True)
    interest_coverage = Column(Numeric(precision=10, scale=4), nullable=True)
    fixed_asset_turnover = Column(Numeric(precision=10, scale=4), nullable=True)
    total_debt_ebitda = Column(Numeric(precision=10, scale=4), nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="ratios")

class DefaultRatePrediction(Base):
    __tablename__ = "default_rate_predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    
    risk_level = Column(String, nullable=False)
    confidence = Column(Numeric(precision=5, scale=4), nullable=False)
    probability = Column(Numeric(precision=5, scale=4), nullable=True)
    
    # Store the ratios used for this prediction
    debt_to_equity_ratio = Column(Numeric(precision=10, scale=4), nullable=True)
    current_ratio = Column(Numeric(precision=10, scale=4), nullable=True)
    quick_ratio = Column(Numeric(precision=10, scale=4), nullable=True)
    return_on_equity = Column(Numeric(precision=10, scale=4), nullable=True)
    return_on_assets = Column(Numeric(precision=10, scale=4), nullable=True)
    profit_margin = Column(Numeric(precision=10, scale=4), nullable=True)
    interest_coverage = Column(Numeric(precision=10, scale=4), nullable=True)
    fixed_asset_turnover = Column(Numeric(precision=10, scale=4), nullable=True)
    total_debt_ebitda = Column(Numeric(precision=10, scale=4), nullable=True)
    
    predicted_at = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="predictions")

# Database setup
def get_database_url():
    # Railway will provide DATABASE_URL automatically
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        # Fallback for local development
        database_url = "postgresql://neondb_owner:npg_2ZLE4VuBytOa@ep-crimson-cell-adrxvu8a-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require"
    return database_url

# Create engine once at module level with connection pooling
engine = create_engine(
    get_database_url(),
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False  # Set to True for SQL debugging
)

# Create SessionLocal factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_database_engine():
    return engine

def get_session_local():
    return SessionLocal

def create_tables():
    Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
