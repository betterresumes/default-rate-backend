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

class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)  
    slug = Column(String(100), unique=True, nullable=False, index=True)
    domain = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)
    
    is_active = Column(Boolean, default=True)
    
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    organizations = relationship("Organization", back_populates="tenant")
    tenant_admins = relationship("User", back_populates="tenant", foreign_keys="User.tenant_id")
    creator = relationship("User", foreign_keys=[created_by])

class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True)  
    name = Column(String(255), unique=True, nullable=False, index=True)  
    slug = Column(String(100), unique=True, nullable=False, index=True)
    domain = Column(String(255), nullable=True) 
    description = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)
    
    is_active = Column(Boolean, default=True)
    allow_global_data_access = Column(Boolean, default=False)  # New field for global data access
    
    join_token = Column(String(32), unique=True, nullable=False, index=True)
    join_enabled = Column(Boolean, default=True)
    default_role = Column(String(50), default="org_member")  
    join_created_at = Column(DateTime, default=func.now())
    max_users = Column(Integer, default=500)  
    
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    tenant = relationship("Tenant", back_populates="organizations")
    users = relationship("User", back_populates="organization", foreign_keys="User.organization_id")
    companies = relationship("Company", back_populates="organization")
    whitelist_entries = relationship("OrganizationMemberWhitelist", back_populates="organization", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by])


class OrganizationMemberWhitelist(Base):
    __tablename__ = "organization_member_whitelist"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    email = Column(String(255), nullable=False, index=True)
    
    added_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    added_at = Column(DateTime, default=func.now())
    status = Column(String(20), default="active")  # active/inactive
    
    organization = relationship("Organization", back_populates="whitelist_entries")
    added_by_user = relationship("User", foreign_keys=[added_by])
    
    __table_args__ = (
        Index('idx_org_whitelist_unique', 'organization_id', 'email', unique=True),
    )

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True)  # For tenant admins
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)  # For org members
    
    role = Column(String(50), default="user")  
    
    is_active = Column(Boolean, default=True)
    
    joined_via_token = Column(String(32), nullable=True)  
    whitelist_email = Column(String(255), nullable=True)  
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, nullable=True)
    
    tenant = relationship("Tenant", back_populates="tenant_admins", foreign_keys=[tenant_id])
    organization = relationship("Organization", back_populates="users", foreign_keys=[organization_id])

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    symbol = Column(String(20), index=True, nullable=False)  
    name = Column(String(255), nullable=False)
    market_cap = Column(Numeric(precision=20, scale=2), nullable=False)  # Market cap in raw dollars
    sector = Column(String(100), nullable=False)
    
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)
    access_level = Column(String(20), default="personal", nullable=False, index=True)  # personal, organization, system
    
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('ix_company_symbol_org', 'symbol', 'organization_id', unique=True),
    )
    
    # Relationships
    organization = relationship("Organization", back_populates="companies")
    annual_predictions = relationship("AnnualPrediction", back_populates="company", cascade="all, delete-orphan")
    quarterly_predictions = relationship("QuarterlyPrediction", back_populates="company", cascade="all, delete-orphan")


class AnnualPrediction(Base):
    __tablename__ = "annual_predictions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)
    access_level = Column(String(20), default="personal", nullable=False, index=True)  # personal, organization, system
    
    reporting_year = Column(String(10), nullable=False)
    reporting_quarter = Column(String(10), nullable=True)  
    
    long_term_debt_to_total_capital = Column(Numeric(precision=10, scale=4), nullable=True)
    total_debt_to_ebitda = Column(Numeric(precision=10, scale=4), nullable=True)
    net_income_margin = Column(Numeric(precision=10, scale=4), nullable=True)
    ebit_to_interest_expense = Column(Numeric(precision=10, scale=4), nullable=True)
    return_on_assets = Column(Numeric(precision=10, scale=4), nullable=True)
    
    probability = Column(Numeric(precision=5, scale=4), nullable=False)
    risk_level = Column(String(20), nullable=False)
    confidence = Column(Numeric(precision=5, scale=4), nullable=False)
    predicted_at = Column(DateTime, nullable=True)
    
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    company = relationship("Company", back_populates="annual_predictions")
    
    __table_args__ = (
        Index('idx_annual_company_reporting_year', 'company_id', 'reporting_year'),
        Index('idx_annual_organization', 'organization_id'),
        Index('idx_annual_created_by', 'created_by'),
    )

