# 🚀 Database Setup Scripts

Professional scripts for setting up the Default Rate Prediction System database with complete test data.

## 📋 Scripts Overview

### 1. `reset_database.py` - Database Reset
Completely resets the PostgreSQL database by dropping all tables and recreating them.

**Features:**
- Uses DATABASE_URL from `.env` file
- Safe confirmation prompt
- Comprehensive logging
- Error handling and validation

### 2. `setup_application_data.py` - Complete Data Setup
Creates a professional test environment with all necessary users and organizations.

**Creates:**
- 1 Super Admin
- 1 Tenant with 1 Tenant Admin  
- 2 Organizations with 1 Admin each
- 2 Members per organization (total 9 users)

## 🏗️ Quick Setup Process

### Step 1: Reset Database
```bash
cd /path/to/backend
python scripts/reset_database.py
```

### Step 2: Create Application Data
```bash
python scripts/setup_application_data.py
```

## 👥 Default Users Created

### 👑 Super Admin
- **Email:** `admin@defaultrate.com`
- **Username:** `super_admin`
- **Password:** `SuperAdmin123!`
- **Role:** `super_admin`

### 🏢 Tenant: "FinTech Solutions Enterprise"
- **Domain:** `fintech-solutions.com`
- **Description:** Leading financial technology platform

### 👔 Tenant Admin
- **Email:** `admin@fintech-solutions.com`
- **Username:** `tenant_admin`
- **Password:** `TenantAdmin123!`
- **Role:** `tenant_admin`

### 🏛️ Organization 1: "Risk Assessment Division"
- **Domain:** `risk.fintech-solutions.com`
- **Global Data Access:** Yes

**Admin:**
- **Email:** `risk.admin@fintech-solutions.com`
- **Username:** `risk_admin`
- **Password:** `RiskAdmin123!`

**Members:**
1. **Michael Chen** - `analyst1@fintech-solutions.com` / `risk_analyst_1` / `Analyst123!`
2. **Emily Davis** - `analyst2@fintech-solutions.com` / `risk_analyst_2` / `Analyst123!`

### 🏛️ Organization 2: "Credit Analytics Department"
- **Domain:** `credit.fintech-solutions.com`
- **Global Data Access:** No

**Admin:**
- **Email:** `credit.admin@fintech-solutions.com`
- **Username:** `credit_admin`
- **Password:** `CreditAdmin123!`

**Members:**
1. **Jessica Rodriguez** - `modeler1@fintech-solutions.com` / `credit_modeler_1` / `Modeler123!`
2. **Alex Kumar** - `modeler2@fintech-solutions.com` / `credit_modeler_2` / `Modeler123!`

## 🏗️ Multi-Tenant Architecture

### **User-Tenant-Organization Relationships**

```
SUPER ADMIN
├── tenant_id: NULL
├── organization_id: NULL
└── Can access: EVERYTHING

TENANT ADMIN (Robert Johnson)
├── tenant_id: "fintech-solutions"
├── organization_id: NULL
└── Can manage: ALL orgs within "fintech-solutions" tenant

ORGANIZATION ADMIN (Sarah Williams)
├── tenant_id: NULL
├── organization_id: "risk-assessment-division"
└── Can manage: Users within "risk-assessment-division" org

ORGANIZATION MEMBER (Michael Chen)
├── tenant_id: NULL
├── organization_id: "risk-assessment-division"
└── Can access: Resources within "risk-assessment-division" org

REGULAR USER
├── tenant_id: NULL
├── organization_id: NULL
└── Can access: Limited public resources
```

### **Why Both Fields Are Required**

1. **`tenant_id`** - Links tenant admins to their tenant (1 tenant admin can manage multiple orgs)
2. **`organization_id`** - Links org users to their specific organization (1 user belongs to 1 org)
3. **Both NULL** - Super admins and regular users without organization assignment
4. **Mutually Exclusive** - A user cannot have both tenant_id AND organization_id set

This follows standard **multi-tenant SaaS architecture** patterns used by companies like Slack, Microsoft Teams, etc.

## ⚙️ Customization

To modify the default data, edit the `DATA_CONFIG` dictionary in `setup_application_data.py`:

```python
DATA_CONFIG = {
    "super_admin": {
        "email": "your-admin@company.com",
        "password": "YourPassword123!",
        # ... other fields
    },
    # ... rest of configuration
}
```

## 🔐 Security Features

- Strong password requirements (12+ chars, mixed case, numbers, symbols)
- Professional email domains
- Proper role assignments
- Whitelist entries for organization access
- Secure join tokens generated

## 📊 Database Schema

The scripts work with these main tables:
- `users` - All system users with role-based access
- `tenants` - Enterprise tenant organizations
- `organizations` - Departmental organizations within tenants
- `organization_member_whitelist` - Email whitelist for org access

## 🛠️ Requirements

- Python 3.8+
- PostgreSQL database
- Required Python packages:
  - `sqlalchemy`
  - `psycopg2-binary`
  - `python-dotenv`
  - `werkzeug`

## 📝 Environment Setup

Ensure your `.env` file contains:
```bash
DATABASE_URL="postgresql://user:password@host:port/database"
```

## 🎯 Testing

After setup, test the authentication flow:

1. Start your FastAPI server
2. Import the Postman collection
3. Login with any of the created users
4. Test role-based access controls

## 🔧 Troubleshooting

**Database Connection Issues:**
- Verify DATABASE_URL in `.env`
- Check PostgreSQL server is running
- Ensure database exists and is accessible

**Import Errors:**
- Verify Python path includes backend directory
- Check all required packages are installed
- Ensure virtual environment is activated

**Permission Issues:**
- Check file permissions on scripts
- Verify database user has CREATE/DROP privileges
