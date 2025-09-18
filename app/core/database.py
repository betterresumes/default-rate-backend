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
# TENANT TABLES (ENTERPRISE)
# ========================================

class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)  # Unique tenant names
    slug = Column(String(100), unique=True, nullable=False, index=True)
    domain = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)
    
    is_active = Column(Boolean, default=True)
    
    # Metadata
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    organizations = relationship("Organization", back_populates="tenant")
    tenant_admins = relationship("User", back_populates="tenant", foreign_keys="User.tenant_id")
    creator = relationship("User", foreign_keys=[created_by])

# ========================================
# ORGANIZATION TABLES (UPDATED)
# ========================================

class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True)  # Nullable for direct orgs
    name = Column(String(255), unique=True, nullable=False, index=True)  # Unique org names globally
    slug = Column(String(100), unique=True, nullable=False, index=True)
    domain = Column(String(255), nullable=True) 
    description = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)
    
    is_active = Column(Boolean, default=True)
    
    # Whitelist-based Join System
    join_token = Column(String(32), unique=True, nullable=False, index=True)
    join_enabled = Column(Boolean, default=True)
    default_role = Column(String(50), default="member")  # Role assigned to new joiners
    join_created_at = Column(DateTime, default=func.now())
    max_users = Column(Integer, default=500)  # Maximum number of users allowed in organization
    
    # Metadata
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="organizations")
    users = relationship("User", back_populates="organization", foreign_keys="User.organization_id")
    companies = relationship("Company", back_populates="organization")
    whitelist_entries = relationship("OrganizationMemberWhitelist", back_populates="organization", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by])

# ========================================
# ORGANIZATION MEMBER WHITELIST (NEW)
# ========================================

class OrganizationMemberWhitelist(Base):
    __tablename__ = "organization_member_whitelist"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    
    # Metadata
    added_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    added_at = Column(DateTime, default=func.now())
    status = Column(String(20), default="active")  # active/inactive
    
    # Relationships
    organization = relationship("Organization", back_populates="whitelist_entries")
    added_by_user = relationship("User", foreign_keys=[added_by])
    
    # Ensure unique email per organization
    __table_args__ = (
        Index('idx_org_whitelist_unique', 'organization_id', 'email', unique=True),
    )

# ========================================
# UPDATED USER TABLE (5-ROLE SYSTEM)
# ========================================

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    
    # Multi-tenant relationships
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True)  # For tenant admins
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)  # For org members
    
    # Role system (5 roles)
    global_role = Column(String(50), default="user")  # "super_admin", "tenant_admin", "user"
    organization_role = Column(String(50), nullable=True)  # "admin", "member" (only if in organization)
    
    # Status and metadata
    is_active = Column(Boolean, default=True)
    
    # Join tracking
    joined_via_token = Column(String(32), nullable=True)  # Track which join link was used
    whitelist_email = Column(String(255), nullable=True)  # Email that was whitelisted
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="tenant_admins", foreign_keys=[tenant_id])
    organization = relationship("Organization", back_populates="users", foreign_keys=[organization_id])

# ========================================
# REMOVED: EMAIL VERIFICATION TABLES
# ========================================
# No OTP tokens needed - email verification removed completely

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
# UPDATED PREDICTION TABLES (MULTI-TENANT)
# ========================================

class AnnualPrediction(Base):
    __tablename__ = "annual_predictions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    
    # Multi-tenant context
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)
    # NULL organization_id = accessible to all users (super admin data)
    # Non-NULL organization_id = only accessible to org members
    
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
        Index('idx_annual_created_by', 'created_by'),
    )

class QuarterlyPrediction(Base):
    __tablename__ = "quarterly_predictions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    
    # Multi-tenant context
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)
    # NULL organization_id = accessible to all users (super admin data)
    # Non-NULL organization_id = only accessible to org members
    
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
        Index('idx_quarterly_created_by', 'created_by'),
    )

# ========================================
# DATABASE CONFIGURATION
# ========================================

def get_database_url():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    return database_url

# Lazy engine creation
_engine = None
_SessionLocal = None

def create_database_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            get_database_url(),
            pool_size=20,  # Increased for better performance
            max_overflow=30,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=False
        )
    return _engine

def get_session_local():
    global _SessionLocal
    if _SessionLocal is None:
        engine = create_database_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal

def create_tables():
    engine = create_database_engine()
    Base.metadata.create_all(bind=engine)

def get_db():
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