class QuarterlyPrediction(Base):
    __tablename__ = "quarterly_predictions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)
    access_level = Column(String(20), default="personal", nullable=False, index=True)  
    
    reporting_year = Column(String(10), nullable=False)
    reporting_quarter = Column(String(10), nullable=False)  
    
    total_debt_to_ebitda = Column(Numeric(precision=10, scale=4), nullable=True)
    sga_margin = Column(Numeric(precision=10, scale=4), nullable=True)
    long_term_debt_to_total_capital = Column(Numeric(precision=10, scale=4), nullable=True)
    return_on_capital = Column(Numeric(precision=10, scale=4), nullable=True)
    
    logistic_probability = Column(Numeric(precision=5, scale=4), nullable=True)
    gbm_probability = Column(Numeric(precision=5, scale=4), nullable=True)
    ensemble_probability = Column(Numeric(precision=5, scale=4), nullable=True)
    risk_level = Column(String(20), nullable=False)
    confidence = Column(Numeric(precision=5, scale=4), nullable=False)
    predicted_at = Column(DateTime, nullable=True)
    
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    company = relationship("Company", back_populates="quarterly_predictions")
    
    __table_args__ = (
        Index('idx_quarterly_company_reporting_year_quarter', 'company_id', 'reporting_year', 'reporting_quarter'),
        Index('idx_quarterly_organization', 'organization_id'),
        Index('idx_quarterly_created_by', 'created_by'),
    )

class BulkUploadJob(Base):
    __tablename__ = "bulk_upload_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    job_type = Column(String(50), nullable=False, index=True)  
    status = Column(String(20), default='pending', index=True) 
    
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=True)
    total_rows = Column(Integer, nullable=True)
    
    processed_rows = Column(Integer, default=0)
    successful_rows = Column(Integer, default=0)
    failed_rows = Column(Integer, default=0)
    
    error_message = Column(Text, nullable=True)
    error_details = Column(Text, nullable=True)  
    
    celery_task_id = Column(String(255), nullable=True, index=True)  
    
    created_at = Column(DateTime, default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    user = relationship("User", foreign_keys=[user_id])
    organization = relationship("Organization", foreign_keys=[organization_id])
    
    __table_args__ = (
        Index('idx_bulk_job_status', 'status'),
        Index('idx_bulk_job_user', 'user_id'),
        Index('idx_bulk_job_org', 'organization_id'),
        Index('idx_bulk_job_created', 'created_at'),
    )

def get_database_url():
    """Get database URL with proper fallback and validation"""
    import os
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        # Try loading from .env file if not already loaded
        try:
            from dotenv import load_dotenv
            
            # Load .env from the project root
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
            if os.path.exists(env_path):
                load_dotenv(env_path)
                database_url = os.getenv("DATABASE_URL")
        except ImportError:
            pass
    
    if not database_url:
        raise ValueError(
            "DATABASE_URL environment variable is not set. "
            "Please check your .env file or set the DATABASE_URL environment variable."
        )
    
    # Clean the URL by removing quotes if present
    database_url = database_url.strip().strip('"').strip("'")
    
    # Validate that it looks like a database URL
    if not database_url.startswith(('postgresql://', 'postgres://', 'sqlite:///')):
        raise ValueError(
            f"Invalid DATABASE_URL format: {database_url[:50]}... "
            f"Expected a valid database URL starting with postgresql:// or sqlite:/// "
            f"Got URL starting with: {database_url[:20]}"
        )
    
    return database_url

_engine = None
_SessionLocal = None

def create_database_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            get_database_url(),
            pool_size=20,  
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
