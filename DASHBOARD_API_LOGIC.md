# Dashboard API Logic Explanation

## Overview

The `/predictions/dashboard` API endpoint is a **POST endpoint** that provides role-based dashboard data with optional platform statistics. It implements a sophisticated access control system that shows different data based on the user's role and organization membership.

## API Flow Architecture

```
User Request → Authentication → Role Detection → Data Filtering → Response Generation
```

## Step-by-Step Logic Breakdown

### 1. **Request Structure**
```json
POST /api/v1/predictions/dashboard
Content-Type: application/json
Authorization: Bearer <token>

{
  "include_platform_stats": true/false,
  "organization_filter": null,
  "custom_scope": null
}
```

### 2. **Authentication & User Detection**
- Validates JWT token
- Extracts current user information
- Checks if user is active and verified

### 3. **Role-Based Scope Determination**

The API determines the user's data scope based on their role:

```python
if current_user.role == "super_admin":
    scope = "system"  # See ALL system data
elif current_user.role in ["tenant_admin", "org_admin", "org_member"] and current_user.organization_id:
    scope = "organization"  # See organization data
else:
    scope = "personal"  # See only personal data
```

#### **Scope Hierarchy:**
- **System Scope** (Super Admin): All companies, predictions, users system-wide
- **Organization Scope** (Org Users): Only their organization's data
- **Personal Scope** (Regular Users): Only data they created

### 4. **Data Filtering Logic**

#### **A. System Dashboard (Super Admin)**
```python
async def get_system_dashboard(db: Session, current_user: User):
    # Gets EVERYTHING - no filtering
    total_companies = db.query(Company).count()
    total_predictions = db.query(AnnualPrediction).count() + db.query(QuarterlyPrediction).count()
    # ... calculate averages, sectors, etc.
```

#### **B. Organization Dashboard (Org Users)**
```python
async def get_organization_dashboard(db: Session, current_user: User):
    if current_user.role == "tenant_admin":
        # Tenant admin sees ALL organizations
        companies = db.query(Company).all()
        annual_predictions = db.query(AnnualPrediction).all()
        quarterly_predictions = db.query(QuarterlyPrediction).all()
    else:
        # Regular org users see ONLY their organization's data
        companies = db.query(Company).filter(
            Company.organization_id == current_user.organization_id
        ).all()
        
        annual_predictions = db.query(AnnualPrediction).filter(
            AnnualPrediction.organization_id == current_user.organization_id
        ).all()
        
        quarterly_predictions = db.query(QuarterlyPrediction).filter(
            QuarterlyPrediction.organization_id == current_user.organization_id
        ).all()
```

#### **C. Personal Dashboard (Personal Users)**
```python
async def get_personal_dashboard(db: Session, current_user: User):
    # Only data created by this specific user
    companies = db.query(Company).filter(Company.created_by == str(current_user.id)).all()
    annual_predictions = db.query(AnnualPrediction).filter(AnnualPrediction.created_by == str(current_user.id)).all()
    quarterly_predictions = db.query(QuarterlyPrediction).filter(QuarterlyPrediction.created_by == str(current_user.id)).all()
```

### 5. **Data Calculation Process**

For each scope, the API calculates:

```python
# Basic counts
total_companies = len(companies)
total_predictions = len(annual_predictions) + len(quarterly_predictions)

# Risk analysis
annual_probs = [p.probability for p in annual_predictions if p.probability is not None]
quarterly_probs = [p.logistic_probability for p in quarterly_predictions if p.logistic_probability is not None]
all_probs = annual_probs + quarterly_probs
average_default_rate = sum(all_probs) / len(all_probs) if all_probs else 0

# High risk companies (>70% default probability)
high_risk_annual = len([p for p in annual_predictions if p.probability and p.probability > 0.7])
high_risk_quarterly = len([p for p in quarterly_predictions if p.logistic_probability and p.logistic_probability > 0.7])
high_risk_companies = high_risk_annual + high_risk_quarterly

# Sector diversity
sectors = set([c.sector for c in companies if c.sector])
sectors_covered = len(sectors)
```

### 6. **Platform Statistics (Optional)**

If `include_platform_stats: true`, the API adds system-wide statistics:

```python
async def get_platform_statistics(db: Session):
    # Always shows complete system data regardless of user role
    total_companies = db.query(Company).count()
    total_users = db.query(User).count()
    total_organizations = db.query(Organization).count()
    # ... calculate platform-wide metrics
```

### 7. **Response Structure**

The API returns **separate objects** for user data and platform stats:

```json
{
  "user_dashboard": {
    "scope": "organization",
    "user_name": "Robert Chen",
    "organization_name": "Morgan Stanley Credit Risk Division",
    "total_companies": 8,
    "total_predictions": 7,
    "average_default_rate": 0.0167,
    "high_risk_companies": 0,
    "sectors_covered": 2,
    "data_scope": "Data within Morgan Stanley Credit Risk Division (Organization data only)"
  },
  "scope": "organization",
  "platform_statistics": {  // Only if include_platform_stats: true
    "total_companies": 94,
    "total_users": 10,
    "total_organizations": 2,
    "total_tenants": 1,
    "total_predictions": 2482,
    "annual_predictions": 2478,
    "quarterly_predictions": 4,
    "average_default_rate": 0.0169,
    "high_risk_companies": 0,
    "sectors_covered": 14
  }
}
```

## Key Design Principles

### 1. **Data Isolation**
- Users see only data they're authorized to access
- No mixing of personal, organization, and system data
- Clear separation between user scope data and platform statistics

### 2. **Role-Based Access Control**
```
Super Admin    → System-wide data
Tenant Admin   → Cross-organization data
Org Admin      → Organization data only
Org Member     → Organization data only
Regular User   → Personal data only
```

### 3. **Optional Platform Context**
- Platform statistics are separate from user data
- Users can choose to include or exclude system-wide context
- Enables comparison between user's scope and overall platform

### 4. **Performance Optimization**
- Uses ORM queries instead of complex SQL for reliability
- Calculates metrics in Python for better maintainability
- Separate functions for each scope reduce complexity

## Example User Scenarios

### **Morgan Stanley Risk Director**
- **Role**: `org_admin`
- **Organization**: Morgan Stanley Credit Risk Division
- **Sees**: 8 companies, 7 predictions from Morgan Stanley only
- **Platform Stats**: 94 total companies, 2482 predictions system-wide

### **Super Admin**
- **Role**: `super_admin`
- **Organization**: None (system level)
- **Sees**: All 94 companies, all 2482 predictions
- **Platform Stats**: Same as user data (they see everything)

### **Regular User**
- **Role**: `user`
- **Organization**: None
- **Sees**: Only companies and predictions they personally created
- **Platform Stats**: System-wide context for comparison

## Security Features

1. **JWT Authentication**: Every request requires valid token
2. **Role Verification**: User role determines data access
3. **Organization Filtering**: Automatic filtering by organization membership
4. **Data Separation**: User data and platform stats are separate objects
5. **No Data Leakage**: Users cannot access unauthorized data

This architecture ensures that each user gets exactly the data they should see based on their role and organizational context, while optionally providing platform-wide context for business intelligence purposes.
