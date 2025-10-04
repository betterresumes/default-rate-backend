# Database Architecture

This document explains how AccuNode stores and organizes data in simple terms with easy-to-understand diagrams.

## What is a Database?

A database is like a digital filing cabinet that stores all of AccuNode's information in organized tables. Think of it like Excel spreadsheets that are connected to each other.

## Database Overview

### Technology Used
- **Database Type**: PostgreSQL (a reliable, professional database)
- **Storage**: All data is stored securely with backups
- **Security**: Each piece of data has unique IDs for security
- **Performance**: Optimized for fast searches and updates

### How Data is Connected

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Tenant    │───▶│Organization │───▶│    User     │
│             │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
                                              │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Predictions │◀───│   Company   │◀───│             │
│             │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
```

## Database Tables (6 Main Tables)

AccuNode stores information in **6 main tables**. Think of each table as a spreadsheet:

### 1. Tenant Table 📊
**Purpose**: Top-level container for multiple organizations

| Field | Type | What It Stores |
|-------|------|----------------|
| **id** | UUID | Unique identifier for each tenant |
| **name** | Text | Tenant name (e.g., "Acme Corporation") |
| **slug** | Text | URL-friendly name (e.g., "acme-corp") |
| **domain** | Text | Website domain (e.g., "acme.com") |
| **description** | Text | About the tenant |
| **logo_url** | Text | Logo image location |
| **is_active** | Yes/No | Whether tenant is enabled |
| **created_by** | UUID | Who created this tenant |
| **created_at** | Date/Time | When it was created |
| **updated_at** | Date/Time | Last update time |

**Real Example:**
```
ID: abc123...
Name: "Tech Solutions Inc"
Slug: "tech-solutions" 
Domain: "techsolutions.com"
Is Active: Yes
```

### 2. Organization Table 🏢  
**Purpose**: Groups within tenants (like departments or divisions)

| Field | Type | What It Stores |
|-------|------|----------------|
| **id** | UUID | Unique identifier |
| **tenant_id** | UUID | Which tenant this belongs to |
| **name** | Text | Organization name (e.g., "Finance Team") |
| **slug** | Text | URL-friendly name |
| **domain** | Text | Organization website |
| **description** | Text | About this organization |
| **max_users** | Number | Maximum users allowed (default: 500) |
| **join_token** | Text | Invitation code for new users |
| **join_enabled** | Yes/No | Whether new users can join |
| **default_role** | Text | Role for new members (default: "org_member") |
| **is_active** | Yes/No | Whether organization is enabled |
| **created_by** | UUID | Who created it |

**Real Example:**
```
Name: "Financial Analysis Department"
Max Users: 50
Join Token: "ABC123XYZ"
Join Enabled: Yes
Default Role: "org_member"
```

### 3. User Table 👤
**Purpose**: All user accounts with their roles and permissions

| Field | Type | What It Stores |
|-------|------|----------------|
| **id** | UUID | Unique identifier |
| **email** | Text | User's email (unique) |
| **username** | Text | Display name (unique) |
| **full_name** | Text | Real name |
| **hashed_password** | Text | Encrypted password |
| **role** | Text | Permission level (user/org_member/org_admin/tenant_admin/super_admin) |
| **tenant_id** | UUID | Which tenant they belong to |
| **organization_id** | UUID | Which organization they're in |
| **is_active** | Yes/No | Account enabled/disabled |
| **created_at** | Date/Time | When account was created |
| **last_login** | Date/Time | Last login time |

**Role Examples:**
- **user**: "john@company.com" - can only see their own data
- **org_member**: "jane@company.com" - can view team data
- **org_admin**: "admin@company.com" - can manage the organization
- **super_admin**: "system@accunode.com" - can manage everything

### 4. Company Table 🏭
**Purpose**: Information about companies being analyzed

| Field | Type | What It Stores |
|-------|------|----------------|
| **id** | UUID | Unique identifier |
| **symbol** | Text | Stock symbol (e.g., "AAPL", "MSFT") |
| **name** | Text | Company name (e.g., "Apple Inc.") |
| **market_cap** | Number | Market value in dollars |
| **sector** | Text | Business sector (e.g., "Technology") |
| **organization_id** | UUID | Which organization owns this data |
| **access_level** | Text | Who can see it (personal/organization/system) |
| **created_by** | UUID | Who added this company |
| **created_at** | Date/Time | When it was added |

**Real Examples:**
```
Symbol: "AAPL"
Name: "Apple Inc."
Market Cap: $2,800,000,000,000
Sector: "Technology"
Access Level: "organization"

