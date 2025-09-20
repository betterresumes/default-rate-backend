# 🗄️ Database Schema

## 📊 Complete Entity Relationship Diagram

```
┌─────────────────┐           ┌─────────────────┐           ┌─────────────────┐
│     TENANTS     │     1:N   │ ORGANIZATIONS   │     1:N   │     USERS       │
│─────────────────│◄─────────►│─────────────────│◄─────────►│─────────────────│
│ • id (UUID)     │           │ • id (UUID)     │           │ • id (UUID)     │
│ • name (unique) │           │ • tenant_id FK  │           │ • email (unique)│
│ • slug (unique) │           │ • name (unique) │           │ • username      │
│ • domain        │           │ • slug (unique) │           │ • password_hash │
│ • description   │           │ • domain        │           │ • full_name     │
│ • logo_url      │           │ • description   │           │ • role          │
│ • is_active     │           │ • logo_url      │           │ • tenant_id FK  │
│ • created_by FK │           │ • is_active     │           │ • org_id FK     │
│ • created_at    │           │ • join_token    │           │ • is_active     │
│ • updated_at    │           │ • join_enabled  │           │ • joined_via    │
└─────────────────┘           │ • default_role  │           │ • whitelist_email│
                              │ • max_users     │           │ • created_at    │
                              │ • global_access │           │ • updated_at    │
                              │ • created_by FK │           │ • last_login    │
                              │ • created_at    │           └─────────────────┘
                              │ • updated_at    │                     │
                              └─────────────────┘                     │ 1:N
                                      │                               │
                                      │ 1:N                           ▼
                                      ▼                     ┌─────────────────┐
                              ┌─────────────────┐           │ ORG_WHITELIST   │
                              │   COMPANIES     │           │─────────────────│
                              │─────────────────│           │ • id (UUID)     │
                              │ • id (UUID)     │           │ • org_id FK     │
                              │ • symbol        │           │ • email         │
                              │ • name          │           │ • added_by FK   │
                              │ • market_cap    │           │ • added_at      │
                              │ • sector        │           │ • status        │
                              │ • org_id FK     │           └─────────────────┘
                              │ • is_global     │
                              │ • created_by FK │
                              │ • created_at    │
                              │ • updated_at    │
                              └─────────────────┘
                                      │
                                      │ 1:N
                                      ▼
                    ┌─────────────────────────────────────────────────────┐
                    │                                                     │
          ┌─────────────────┐                             ┌─────────────────┐
          │ANNUAL_PREDICTIONS│                             │QUARTERLY_PREDICT│
          │─────────────────│                             │─────────────────│
          │ • id (UUID)     │                             │ • id (UUID)     │
          │ • company_id FK │                             │ • company_id FK │
          │ • org_id FK     │                             │ • org_id FK     │
          │ • report_year   │                             │ • report_year   │
          │ • report_quarter│                             │ • report_quarter│
          │ • debt_capital  │                             │ • debt_ebitda   │
          │ • debt_ebitda   │                             │ • sga_margin    │
          │ • income_margin │                             │ • debt_capital  │
          │ • ebit_interest │                             │ • return_capital│
          │ • return_assets │                             │ • logistic_prob │
          │ • probability   │                             │ • gbm_prob      │
          │ • risk_level    │                             │ • ensemble_prob │
          │ • confidence    │                             │ • risk_level    │
          │ • predicted_at  │                             │ • confidence    │
          │ • created_by FK │                             │ • predicted_at  │
          │ • created_at    │                             │ • created_by FK │
          │ • updated_at    │                             │ • created_at    │
          └─────────────────┘                             │ • updated_at    │
                                                          └─────────────────┘

                              ┌─────────────────┐
                              │ BULK_UPLOAD_JOBS│
                              │─────────────────│
                              │ • id (UUID)     │
                              │ • org_id FK     │
                              │ • user_id FK    │
                              │ • job_type      │
                              │ • status        │
                              │ • celery_task_id│
                              │ • filename      │
                              │ • file_size     │
                              │ • total_rows    │
                              │ • processed_rows│
                              │ • success_rows  │
                              │ • failed_rows   │
                              │ • error_message │
                              │ • error_details │
                              │ • started_at    │
                              │ • completed_at  │
                              │ • created_at    │
                              └─────────────────┘
```

## 📋 Table Specifications

### 1. 🏢 Tenants Table

