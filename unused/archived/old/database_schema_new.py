#!/usr/bin/env python3

from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Index
from sqlalchemy.types import Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
import os
import uuid

Base = declarative_base()

# ========================================
# ORGANIZATION TABLES (NEW)
# ========================================

class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False)  
    slug = Column(String(100), unique=True, nullable=False, index=True)
    domain = Column(String(255), nullable=True) 
    description = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)
    
    is_active = Column(Boolean, default=True)
    max_users = Column(Integer, default=100)  
    
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    users = relationship("User", back_populates="organization")
    companies = relationship("Company", back_populates="organization")
    invitations = relationship("Invitation", back_populates="organization")
    creator = relationship("User", foreign_keys=[created_by])

class Invitation(Base):
    __tablename__ = "invitations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    
    # Invitation details
    email = Column(String(255), nullable=False, index=True)
    role = Column(String(50), nullable=False, default="user")  
    token = Column(String(255), unique=True, nullable=False, index=True)
    
    # Status
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    
    # Metadata
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    accepted_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    organization = relationship("Organization", back_populates="invitations")
    inviter = relationship("User", foreign_keys=[invited_by])
    accepter = relationship("User", foreign_keys=[accepted_by])

# ========================================
# UPDATED USER TABLE
# ========================================

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    
    # Organization relationship (ONE organization per user for now)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)
    organization_role = Column(String(50), default="user")  # "admin", "user"
    
    # Global roles and status
    global_role = Column(String(50), default="user")  # "super_admin", "user" 
    is_active = Column(Boolean, default=True)  # Simplified: active by default
    is_verified = Column(Boolean, default=False)  # Email verification
    
    # Metadata
    invited_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    invitation_accepted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    inviter = relationship("User", remote_side=[id])
    
    # Remove old relationships that we'll simplify
    # otp_tokens = relationship("OTPToken", back_populates="user", cascade="all, delete-orphan")
    # sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

# ========================================
# SIMPLIFIED AUTH TABLES (FastAPI-Users will handle sessions)
# ========================================

class OTPToken(Base):
    """Simplified OTP for email verification only"""
    __tablename__ = "otp_tokens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token = Column(String(10), nullable=False)  # 6-digit OTP
    token_type = Column(String(50), nullable=False, default="email_verification")
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

# Remove UserSession table - FastAPI-Users will handle this with JWT + Redis

# ========================================
# UPDATED COMPANY TABLE
# ========================================

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    symbol = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    market_cap = Column(Numeric(precision=20, scale=2), nullable=False)
    sector = Column(String(100), nullable=False)
    
    # Organization relationship
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)
    is_global = Column(Boolean, default=False, index=True)  # Global companies visible to all orgs
    
    # Metadata
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    organization = relationship("Organization", back_populates="companies")
    annual_predictions = relationship("AnnualPrediction", back_populates="company", cascade="all, delete-orphan")
    quarterly_predictions = relationship("QuarterlyPrediction", back_populates="company", cascade="all, delete-orphan")

# ========================================
# UPDATED PREDICTION TABLES
# ========================================

class AnnualPrediction(Base):
    __tablename__ = "annual_predictions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    
    # Organization context (nullable allows personal predictions without org)
    # Personal predictions (organization_id = null) are only visible to:
    # 1. The user who created them (created_by = user.id)
    # 2. Super admins (global_role = "super_admin")
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)
    
    # Prediction data (unchanged)
    reporting_year = Column(String(4), nullable=True)
    reporting_quarter = Column(String(2), nullable=True)
    
    long_term_debt_to_total_capital = Column(Numeric(precision=10, scale=4), nullable=True)
    total_debt_to_ebitda = Column(Numeric(precision=10, scale=4), nullable=True)
    net_income_margin = Column(Numeric(precision=10, scale=4), nullable=True)
    ebit_to_interest_expense = Column(Numeric(precision=10, scale=4), nullable=True)
    return_on_assets = Column(Numeric(precision=10, scale=4), nullable=True)
    
    probability = Column(Numeric(precision=5, scale=4), nullable=False)
    risk_level = Column(String(20), nullable=False)
    confidence = Column(Numeric(precision=5, scale=4), nullable=False)
    predicted_at = Column(DateTime, default=func.now())
    
    # Metadata
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="annual_predictions")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_annual_company_year_quarter', 'company_id', 'reporting_year', 'reporting_quarter', unique=True),
        Index('idx_annual_organization', 'organization_id'),
    )

class QuarterlyPrediction(Base):
    __tablename__ = "quarterly_predictions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    
    # Organization context (nullable allows personal predictions without org)
    # Personal predictions (organization_id = null) are only visible to:
    # 1. The user who created them (created_by = user.id)
    # 2. Super admins (global_role = "super_admin")
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)
    
    # Prediction data (unchanged)
    reporting_year = Column(String(4), nullable=False)
    reporting_quarter = Column(String(2), nullable=False)
    
    total_debt_to_ebitda = Column(Numeric(precision=10, scale=4), nullable=False)
    sga_margin = Column(Numeric(precision=10, scale=4), nullable=False)
    long_term_debt_to_total_capital = Column(Numeric(precision=10, scale=4), nullable=False)
    return_on_capital = Column(Numeric(precision=10, scale=4), nullable=False)
    
    logistic_probability = Column(Numeric(precision=5, scale=4), nullable=False)
    gbm_probability = Column(Numeric(precision=5, scale=4), nullable=False)
    ensemble_probability = Column(Numeric(precision=5, scale=4), nullable=False)
    risk_level = Column(String(20), nullable=False)
    confidence = Column(Numeric(precision=5, scale=4), nullable=False)
    predicted_at = Column(DateTime, default=func.now())
    
    # Metadata
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="quarterly_predictions")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_quarterly_company_year_quarter', 'company_id', 'reporting_year', 'reporting_quarter', unique=True),
        Index('idx_quarterly_organization', 'organization_id'),
    )

# ========================================
# DATABASE CONFIGURATION
# ========================================

def get_database_url():
    database_url = os.getenv("DATABASE_URL")
    return database_url

engine = create_engine(
    get_database_url(),
    pool_size=20,  # Increased for better performance
    max_overflow=30,
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