Symbol: "MSFT"  
Name: "Microsoft Corporation"
Market Cap: $2,400,000,000,000
Sector: "Technology"
Access Level: "personal"
```

**Business Rule**: Each organization can have only one entry per stock symbol (no duplicates)

### 5. Annual Predictions Table 📈
**Purpose**: Yearly default risk predictions using 5 financial ratios

| Field | Type | What It Stores |
|-------|------|----------------|
| **id** | UUID | Unique identifier |
| **company_id** | UUID | Which company this prediction is for |
| **reporting_year** | Text | Year being analyzed (e.g., "2024") |
| **reporting_quarter** | Text | Optional quarter (e.g., "Q3") |

**Financial Ratios (5 required):**
| Ratio | What It Measures |
|-------|------------------|
| **long_term_debt_to_total_capital** | Long-term debt as % of total capital |
| **total_debt_to_ebitda** | Total debt compared to earnings |
| **net_income_margin** | Profit margin percentage |
| **ebit_to_interest_expense** | Earnings vs interest payments |
| **return_on_assets** | How efficiently assets generate profit |

**Prediction Results:**
| Field | What It Shows |
|-------|---------------|
| **probability** | Default risk probability (0.0 to 1.0) |
| **risk_level** | LOW/MEDIUM/HIGH/CRITICAL |
| **confidence** | How confident the AI is (0.0 to 1.0) |
| **predicted_at** | When prediction was made |

**Real Example:**
```
Company: Apple Inc. (AAPL)
Year: 2024
Long-term Debt to Capital: 15.5%
Total Debt to EBITDA: 2.1
Net Income Margin: 25.3%
EBIT to Interest: 45.2
Return on Assets: 18.7%
→ Result: 2.3% risk (MEDIUM), 85% confidence
```

### 6. Quarterly Predictions Table 📊
**Purpose**: Short-term default risk predictions using 4 financial ratios

| Field | Type | What It Stores |
|-------|------|----------------|
| **id** | UUID | Unique identifier |
| **company_id** | UUID | Which company this prediction is for |
| **reporting_year** | Text | Year being analyzed (e.g., "2024") |
| **reporting_quarter** | Text | Quarter being analyzed (Q1/Q2/Q3/Q4) |

**Financial Ratios (4 required):**
| Ratio | What It Measures |
|-------|------------------|
| **total_debt_to_ebitda** | Total debt compared to earnings |
| **sga_margin** | Sales, General & Admin costs as % |
| **long_term_debt_to_total_capital** | Long-term debt as % of capital |
| **return_on_capital** | How efficiently capital generates returns |

**Advanced AI Predictions (Ensemble Model):**
| Field | What It Shows |
|-------|---------------|
| **logistic_probability** | Logistic model prediction |
| **gbm_probability** | Gradient Boosting model prediction |
| **ensemble_probability** | Combined final prediction |
| **risk_level** | LOW/MEDIUM/HIGH/CRITICAL |
| **confidence** | How confident the AI is |

**Real Example:**
```
Company: Tesla Inc. (TSLA)
Year: 2024, Quarter: Q3
Total Debt to EBITDA: 1.8
SG&A Margin: 7.2%
Long-term Debt to Capital: 8.5%
Return on Capital: 19.4%
→ Results:
  Logistic Model: 3.1% risk
  GBM Model: 2.8% risk  
  Final Ensemble: 2.95% risk (MEDIUM)
  Confidence: 78%
```

## Additional Tables

### 7. Bulk Upload Jobs Table 📤
**Purpose**: Tracks file uploads and batch processing jobs

| Field | Type | What It Stores |
|-------|------|----------------|
| **id** | UUID | Unique job identifier |
| **user_id** | UUID | Who uploaded the file |
| **organization_id** | UUID | Which organization (if any) |
| **job_type** | Text | Type of upload (annual/quarterly predictions) |
| **status** | Text | pending/processing/completed/failed |
| **original_filename** | Text | Name of uploaded file |
| **file_size** | Number | Size of file in bytes |
| **total_rows** | Number | Total rows in the file |
| **processed_rows** | Number | How many rows processed |
| **successful_rows** | Number | How many succeeded |
| **failed_rows** | Number | How many failed |
| **error_message** | Text | What went wrong (if any) |
| **created_at** | Date/Time | When job started |
| **completed_at** | Date/Time | When job finished |

**Job Status Flow:**
```
pending → processing → completed/failed
```

**Real Example:**
```
Filename: "Q3_2024_predictions.xlsx"
Status: "completed"
Total Rows: 1,000
Successful: 987
Failed: 13
Error Message: "13 rows had invalid stock symbols"
```

## How Tables Connect to Each Other

### Data Relationships Diagram

```
┌─────────────┐
│   TENANT    │
└─────┬───────┘
      │ (can have many)
      ▼
