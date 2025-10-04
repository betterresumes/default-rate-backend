# 🗄️ Database Design & Architecture

## 📋 **Table of Contents**
1. [Database Schema Overview](#database-schema-overview)
2. [Entity Relationship Diagram](#entity-relationship-diagram)
3. [Table Specifications](#table-specifications)
4. [Relationships & Constraints](#relationships--constraints)
5. [Indexing Strategy](#indexing-strategy)
6. [Data Access Patterns](#data-access-patterns)
7. [Performance Optimization](#performance-optimization)

---

## 🎯 **Database Schema Overview**

AccuNode uses **PostgreSQL 15+** as the primary database with a carefully designed schema supporting multi-tenancy, role-based access control, and ML prediction storage.

### **Schema Architecture**
```
┌─────────────────────────────────────────────────────────────────┐
│                    DATABASE ARCHITECTURE                        │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                 CORE ENTITIES                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │    Users    │  │Organizations│  │  Companies  │            │
│  │(Multi-Role) │  │(Multi-Tenant)│  │ (Entities) │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│              PREDICTION ENTITIES                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Annual    │  │ Quarterly   │  │    Bulk     │            │
│  │Predictions  │  │Predictions  │  │    Jobs     │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│               AUDIT & LOGGING                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ Audit Logs  │  │  Sessions   │  │System Logs  │            │
│  │ (Security)  │  │  (Redis)    │  │(CloudWatch) │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

### **Database Configuration**
```yaml
Database_Engine: PostgreSQL 15.3
Connection_Pool_Size: 20
Max_Connections: 100
Shared_Buffers: 256MB
Work_Mem: 4MB
Maintenance_Work_Mem: 64MB
Effective_Cache_Size: 1GB
```

---

## 🔗 **Entity Relationship Diagram**

### **Complete ERD**
```
                    ┌─────────────────┐
                    │  organizations  │
                    ├─────────────────┤
                    │ id (PK)         │
                    │ name            │
                    │ domain          │
                    │ created_at      │
                    │ updated_at      │
                    └─────────┬───────┘
                              │
                              │ 1:N
                              ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│      users      │    │    companies    │    │  bulk_upload_   │
├─────────────────┤    ├─────────────────┤    │      jobs       │
│ id (PK)         │◄──►│ id (PK)         │    ├─────────────────┤
│ email           │    │ symbol          │    │ id (PK)         │
│ password_hash   │    │ name            │    │ filename        │
│ role            │    │ sector          │    │ status          │
│ organization_id │    │ market_cap      │    │ total_rows      │
│ is_verified     │    │ organization_id │    │ processed_rows  │
│ created_at      │    │ access_level    │    │ success_count   │
│ updated_at      │    │ created_by      │    │ error_count     │
│ last_login      │    │ created_at      │    │ created_by      │
└─────────┬───────┘    │ updated_at      │    │ created_at      │
          │            └─────────┬───────┘    │ updated_at      │
          │                      │            └─────────────────┘
          │ 1:N                  │ 1:N
          ▼                      ▼
┌─────────────────┐    ┌─────────────────┐
│annual_predictions│    │quarterly_predic.│
├─────────────────┤    ├─────────────────┤
│ id (PK)         │    │ id (PK)         │
│ company_id (FK) │    │ company_id (FK) │
│ reporting_year  │    │ reporting_year  │
│ probability     │    │ reporting_qtr   │
│ risk_level      │    │ logistic_prob   │
│ confidence      │    │ gbm_probability │
│ access_level    │    │ ensemble_prob   │
│ organization_id │    │ risk_level      │
│ created_by (FK) │    │ confidence      │
│ predicted_at    │    │ access_level    │
│ created_at      │    │ organization_id │
│ updated_at      │    │ created_by (FK) │
│                 │    │ predicted_at    │
│ + 5 fin ratios  │    │ created_at      │
└─────────────────┘    │ updated_at      │
                       │                 │
                       │ + 6 fin ratios  │
                       └─────────────────┘
```

---

## 📊 **Table Specifications**

### **1. Users Table**
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('user', 'org_member', 'org_admin', 'tenant_admin', 'super_admin')),
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(20),
    is_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_organization_id ON users(organization_id);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_is_verified ON users(is_verified);
CREATE INDEX idx_users_created_at ON users(created_at);
```

### **2. Organizations Table**
```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    domain VARCHAR(100),
    description TEXT,
    industry VARCHAR(100),
    size_category VARCHAR(50) CHECK (size_category IN ('startup', 'small', 'medium', 'large', 'enterprise')),
    is_active BOOLEAN DEFAULT TRUE,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_organizations_name ON organizations(name);
CREATE INDEX idx_organizations_domain ON organizations(domain);
CREATE INDEX idx_organizations_is_active ON organizations(is_active);
CREATE INDEX idx_organizations_industry ON organizations(industry);
```

### **3. Companies Table**
```sql
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(10) NOT NULL,
    name VARCHAR(200) NOT NULL,
    sector VARCHAR(100) NOT NULL,
    industry VARCHAR(100),
    market_cap BIGINT CHECK (market_cap > 0),
    country VARCHAR(3) DEFAULT 'USA',
    currency VARCHAR(3) DEFAULT 'USD',
    exchange VARCHAR(10),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    access_level VARCHAR(20) NOT NULL CHECK (access_level IN ('personal', 'organization', 'system')),
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint per organization
    CONSTRAINT unique_company_symbol_per_org UNIQUE(symbol, organization_id)
);

-- Indexes
CREATE INDEX idx_companies_symbol ON companies(symbol);
CREATE INDEX idx_companies_name ON companies(name);
CREATE INDEX idx_companies_sector ON companies(sector);
CREATE INDEX idx_companies_organization_id ON companies(organization_id);
CREATE INDEX idx_companies_access_level ON companies(access_level);
CREATE INDEX idx_companies_created_by ON companies(created_by);
CREATE INDEX idx_companies_market_cap ON companies(market_cap);
```

### **4. Annual Predictions Table**
```sql
CREATE TABLE annual_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    reporting_year VARCHAR(4) NOT NULL CHECK (reporting_year ~ '^\d{4}$'),
    
    -- ML Prediction Results
    probability DECIMAL(5,4) NOT NULL CHECK (probability >= 0 AND probability <= 1),
    risk_level VARCHAR(10) NOT NULL CHECK (risk_level IN ('Low', 'Medium', 'High')),
    confidence DECIMAL(5,4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    predicted_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Financial Ratios (5 ratios for annual predictions)
    long_term_debt_to_total_capital DECIMAL(8,4) CHECK (long_term_debt_to_total_capital >= 0 AND long_term_debt_to_total_capital <= 2),
    total_debt_to_ebitda DECIMAL(8,4) CHECK (total_debt_to_ebitda >= 0 AND total_debt_to_ebitda <= 50),
    net_income_margin DECIMAL(8,4) CHECK (net_income_margin >= -1 AND net_income_margin <= 1),
    ebit_to_interest_expense DECIMAL(8,4) CHECK (ebit_to_interest_expense >= 0 AND ebit_to_interest_expense <= 100),
    return_on_assets DECIMAL(8,4) CHECK (return_on_assets >= -1 AND return_on_assets <= 1),
    
    -- Access Control
    access_level VARCHAR(20) NOT NULL CHECK (access_level IN ('personal', 'organization', 'system')),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    created_by UUID NOT NULL REFERENCES users(id),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint to prevent duplicate predictions
    CONSTRAINT unique_annual_prediction UNIQUE(company_id, reporting_year, organization_id)
);

-- Indexes for Performance
CREATE INDEX idx_annual_predictions_company_id ON annual_predictions(company_id);
CREATE INDEX idx_annual_predictions_reporting_year ON annual_predictions(reporting_year);
CREATE INDEX idx_annual_predictions_risk_level ON annual_predictions(risk_level);
CREATE INDEX idx_annual_predictions_organization_id ON annual_predictions(organization_id);
CREATE INDEX idx_annual_predictions_created_by ON annual_predictions(created_by);
CREATE INDEX idx_annual_predictions_access_level ON annual_predictions(access_level);
CREATE INDEX idx_annual_predictions_probability ON annual_predictions(probability);
CREATE INDEX idx_annual_predictions_created_at ON annual_predictions(created_at);
CREATE INDEX idx_annual_predictions_predicted_at ON annual_predictions(predicted_at);

-- Composite indexes for common queries
CREATE INDEX idx_annual_predictions_company_year ON annual_predictions(company_id, reporting_year);
CREATE INDEX idx_annual_predictions_org_year ON annual_predictions(organization_id, reporting_year);
CREATE INDEX idx_annual_predictions_user_created ON annual_predictions(created_by, created_at);
```

### **5. Quarterly Predictions Table**
```sql
CREATE TABLE quarterly_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    reporting_year VARCHAR(4) NOT NULL CHECK (reporting_year ~ '^\d{4}$'),
    reporting_quarter VARCHAR(2) NOT NULL CHECK (reporting_quarter IN ('Q1', 'Q2', 'Q3', 'Q4')),
    
    -- ML Prediction Results (Enhanced for Quarterly)
    logistic_probability DECIMAL(5,4) NOT NULL CHECK (logistic_probability >= 0 AND logistic_probability <= 1),
    gbm_probability DECIMAL(5,4) NOT NULL CHECK (gbm_probability >= 0 AND gbm_probability <= 1),
    ensemble_probability DECIMAL(5,4) NOT NULL CHECK (ensemble_probability >= 0 AND ensemble_probability <= 1),
    risk_level VARCHAR(10) NOT NULL CHECK (risk_level IN ('Low', 'Medium', 'High')),
    confidence DECIMAL(5,4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    predicted_at TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Financial Ratios (6 ratios for quarterly predictions)
    current_ratio DECIMAL(8,4) CHECK (current_ratio >= 0 AND current_ratio <= 10),
    quick_ratio DECIMAL(8,4) CHECK (quick_ratio >= 0 AND quick_ratio <= 10),
    debt_to_equity DECIMAL(8,4) CHECK (debt_to_equity >= 0 AND debt_to_equity <= 5),
    inventory_turnover DECIMAL(8,4) CHECK (inventory_turnover >= 0 AND inventory_turnover <= 50),
    receivables_turnover DECIMAL(8,4) CHECK (receivables_turnover >= 0 AND receivables_turnover <= 50),
    working_capital_to_total_assets DECIMAL(8,4) CHECK (working_capital_to_total_assets >= -1 AND working_capital_to_total_assets <= 1),
    
    -- Access Control
    access_level VARCHAR(20) NOT NULL CHECK (access_level IN ('personal', 'organization', 'system')),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    created_by UUID NOT NULL REFERENCES users(id),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint to prevent duplicate predictions
    CONSTRAINT unique_quarterly_prediction UNIQUE(company_id, reporting_year, reporting_quarter, organization_id)
);

-- Indexes for Performance
CREATE INDEX idx_quarterly_predictions_company_id ON quarterly_predictions(company_id);
CREATE INDEX idx_quarterly_predictions_reporting_year ON quarterly_predictions(reporting_year);
CREATE INDEX idx_quarterly_predictions_reporting_quarter ON quarterly_predictions(reporting_quarter);
CREATE INDEX idx_quarterly_predictions_risk_level ON quarterly_predictions(risk_level);
CREATE INDEX idx_quarterly_predictions_organization_id ON quarterly_predictions(organization_id);
CREATE INDEX idx_quarterly_predictions_created_by ON quarterly_predictions(created_by);
CREATE INDEX idx_quarterly_predictions_access_level ON quarterly_predictions(access_level);
CREATE INDEX idx_quarterly_predictions_ensemble_probability ON quarterly_predictions(ensemble_probability);
CREATE INDEX idx_quarterly_predictions_created_at ON quarterly_predictions(created_at);

-- Composite indexes for common queries
CREATE INDEX idx_quarterly_predictions_company_year_qtr ON quarterly_predictions(company_id, reporting_year, reporting_quarter);
CREATE INDEX idx_quarterly_predictions_org_year_qtr ON quarterly_predictions(organization_id, reporting_year, reporting_quarter);
```

### **6. Bulk Upload Jobs Table**
```sql
CREATE TABLE bulk_upload_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_size BIGINT NOT NULL,
    file_hash VARCHAR(64), -- SHA-256 hash for deduplication
    
    -- Job Status and Progress
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
    job_type VARCHAR(20) NOT NULL CHECK (job_type IN ('annual', 'quarterly')),
    total_rows INTEGER DEFAULT 0,
    processed_rows INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    
    -- Processing Details
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    processing_logs JSONB DEFAULT '[]',
    
    -- Access Control
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    created_by UUID NOT NULL REFERENCES users(id),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_bulk_jobs_status ON bulk_upload_jobs(status);
CREATE INDEX idx_bulk_jobs_created_by ON bulk_upload_jobs(created_by);
CREATE INDEX idx_bulk_jobs_organization_id ON bulk_upload_jobs(organization_id);
CREATE INDEX idx_bulk_jobs_job_type ON bulk_upload_jobs(job_type);
CREATE INDEX idx_bulk_jobs_created_at ON bulk_upload_jobs(created_at);
CREATE INDEX idx_bulk_jobs_file_hash ON bulk_upload_jobs(file_hash);
```

### **7. Audit Logs Table**
```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID,
    user_id UUID REFERENCES users(id),
    organization_id UUID REFERENCES organizations(id),
    
    -- Event Details
    action VARCHAR(20) NOT NULL CHECK (action IN ('CREATE', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT', 'FAILED_LOGIN')),
    old_values JSONB,
    new_values JSONB,
    metadata JSONB DEFAULT '{}',
    
    -- Request Context
    ip_address INET,
    user_agent TEXT,
    request_id VARCHAR(100),
    
    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for Audit Queries
CREATE INDEX idx_audit_logs_event_type ON audit_logs(event_type);
CREATE INDEX idx_audit_logs_entity_type ON audit_logs(entity_type);
CREATE INDEX idx_audit_logs_entity_id ON audit_logs(entity_id);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_organization_id ON audit_logs(organization_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX idx_audit_logs_ip_address ON audit_logs(ip_address);

-- Composite index for common audit queries
CREATE INDEX idx_audit_logs_user_action_date ON audit_logs(user_id, action, created_at);
```

---

## 🔗 **Relationships & Constraints**

### **Foreign Key Relationships**
```sql
-- User to Organization (Many-to-One)
ALTER TABLE users ADD CONSTRAINT fk_users_organization 
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE SET NULL;

-- Company to Organization (Many-to-One)
ALTER TABLE companies ADD CONSTRAINT fk_companies_organization 
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE;

-- Company to User (Many-to-One - Created By)
ALTER TABLE companies ADD CONSTRAINT fk_companies_created_by 
    FOREIGN KEY (created_by) REFERENCES users(id);

-- Annual Predictions Relationships
ALTER TABLE annual_predictions ADD CONSTRAINT fk_annual_predictions_company 
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE;
ALTER TABLE annual_predictions ADD CONSTRAINT fk_annual_predictions_organization 
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE;
ALTER TABLE annual_predictions ADD CONSTRAINT fk_annual_predictions_created_by 
    FOREIGN KEY (created_by) REFERENCES users(id);

-- Quarterly Predictions Relationships
ALTER TABLE quarterly_predictions ADD CONSTRAINT fk_quarterly_predictions_company 
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE;
ALTER TABLE quarterly_predictions ADD CONSTRAINT fk_quarterly_predictions_organization 
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE;
ALTER TABLE quarterly_predictions ADD CONSTRAINT fk_quarterly_predictions_created_by 
    FOREIGN KEY (created_by) REFERENCES users(id);

-- Bulk Jobs Relationships
ALTER TABLE bulk_upload_jobs ADD CONSTRAINT fk_bulk_jobs_organization 
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE;
ALTER TABLE bulk_upload_jobs ADD CONSTRAINT fk_bulk_jobs_created_by 
    FOREIGN KEY (created_by) REFERENCES users(id);
```

### **Business Logic Constraints**
```sql
-- Ensure organization consistency for predictions
CREATE OR REPLACE FUNCTION check_prediction_organization_consistency()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if company belongs to the same organization as prediction
    IF NEW.organization_id IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM companies 
            WHERE id = NEW.company_id 
            AND (organization_id = NEW.organization_id OR organization_id IS NULL)
        ) THEN
            RAISE EXCEPTION 'Company must belong to the same organization as the prediction';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to both prediction tables
CREATE TRIGGER trigger_annual_prediction_org_check
    BEFORE INSERT OR UPDATE ON annual_predictions
    FOR EACH ROW EXECUTE FUNCTION check_prediction_organization_consistency();

CREATE TRIGGER trigger_quarterly_prediction_org_check
    BEFORE INSERT OR UPDATE ON quarterly_predictions
    FOR EACH ROW EXECUTE FUNCTION check_prediction_organization_consistency();
```

---

## 📈 **Indexing Strategy**

### **Primary Indexes (Performance)**
```sql
-- Users table indexes
CREATE INDEX CONCURRENTLY idx_users_email_verified ON users(email) WHERE is_verified = true;
CREATE INDEX CONCURRENTLY idx_users_active_role ON users(role) WHERE is_active = true;

-- Companies performance indexes
CREATE INDEX CONCURRENTLY idx_companies_sector_market_cap ON companies(sector, market_cap DESC);
CREATE INDEX CONCURRENTLY idx_companies_name_trgm ON companies USING gin(name gin_trgm_ops);

-- Predictions performance indexes
CREATE INDEX CONCURRENTLY idx_annual_pred_performance ON annual_predictions(organization_id, created_at DESC, risk_level);
CREATE INDEX CONCURRENTLY idx_quarterly_pred_performance ON quarterly_predictions(organization_id, reporting_year DESC, reporting_quarter);

-- Audit logs partitioned index
CREATE INDEX CONCURRENTLY idx_audit_logs_date_partition ON audit_logs(created_at, event_type) 
WHERE created_at >= CURRENT_DATE - INTERVAL '90 days';
```

### **Search and Filter Indexes**
```sql
-- Enable full-text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Company search indexes
CREATE INDEX CONCURRENTLY idx_companies_name_search ON companies USING gin(to_tsvector('english', name));
CREATE INDEX CONCURRENTLY idx_companies_symbol_search ON companies USING gin(to_tsvector('english', symbol));

-- Prediction filtering indexes
CREATE INDEX CONCURRENTLY idx_predictions_date_range ON annual_predictions(predicted_at, risk_level);
CREATE INDEX CONCURRENTLY idx_predictions_probability_range ON annual_predictions(probability) 
WHERE probability BETWEEN 0.3 AND 0.7;
```

---

## 🔍 **Data Access Patterns**

### **Common Query Patterns**

#### **1. User Access Control Queries**
```sql
-- Get user's accessible predictions (with organization filtering)
SELECT p.*, c.symbol, c.name as company_name
FROM annual_predictions p
JOIN companies c ON p.company_id = c.id
WHERE (
    p.created_by = $user_id OR 
    (p.organization_id = $user_org_id AND p.access_level = 'organization') OR
    p.access_level = 'system'
)
ORDER BY p.created_at DESC
LIMIT 20 OFFSET $offset;

-- Performance: Uses idx_annual_predictions_org_year and idx_annual_predictions_user_created
```

#### **2. Dashboard Analytics Queries**
```sql
-- Risk distribution by sector (for organization dashboard)
SELECT c.sector, p.risk_level, COUNT(*) as count
FROM annual_predictions p
JOIN companies c ON p.company_id = c.id
WHERE p.organization_id = $org_id 
AND p.reporting_year = $year
GROUP BY c.sector, p.risk_level
ORDER BY c.sector, p.risk_level;

-- Performance: Uses idx_annual_predictions_org_year and idx_companies_sector
```

#### **3. ML Model Performance Queries**
```sql
-- Compare quarterly model accuracies
SELECT 
    reporting_year,
    reporting_quarter,
    AVG(ABS(logistic_probability - ensemble_probability)) as logistic_deviation,
    AVG(ABS(gbm_probability - ensemble_probability)) as gbm_deviation,
    AVG(confidence) as avg_confidence
FROM quarterly_predictions
WHERE organization_id = $org_id
GROUP BY reporting_year, reporting_quarter
ORDER BY reporting_year DESC, reporting_quarter DESC;
```

### **Optimized Query Examples**

#### **Pagination with Cursor-based Approach**
```sql
-- Efficient pagination for large datasets
SELECT p.*, c.symbol, c.name
FROM annual_predictions p
JOIN companies c ON p.company_id = c.id
WHERE p.organization_id = $org_id
AND p.created_at < $cursor_timestamp
ORDER BY p.created_at DESC
LIMIT 20;

-- Uses idx_annual_predictions_org_year for optimal performance
```

#### **Bulk Data Validation Query**
```sql
-- Check for duplicate predictions before bulk insert
SELECT company_id, reporting_year, COUNT(*)
FROM (VALUES 
    ($company_id_1, $year_1),
    ($company_id_2, $year_2)
    -- ... more values
) AS new_predictions(company_id, reporting_year)
WHERE EXISTS (
    SELECT 1 FROM annual_predictions ap
    WHERE ap.company_id = new_predictions.company_id
    AND ap.reporting_year = new_predictions.reporting_year
    AND ap.organization_id = $org_id
)
GROUP BY company_id, reporting_year;
```

---

## ⚡ **Performance Optimization**

### **Query Optimization Techniques**

#### **1. Connection Pooling Configuration**
```python
# SQLAlchemy connection pool settings
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,          # Base number of connections
    max_overflow=30,       # Additional connections during spikes
    pool_timeout=30,       # Wait time for connection
    pool_recycle=3600,     # Recycle connections every hour
    pool_pre_ping=True,    # Validate connections
    echo=False             # Disable SQL logging in production
)
```

#### **2. Query Caching Strategy**
```python
# Redis-based query result caching
@cache_result(ttl=1800)  # 30 minutes cache
async def get_user_predictions_summary(user_id: str, org_id: str):
    """Cache expensive aggregation queries"""
    query = """
    SELECT 
        COUNT(*) as total_predictions,
        COUNT(CASE WHEN risk_level = 'High' THEN 1 END) as high_risk_count,
        AVG(probability) as avg_probability,
        MAX(created_at) as last_prediction
    FROM annual_predictions 
    WHERE created_by = $1 OR organization_id = $2
    """
    return await db.fetch_one(query, user_id, org_id)
```

#### **3. Batch Processing Optimization**
```python
# Optimized bulk insert with COPY command
async def bulk_insert_predictions(predictions: List[dict]):
    """Use PostgreSQL COPY for efficient bulk inserts"""
    
    # Prepare data in CSV format
    csv_data = io.StringIO()
    writer = csv.writer(csv_data)
    
    for pred in predictions:
        writer.writerow([
            pred['id'], pred['company_id'], pred['reporting_year'],
            pred['probability'], pred['risk_level'], pred['confidence'],
            # ... other fields
        ])
    
    csv_data.seek(0)
    
    # Use COPY command for fast bulk insert
    async with get_db_connection() as conn:
        await conn.copy_from_table(
            'annual_predictions',
            source=csv_data,
            format='csv',
            columns=['id', 'company_id', 'reporting_year', ...]
        )
```

### **Database Maintenance Procedures**

#### **1. Regular Maintenance Tasks**
```sql
-- Weekly maintenance script
DO $$
BEGIN
    -- Update table statistics
    ANALYZE users;
    ANALYZE organizations;
    ANALYZE companies;
    ANALYZE annual_predictions;
    ANALYZE quarterly_predictions;
    
    -- Reindex if needed (check for bloat first)
    REINDEX INDEX CONCURRENTLY idx_annual_predictions_created_at;
    
    -- Clean up old audit logs (keep 90 days)
    DELETE FROM audit_logs 
    WHERE created_at < CURRENT_DATE - INTERVAL '90 days';
END $$;
```

#### **2. Performance Monitoring Queries**
```sql
-- Monitor slow queries
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements
WHERE mean_time > 1000  -- Queries taking > 1 second on average
ORDER BY total_time DESC
LIMIT 10;

-- Monitor index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE idx_scan < 10  -- Potentially unused indexes
ORDER BY idx_scan;

-- Monitor table bloat
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    pg_stat_get_live_tuples(c.oid) as live_tuples,
    pg_stat_get_dead_tuples(c.oid) as dead_tuples
FROM pg_tables pt
JOIN pg_class c ON c.relname = pt.tablename
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## 🔧 **Database Migration Strategy**

### **Alembic Migration Configuration**
```python
# alembic/env.py configuration
from sqlalchemy import create_engine
from app.core.config import settings
from app.models.base import Base

# Import all models to ensure they're registered
from app.models.user import User
from app.models.organization import Organization
from app.models.company import Company
from app.models.prediction import AnnualPrediction, QuarterlyPrediction
from app.models.bulk_job import BulkUploadJob
from app.models.audit_log import AuditLog

target_metadata = Base.metadata

def run_migrations_online():
    """Run migrations in 'online' mode with connection pooling"""
    connectable = create_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=True  # For SQLite compatibility in tests
        )

        with context.begin_transaction():
            context.run_migrations()
```

### **Migration Best Practices**
```python
# Example migration with proper indexing
"""add_company_search_indexes

Revision ID: abc123def456
Revises: def456ghi789
Create Date: 2023-10-05 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add indexes concurrently to avoid locks in production
    op.execute("CREATE INDEX CONCURRENTLY idx_companies_name_search ON companies USING gin(to_tsvector('english', name))")
    op.execute("CREATE INDEX CONCURRENTLY idx_companies_sector_market_cap ON companies(sector, market_cap DESC)")

def downgrade():
    op.drop_index('idx_companies_name_search', table_name='companies')
    op.drop_index('idx_companies_sector_market_cap', table_name='companies')
```

---

**Last Updated**: October 5, 2025  
**Database Schema Version**: 2.0.0
