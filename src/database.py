#!/usr/bin/env python3

from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.types import Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
import os
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=False)  
    is_verified = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    role = Column(String, default="user")  
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, nullable=True)
    
    # Removed company relationship as requested
    otp_tokens = relationship("OTPToken", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

class OTPToken(Base):
    __tablename__ = "otp_tokens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token = Column(String, nullable=False)
    token_type = Column(String, nullable=False)  
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    
    user = relationship("User", back_populates="otp_tokens")

class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    session_token = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    user_agent = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    last_accessed = Column(DateTime, default=func.now())
    
    user = relationship("User", back_populates="sessions")

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    symbol = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    market_cap = Column(Numeric(precision=20, scale=2), nullable=False)
    sector = Column(String, nullable=False)
    reporting_year = Column(String, nullable=True)
    reporting_quarter = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Removed user relationship as requested
    ratios = relationship("FinancialRatio", back_populates="company", cascade="all, delete-orphan")
    predictions = relationship("DefaultRatePrediction", back_populates="company", cascade="all, delete-orphan")

class FinancialRatio(Base):
    __tablename__ = "financial_ratios"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    
    # Required ratios for ML model
    long_term_debt_to_total_capital = Column(Numeric(precision=10, scale=4), nullable=False)
    total_debt_to_ebitda = Column(Numeric(precision=10, scale=4), nullable=False)
    net_income_margin = Column(Numeric(precision=10, scale=4), nullable=False)
    ebit_to_interest_expense = Column(Numeric(precision=10, scale=4), nullable=False)
    return_on_assets = Column(Numeric(precision=10, scale=4), nullable=False)
    
    # Reporting information
    reporting_year = Column(String, nullable=True)
    reporting_quarter = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    company = relationship("Company", back_populates="ratios")
    predictions = relationship("DefaultRatePrediction", back_populates="financial_ratio", cascade="all, delete-orphan")

class DefaultRatePrediction(Base):
    __tablename__ = "default_rate_predictions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    financial_ratio_id = Column(UUID(as_uuid=True), ForeignKey("financial_ratios.id"), nullable=False)
    
    risk_level = Column(String, nullable=False)
    confidence = Column(Numeric(precision=5, scale=4), nullable=False)
    probability = Column(Numeric(precision=5, scale=4), nullable=True)
    
    predicted_at = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    company = relationship("Company", back_populates="predictions")
    financial_ratio = relationship("FinancialRatio", back_populates="predictions")

def get_database_url():
    database_url = os.getenv("DATABASE_URL")
    return database_url

engine = create_engine(
    get_database_url(),
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False  
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_database_engine():
    return engine

def get_session_local():
    return SessionLocal

def create_tables():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