┌─────────────┐      ┌─────────────┐
│ORGANIZATION │──────│    USER     │
└─────┬───────┘      └─────────────┘
      │ (owns)             │ (creates)
      ▼                    ▼
┌─────────────┐      ┌─────────────┐
│   COMPANY   │──────│ PREDICTIONS │
└─────────────┘      └─────────────┘
      │                    ▲
      │              ┌─────┴─────┐
      │              │           │
      │         ┌────────┐ ┌────────────┐
      │         │ ANNUAL │ │ QUARTERLY  │
      │         │        │ │            │
      │         └────────┘ └────────────┘
      │
      ▼
┌─────────────┐
│ BULK JOBS   │
└─────────────┘
```

### What Happens When Data is Deleted

**If you delete a Company:**
- ✅ All its Annual Predictions are automatically deleted
- ✅ All its Quarterly Predictions are automatically deleted
- ✅ This prevents orphaned data

**If you delete a User:**
- ⚠️ Their created companies remain (ownership transfers)
- ⚠️ Their predictions remain for historical records
- ✅ Their bulk jobs are marked with deleted user

**If you delete an Organization:**  
- ⚠️ Users are moved out of the organization
- ⚠️ Companies and predictions are preserved
- ✅ Data integrity is maintained

## Data Access Control

### Who Can See What Data?

AccuNode has **3 levels of data access**:

#### 1. Personal Data 👤
- **Who sees it**: Only the person who created it
- **Example**: John creates a prediction for Apple → only John can see it
- **Use case**: Individual analysis, private research

#### 2. Organization Data 🏢  
- **Who sees it**: All members of the organization (based on their role)
- **Example**: Finance team creates predictions → all finance team members can see them
- **Use case**: Team collaboration, shared analysis

#### 3. System Data 🌐
- **Who sees it**: Only Super Administrators
- **Example**: Global market data, system-wide statistics
- **Use case**: Platform management, global insights

### Access Level Examples

```
┌─────────────────────────────────────────────┐
│              ORGANIZATION A                 │
│                                             │
│ John (user)     → Can see: His own data     │
│ Jane (org_member) → Can see: His + Org data │
│ Mike (org_admin)  → Can see: All org data   │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│         SUPER ADMIN (Global View)           │
│                                             │
│ Admin → Can see: Everything in all orgs     │
└─────────────────────────────────────────────┘
```

### Data Privacy Rules

| Your Role | Personal Data | Your Org Data | Other Org Data | System Data |
|-----------|---------------|---------------|----------------|-------------|
| **User** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Org Member** | ✅ Yes | ✅ Read Only | ❌ No | ❌ No |
| **Org Admin** | ✅ Yes | ✅ Full Access | ❌ No | ❌ No |
| **Tenant Admin** | ✅ Yes | ✅ Full Access | ✅ Read Only | ❌ No |
| **Super Admin** | ✅ Yes | ✅ Full Access | ✅ Full Access | ✅ Yes |

## Database Performance & Security

### Performance Features

**Connection Pooling**: 
- The database maintains 20 active connections
- Can scale up to 50 connections during high usage
- Connections are recycled every 5 minutes for freshness

**Fast Searches**:
- Database indexes are like a book's index - they make searches super fast
- Common searches (by company, year, organization) are optimized
- Multiple search criteria can be used together efficiently

**Data Loading**:
- Related data is loaded together to avoid multiple trips to the database
- Example: When you load a company, its predictions come with it

### Security Features

**Unique Identifiers**:
- Every record has a unique ID (UUID) that can't be guessed
- This prevents unauthorized access to data

**Access Filtering**:
- Every database query automatically filters based on user permissions  
- Users can never accidentally see data they shouldn't
- The system double-checks permissions before showing any data

**Data Validation**:
- All data is checked for correctness before being stored
- Invalid data is rejected with helpful error messages
- This keeps the database clean and reliable

### Backup & Recovery

**Automatic Backups**:
- Database is backed up regularly
- Multiple backup copies are kept for safety
- Backups are stored separately from main database

**Data Integrity**:
- The database checks that all relationships make sense
- Orphaned data (predictions without companies) is prevented
- Regular integrity checks ensure data consistency

This architecture ensures AccuNode's data is fast, secure, and always available when you need it.