```sql
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,           -- "Banking Corporation"
    slug VARCHAR(100) UNIQUE NOT NULL,           -- "banking-corp"
    domain VARCHAR(255),                         -- "banking-corp.com"
    description TEXT,                            -- "Leading banking group"
    logo_url VARCHAR(500),                       -- Logo image URL
    is_active BOOLEAN DEFAULT TRUE,              -- Tenant status
    
    -- Metadata
    created_by UUID REFERENCES users(id),       -- Super admin who created
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_tenants_name ON tenants(name);
CREATE INDEX idx_tenants_slug ON tenants(slug);
CREATE INDEX idx_tenants_active ON tenants(is_active);
```

**Purpose**: Top-level organizational containers for enterprise customers.

**Real-World Examples**:
- Banking Corporation (HDFC, ICICI, SBI banks)
- FinTech Solutions (Multiple fintech subsidiaries)
- Insurance Group (Life, Health, Auto insurance divisions)

### 2. 🏛️ Organizations Table

```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),      -- Parent tenant
    name VARCHAR(255) UNIQUE NOT NULL,          -- "HDFC Bank Risk Division"
    slug VARCHAR(100) UNIQUE NOT NULL,          -- "hdfc-risk-division"
    domain VARCHAR(255),                        -- "risk.hdfc.com"
    description TEXT,                           -- Division description
    logo_url VARCHAR(500),                      -- Organization logo
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Join Management
    join_token VARCHAR(32) UNIQUE NOT NULL,     -- "abc123xyz" for invitations
    join_enabled BOOLEAN DEFAULT TRUE,          -- Allow new member joins
    default_role VARCHAR(50) DEFAULT 'org_member', -- Role for new joiners
    join_created_at TIMESTAMP DEFAULT NOW(),
    max_users INTEGER DEFAULT 500,             -- Maximum members allowed
    
    -- Data Access Control
    allow_global_data_access BOOLEAN DEFAULT FALSE, -- Can see global companies/predictions
    
    -- Metadata
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Composite unique constraint for company symbols per organization
CREATE UNIQUE INDEX idx_org_symbol_unique ON organizations(tenant_id, slug);
CREATE INDEX idx_org_tenant ON organizations(tenant_id);
CREATE INDEX idx_org_join_token ON organizations(join_token);
```

**Purpose**: Departments or divisions within tenants where actual work happens.

**Real-World Examples**:
- HDFC Bank Risk Assessment Division
- ICICI Credit Analytics Department  
- SBI Loan Processing Unit
- FinTech Consumer Lending Team

### 3. 👥 Users Table

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,         -- "analyst@hdfc.com"
    username VARCHAR(100) UNIQUE NOT NULL,      -- "hdfc_analyst_01"
    hashed_password VARCHAR(255) NOT NULL,      -- bcrypt hash
    full_name VARCHAR(255),                     -- "John Doe"
    
    -- Multi-tenant relationships (mutually exclusive)
    tenant_id UUID REFERENCES tenants(id),     -- For tenant admins only
    organization_id UUID REFERENCES organizations(id), -- For org members/admins
    
    -- 5-Role System
    role VARCHAR(50) DEFAULT 'user' CHECK (
        role IN ('super_admin', 'tenant_admin', 'org_admin', 'org_member', 'user')
    ),
    
    -- Status and tracking
    is_active BOOLEAN DEFAULT TRUE,
    joined_via_token VARCHAR(32),               -- Which join link was used
    whitelist_email VARCHAR(255),               -- Pre-approved email
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

-- Constraints to ensure role-relationship consistency
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_users_org ON users(organization_id);

-- Business rule: tenant_id and organization_id are mutually exclusive
-- (handled in application logic)
```

**Role Distribution Examples**:
```sql
-- Super Admin
role='super_admin', tenant_id=NULL, organization_id=NULL

-- Tenant Admin (manages multiple organizations)
role='tenant_admin', tenant_id='banking-corp-uuid', organization_id=NULL

-- Organization Admin (manages one organization)
role='org_admin', tenant_id=NULL, organization_id='hdfc-risk-uuid'

-- Organization Member (works in one organization)
role='org_member', tenant_id=NULL, organization_id='hdfc-risk-uuid'

-- Regular User (no organization yet)
role='user', tenant_id=NULL, organization_id=NULL
```

### 4. 📧 Organization Whitelist Table

```sql
CREATE TABLE organization_member_whitelist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) NOT NULL,
    email VARCHAR(255) NOT NULL,               -- Pre-approved email
    added_by UUID REFERENCES users(id) NOT NULL, -- Admin who added
    added_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'active'        -- active/inactive
);

