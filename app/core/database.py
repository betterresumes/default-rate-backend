#!/usr/bin/env python3

from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Index
from sqlalchemy.types import Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
import uuid
import os
from datetime import datetime
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
    tenant_admins = relationship("User", back_populates="assigned_tenant", foreign_keys="User.tenant_id")
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
    default_role = Column(String(50), default="org_member")  # New role system - default to org_member
    join_created_at = Column(DateTime, default=func.now())
    max_users = Column(Integer, default=500)  # Maximum number of users allowed in organization
    
    # Global Data Access Control
    allow_global_data_access = Column(Boolean, default=False)  # Controls if org users can see global predictions/companies
    
    # Metadata
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    tenant = relationship("Tenant", back_populates="organizations")
    users = relationship("User", back_populates="assigned_organization", foreign_keys="User.organization_id")
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
    
    # New 5-Role System (Single role field)
    # super_admin: Can manage everything
    # tenant_admin: Attached to 1 tenant, can manage multiple orgs within that tenant
    # org_admin: Attached to 1 organization, can manage users in that org
    # org_member: Attached to 1 organization, can access org resources
    # user: No organization attachment, limited access
    role = Column(String(50), default="user")  # Single role field
    
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
    assigned_tenant = relationship("Tenant", back_populates="tenant_admins", foreign_keys=[tenant_id])
    assigned_organization = relationship("Organization", back_populates="users", foreign_keys=[organization_id])

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
    symbol = Column(String(20), index=True, nullable=False)  # Removed unique=True
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
    
    # Composite unique constraint: same symbol allowed in different organizations
    __table_args__ = (
        Index('ix_company_symbol_org', 'symbol', 'organization_id', unique=True),
        # This allows: HDFC in org A, HDFC in org B, but not duplicate HDFC in same org
    )
    
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
    is_global = Column(Boolean, default=False, index=True)  # Global data created by super admin
    
    # Time period - matching existing schema
    reporting_year = Column(String(10), nullable=False)
    reporting_quarter = Column(String(10), nullable=True)  # For compatibility
    
    # Financial prediction fields - matching existing schema
    long_term_debt_to_total_capital = Column(Numeric(precision=10, scale=4), nullable=True)
    total_debt_to_ebitda = Column(Numeric(precision=10, scale=4), nullable=True)
    net_income_margin = Column(Numeric(precision=10, scale=4), nullable=True)
    ebit_to_interest_expense = Column(Numeric(precision=10, scale=4), nullable=True)
    return_on_assets = Column(Numeric(precision=10, scale=4), nullable=True)
    
    # ML prediction results
    probability = Column(Numeric(precision=5, scale=4), nullable=False)
    risk_level = Column(String(20), nullable=False)
    confidence = Column(Numeric(precision=5, scale=4), nullable=False)
    predicted_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="annual_predictions")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_annual_company_reporting_year', 'company_id', 'reporting_year'),
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
    is_global = Column(Boolean, default=False, index=True)  # Global data created by super admin
    
    # Time period - matching existing schema
    reporting_year = Column(String(10), nullable=False)
    reporting_quarter = Column(String(10), nullable=False)  # Q1, Q2, Q3, Q4
    
    # Financial prediction fields - matching existing schema
    total_debt_to_ebitda = Column(Numeric(precision=10, scale=4), nullable=True)
    sga_margin = Column(Numeric(precision=10, scale=4), nullable=True)
    long_term_debt_to_total_capital = Column(Numeric(precision=10, scale=4), nullable=True)
    return_on_capital = Column(Numeric(precision=10, scale=4), nullable=True)
    
    # ML prediction results - matching existing schema
    logistic_probability = Column(Numeric(precision=5, scale=4), nullable=True)
    gbm_probability = Column(Numeric(precision=5, scale=4), nullable=True)
    ensemble_probability = Column(Numeric(precision=5, scale=4), nullable=True)
    risk_level = Column(String(20), nullable=False)
    confidence = Column(Numeric(precision=5, scale=4), nullable=False)
    predicted_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="quarterly_predictions")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_quarterly_company_reporting_year_quarter', 'company_id', 'reporting_year', 'reporting_quarter'),
        Index('idx_quarterly_organization', 'organization_id'),
        Index('idx_quarterly_created_by', 'created_by'),
    )

# ========================================
# BULK UPLOAD JOB TABLES
# ========================================

class BulkUploadJob(Base):
    __tablename__ = "bulk_upload_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Job details
    job_type = Column(String(50), nullable=False, index=True)  # 'annual' or 'quarterly'
    status = Column(String(20), default='pending', index=True)  # pending, queued, processing, completed, failed
    celery_task_id = Column(String(255), nullable=True, index=True)  # Celery task ID for tracking
    
    # File information
    original_filename = Column(String(255), nullable=False)
    file_size = Column(Integer, nullable=True)
    total_rows = Column(Integer, nullable=True)
    
    # Progress tracking
    processed_rows = Column(Integer, default=0)
    successful_rows = Column(Integer, default=0)
    failed_rows = Column(Integer, default=0)
    
    # Results
    error_message = Column(Text, nullable=True)
    error_details = Column(Text, nullable=True)  # JSON string with detailed errors
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    organization = relationship("Organization", foreign_keys=[organization_id])
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_bulk_job_status', 'status'),
        Index('idx_bulk_job_user', 'user_id'),
        Index('idx_bulk_job_org', 'organization_id'),
        Index('idx_bulk_job_created', 'created_at'),
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