-- Ensure unique email per organization
CREATE UNIQUE INDEX idx_org_whitelist_unique ON organization_member_whitelist(organization_id, email);
CREATE INDEX idx_whitelist_org ON organization_member_whitelist(organization_id);
```

**Purpose**: Pre-approved email addresses that can join specific organizations.

### 5. 🏭 Companies Table

```sql
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(20) NOT NULL,               -- "HDFC", "ICICI"
    name VARCHAR(255) NOT NULL,                -- "HDFC Bank Limited"
    market_cap NUMERIC(20,2) NOT NULL,         -- Market capitalization
    sector VARCHAR(100) NOT NULL,              -- "Banking", "Technology"
    
    -- Organization scoping
    organization_id UUID REFERENCES organizations(id), -- Org that owns this company
    is_global BOOLEAN DEFAULT FALSE,           -- Visible to all orgs if true
    
    -- Metadata
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Allow same symbol in different organizations
CREATE UNIQUE INDEX idx_company_symbol_org ON companies(symbol, organization_id);
CREATE INDEX idx_company_org ON companies(organization_id);
CREATE INDEX idx_company_global ON companies(is_global);
CREATE INDEX idx_company_sector ON companies(sector);
```

**Data Isolation Examples**:
```sql
-- HDFC can exist in multiple organizations
('HDFC', 'HDFC Bank', org_id='hdfc-risk', is_global=false)
('HDFC', 'HDFC Bank', org_id='icici-risk', is_global=false)

-- Global companies visible to all (if allowed)
('AAPL', 'Apple Inc', org_id=NULL, is_global=true)
```

### 6. 📊 Annual Predictions Table

```sql
CREATE TABLE annual_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) NOT NULL,
    organization_id UUID REFERENCES organizations(id), -- Data scoping
    
    -- Time period
    reporting_year VARCHAR(10) NOT NULL,       -- "2024"
    reporting_quarter VARCHAR(10),             -- Optional for compatibility
    
    -- Financial metrics (matching existing ML model)
    long_term_debt_to_total_capital NUMERIC(10,4),
    total_debt_to_ebitda NUMERIC(10,4),
    net_income_margin NUMERIC(10,4),
    ebit_to_interest_expense NUMERIC(10,4),
    return_on_assets NUMERIC(10,4),
    
    -- ML prediction results
    probability NUMERIC(5,4) NOT NULL,         -- Default probability (0.0-1.0)
    risk_level VARCHAR(20) NOT NULL,           -- "LOW", "MEDIUM", "HIGH"
    confidence NUMERIC(5,4) NOT NULL,          -- Model confidence (0.0-1.0)
    predicted_at TIMESTAMP,
    
    -- Metadata
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Performance indexes
CREATE INDEX idx_annual_company ON annual_predictions(company_id);
CREATE INDEX idx_annual_org ON annual_predictions(organization_id);
CREATE INDEX idx_annual_year ON annual_predictions(reporting_year);
CREATE INDEX idx_annual_risk ON annual_predictions(risk_level);

-- Unique constraint: one prediction per company per year (per organization)
CREATE UNIQUE INDEX idx_annual_unique ON annual_predictions(company_id, reporting_year, organization_id);
```

### 7. 📈 Quarterly Predictions Table

```sql
CREATE TABLE quarterly_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id) NOT NULL,
    organization_id UUID REFERENCES organizations(id), -- Data scoping
    
    -- Time period
    reporting_year VARCHAR(10) NOT NULL,       -- "2024"
    reporting_quarter VARCHAR(10) NOT NULL,    -- "Q1", "Q2", "Q3", "Q4"
    
    -- Financial metrics (quarterly-specific)
    total_debt_to_ebitda NUMERIC(10,4),
    sga_margin NUMERIC(10,4),                  -- SG&A (Selling, General & Administrative)
    long_term_debt_to_total_capital NUMERIC(10,4),
    return_on_capital NUMERIC(10,4),
    
    -- ML ensemble results
    logistic_probability NUMERIC(5,4),         -- Logistic regression result
    gbm_probability NUMERIC(5,4),              -- Gradient boosting result
    ensemble_probability NUMERIC(5,4),         -- Combined ensemble result
    risk_level VARCHAR(20) NOT NULL,
    confidence NUMERIC(5,4) NOT NULL,
    predicted_at TIMESTAMP,
    
    -- Metadata
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Performance indexes
CREATE INDEX idx_quarterly_company ON quarterly_predictions(company_id);
CREATE INDEX idx_quarterly_org ON quarterly_predictions(organization_id);
CREATE INDEX idx_quarterly_year_quarter ON quarterly_predictions(reporting_year, reporting_quarter);
CREATE INDEX idx_quarterly_risk ON quarterly_predictions(risk_level);

-- Unique constraint: one prediction per company per quarter (per organization)
CREATE UNIQUE INDEX idx_quarterly_unique ON quarterly_predictions(company_id, reporting_year, reporting_quarter, organization_id);
```

### 8. 📄 Bulk Upload Jobs Table

```sql
CREATE TABLE bulk_upload_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id), -- Job scope
    user_id UUID REFERENCES users(id) NOT NULL,        -- Who initiated
    
    -- Job configuration
    job_type VARCHAR(50) NOT NULL CHECK (job_type IN ('annual', 'quarterly')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (
        status IN ('pending', 'queued', 'processing', 'completed', 'failed')
    ),
    celery_task_id VARCHAR(255),               -- For async job tracking
    
    -- File information
    original_filename VARCHAR(255) NOT NULL,   -- "predictions_hdfc_2024.csv"
    file_size INTEGER,                         -- File size in bytes
    total_rows INTEGER,                        -- Total rows to process
    
    -- Progress tracking
    processed_rows INTEGER DEFAULT 0,          -- Rows processed so far
    successful_rows INTEGER DEFAULT 0,         -- Successfully imported
    failed_rows INTEGER DEFAULT 0,             -- Failed imports
    
    -- Error handling
    error_message TEXT,                        -- Error summary
    error_details JSONB,                       -- Detailed error information
    
    -- Timing
    started_at TIMESTAMP,                      -- When processing started
    completed_at TIMESTAMP,                    -- When processing finished
    created_at TIMESTAMP DEFAULT NOW()         -- When job was created
);

-- Indexes for job management
CREATE INDEX idx_bulk_jobs_user ON bulk_upload_jobs(user_id);
CREATE INDEX idx_bulk_jobs_org ON bulk_upload_jobs(organization_id);
CREATE INDEX idx_bulk_jobs_status ON bulk_upload_jobs(status);
CREATE INDEX idx_bulk_jobs_type ON bulk_upload_jobs(job_type);
CREATE INDEX idx_bulk_jobs_celery ON bulk_upload_jobs(celery_task_id);
```

## 🔄 Data Relationships & Constraints

### Relationship Rules

1. **Tenant ↔ Organizations**: One tenant can have multiple organizations (1:N)
2. **Organization ↔ Users**: One organization can have multiple users (1:N)
3. **Tenant ↔ Users**: Tenant admins are directly linked to tenants (1:N)
4. **Company ↔ Organization**: Companies belong to organizations or are global (N:1)
5. **Predictions ↔ Company**: Multiple predictions per company over time (N:1)
6. **Predictions ↔ Organization**: Predictions are scoped to organizations (N:1)

### Data Isolation Constraints

```sql
-- Business Rules Enforced:

-- 1. Users cannot belong to both tenant and organization
-- (Enforced in application logic)

-- 2. Global companies (is_global=true) have organization_id=NULL
-- (Enforced in application logic)

-- 3. Organization predictions must reference companies in same org or global companies
-- (Enforced in application logic and foreign keys)

-- 4. Role consistency: tenant_admin users must have tenant_id, org users must have org_id
-- (Enforced in application logic)
```

## 📊 Data Access Patterns

### Query Examples by Role

```sql
-- Super Admin: All data
SELECT * FROM companies;
SELECT * FROM annual_predictions;

-- Tenant Admin: All data within tenant
SELECT c.* FROM companies c 
JOIN organizations o ON c.organization_id = o.id 
WHERE o.tenant_id = 'user_tenant_id';

-- Org Admin/Member: Organization + global data
SELECT * FROM companies 
WHERE organization_id = 'user_org_id' 
   OR (is_global = true AND EXISTS (
       SELECT 1 FROM organizations 
       WHERE id = 'user_org_id' 
       AND allow_global_data_access = true
   ));

-- User: No company access, profile only
SELECT * FROM users WHERE id = 'user_id';
```

### Performance Optimizations

1. **Composite Indexes**: For multi-column queries (org_id + year + quarter)
2. **Partial Indexes**: For active records only
3. **JSONB Indexes**: For error_details column in bulk jobs
4. **UUID Indexes**: All primary and foreign keys indexed

---

This schema supports enterprise-scale multi-tenant financial risk assessment with proper data isolation and performance optimization.
