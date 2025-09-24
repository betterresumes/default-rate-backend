# Updated API Documentation - Complete Reference

## Overview
This document provides the complete API specification for the Default Rate Prediction system after recent updates including system data separation and dashboard enhancements.

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
All endpoints require JWT Bearer token authentication:
```
Authorization: Bearer <your_jwt_token>
```

---

## 1. PREDICTIONS ENDPOINTS

### 1.1 Get Annual Predictions (Personal + Organization Only)
**GET** `/predictions/annual`

**Description:** Returns user's personal and organization predictions. System data is now excluded.

**Query Parameters:**
- `page` (int, default: 1) - Page number
- `size` (int, default: 10) - Items per page
- `company_symbol` (string, optional) - Filter by company symbol
- `reporting_year` (string, optional) - Filter by reporting year

**Response:**
```json
{
    "success": true,
    "predictions": [
        {
            "id": "uuid",
            "company_id": "uuid",
            "company_symbol": "AAPL",
            "company_name": "Apple Inc.",
            "sector": "Technology",
            "market_cap": 2800000000000,
            "reporting_year": "2024",
            "reporting_quarter": null,
            "long_term_debt_to_total_capital": 0.25,
            "total_debt_to_ebitda": 1.2,
            "net_income_margin": 0.15,
            "ebit_to_interest_expense": 12.5,
            "return_on_assets": 0.18,
            "probability": 0.0245,
            "risk_level": "Low",
            "confidence": 0.92,
            "access_level": "personal",  // or "organization"
            "organization_id": "uuid",
            "organization_name": "Tech Corp",
            "created_by": "uuid",
            "created_by_email": "user@company.com",
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:00Z"
        }
    ],
    "pagination": {
        "total": 150,
        "page": 1,
        "size": 10,
        "pages": 15
    }
}
```

**Access Control:**
- **user/org_member/org_admin**: Personal + Organization data
- **tenant_admin**: Cross-organization data
- **super_admin**: Personal + Organization data (system data excluded)

---

### 1.2 Get Quarterly Predictions (Personal + Organization Only)
**GET** `/predictions/quarterly`

**Description:** Returns user's personal and organization predictions. System data is now excluded.

**Query Parameters:**
- `page` (int, default: 1) - Page number
- `size` (int, default: 10) - Items per page
- `company_symbol` (string, optional) - Filter by company symbol
- `reporting_year` (string, optional) - Filter by reporting year
- `reporting_quarter` (string, optional) - Filter by quarter (Q1, Q2, Q3, Q4)

**Response:**
```json
{
    "success": true,
    "predictions": [
        {
            "id": "uuid",
            "company_id": "uuid",
            "company_symbol": "GOOGL",
            "company_name": "Alphabet Inc.",
            "sector": "Technology",
            "market_cap": 1700000000000,
            "reporting_year": "2024",
            "reporting_quarter": "Q1",
            "total_debt_to_ebitda": 0.8,
            "sga_margin": 0.12,
            "long_term_debt_to_total_capital": 0.15,
            "return_on_capital": 0.22,
            "logistic_probability": 0.0189,
            "gbm_probability": 0.0201,
            "ensemble_probability": 0.0195,
            "risk_level": "Low",
            "confidence": 0.94,
            "access_level": "personal",  // or "organization"
            "organization_id": "uuid",
            "organization_name": "Tech Corp",
            "created_by": "uuid",
            "created_by_email": "user@company.com",
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:00Z"
        }
    ],
    "pagination": {
        "total": 75,
        "page": 1,
        "size": 10,
        "pages": 8
    }
}
```

---

### 1.3 Get System Annual Predictions (NEW)
**GET** `/predictions/annual/system`

**Description:** Returns ONLY system-level annual predictions accessible to all users.

**Query Parameters:**
- `page` (int, default: 1) - Page number
- `size` (int, default: 10) - Items per page
- `company_symbol` (string, optional) - Filter by company symbol
- `reporting_year` (string, optional) - Filter by reporting year
- `sector` (string, optional) - Filter by sector
- `risk_level` (string, optional) - Filter by risk level (Low, Medium, High)

**Response:**
```json
{
    "success": true,
    "predictions": [
        {
            "id": "uuid",
            "company_symbol": "MSFT",
            "company_name": "Microsoft Corporation",
            "sector": "Technology",
            "market_cap": 2500000000000,
            "reporting_year": "2024",
            "long_term_debt_to_total_capital": 0.18,
            "total_debt_to_ebitda": 1.1,
            "net_income_margin": 0.31,
            "ebit_to_interest_expense": 15.2,
            "return_on_assets": 0.16,
            "probability": 0.0156,
            "risk_level": "Low",
            "confidence": 0.96,
            "created_at": "2024-01-10T08:15:00Z"
        }
    ],
    "pagination": {
        "total": 500,
        "page": 1,
        "size": 10,
        "pages": 50
    },
    "metadata": {
        "data_scope": "system",
        "description": "System-level annual predictions available to all users",
        "total_system_predictions": 500
    }
}
```

**Access Control:** All authenticated users can access system predictions

---

### 1.4 Get System Quarterly Predictions (NEW)
**GET** `/predictions/quarterly/system`

**Description:** Returns ONLY system-level quarterly predictions accessible to all users.

**Query Parameters:**
- `page` (int, default: 1) - Page number  
- `size` (int, default: 10) - Items per page
- `company_symbol` (string, optional) - Filter by company symbol
- `reporting_year` (string, optional) - Filter by reporting year
- `reporting_quarter` (string, optional) - Filter by quarter (Q1, Q2, Q3, Q4)
- `sector` (string, optional) - Filter by sector
- `risk_level` (string, optional) - Filter by risk level

**Response:**
```json
{
    "success": true,
    "predictions": [
        {
            "id": "uuid",
            "company_symbol": "TSLA",
            "company_name": "Tesla Inc.",
            "sector": "Automotive",
            "market_cap": 800000000000,
            "reporting_year": "2024",
            "reporting_quarter": "Q2",
            "total_debt_to_ebitda": 2.1,
            "sga_margin": 0.08,
            "long_term_debt_to_total_capital": 0.35,
            "return_on_capital": 0.28,
            "logistic_probability": 0.0234,
            "gbm_probability": 0.0267,
            "ensemble_probability": 0.0251,
            "risk_level": "Low",
            "confidence": 0.91,
            "created_at": "2024-02-05T14:20:00Z"
        }
    ],
    "pagination": {
        "total": 200,
        "page": 1,
        "size": 10,
        "pages": 20
    },
    "metadata": {
        "data_scope": "system",
        "description": "System-level quarterly predictions available to all users",
        "total_system_predictions": 200
    }
}
```

---

## 2. DASHBOARD ENDPOINT (UPDATED)

### 2.1 Get Dashboard Data
**POST** `/predictions/dashboard`

**Description:** Returns user-scoped dashboard data and optional platform statistics with enhanced prediction breakdowns.

**Request Body:**
```json
{
    "include_platform_stats": true
}
```

**Response for Personal User:**
```json
{
    "user_dashboard": {
        "scope": "personal",
        "user_name": "Pranit",
        "organization_name": "Personal Data",
        "total_companies": 18,
        "total_predictions": 400,
        "annual_predictions": 350,          // NEW: Annual predictions count
        "quarterly_predictions": 50,        // NEW: Quarterly predictions count
        "average_default_rate": 0.0202,
        "high_risk_companies": 0,
        "sectors_covered": 8,
        "data_scope": "Personal data only"
    },
    "scope": "personal",
    "platform_statistics": {
        "total_companies": 112,
        "total_predictions": 2882,
        "annual_predictions": 2728,         // Existing field
        "quarterly_predictions": 154,       // Existing field  
        "average_default_rate": 0.0172,
        "high_risk_companies": 0,
        "sectors_covered": 15
        // REMOVED: total_users, total_organizations, total_tenants
    }
}
```

**Response for Organization User:**
```json
{
    "user_dashboard": {
        "scope": "organization",
        "user_name": "John Doe",
        "organization_name": "Tech Innovations Inc",
        "total_companies": 45,
        "total_predictions": 1200,
        "annual_predictions": 980,          // NEW
        "quarterly_predictions": 220,       // NEW
        "average_default_rate": 0.0189,
        "high_risk_companies": 2,
        "sectors_covered": 12,
        "data_scope": "Data within Tech Innovations Inc (Organization data only)"
    },
    "scope": "organization",
    "platform_statistics": {
        "total_companies": 112,
        "total_predictions": 2882,
        "annual_predictions": 2728,
        "quarterly_predictions": 154,
        "average_default_rate": 0.0172,
        "high_risk_companies": 0,
        "sectors_covered": 15
    }
}
```

**Response for Super Admin:**
```json
{
    "user_dashboard": {
        "scope": "system",
        "user_name": "Admin User",
        "organization_name": "System Administrator",
        "total_companies": 112,
        "total_predictions": 2882,
        "annual_predictions": 2728,        // NEW
        "quarterly_predictions": 154,      // NEW
        "average_default_rate": 0.0172,
        "high_risk_companies": 0,
        "sectors_covered": 15,
        "data_scope": "All system data"
    },
    "scope": "system",
    "platform_statistics": {
        "total_companies": 112,
        "total_predictions": 2882,
        "annual_predictions": 2728,
        "quarterly_predictions": 154,
        "average_default_rate": 0.0172,
        "high_risk_companies": 0,
        "sectors_covered": 15
    }
}
```

---

## 3. KEY CHANGES SUMMARY

### 3.1 System Data Separation
- **Regular endpoints** (`/annual`, `/quarterly`) now exclude system data
- **System endpoints** (`/annual/system`, `/quarterly/system`) provide dedicated system data access
- All users can access system data through dedicated endpoints

### 3.2 Dashboard Enhancements
- **Added prediction breakdowns** to user_dashboard: `annual_predictions`, `quarterly_predictions`
- **Removed user/org counts** from platform_statistics: `total_users`, `total_organizations`, `total_tenants`
- **Cleaner platform metrics** focused on business data

### 3.3 Access Control Matrix

| User Role | Regular Endpoints | System Endpoints | Dashboard Scope |
|-----------|------------------|------------------|-----------------|
| **user** | Personal data | System data | Personal |
| **org_member** | Personal + Org data | System data | Organization |
| **org_admin** | Personal + Org data | System data | Organization |  
| **tenant_admin** | Cross-org data | System data | Organization |
| **super_admin** | Personal + Org data | System data | System |

---

## 4. EXAMPLE CURL COMMANDS

### 4.1 Get Personal/Org Annual Predictions
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/predictions/annual?page=1&size=20&company_symbol=AAPL"
```

### 4.2 Get System Annual Predictions  
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/predictions/annual/system?page=1&size=20&sector=Technology"
```

### 4.3 Get Dashboard with Platform Stats
```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"include_platform_stats": true}' \
  "http://localhost:8000/api/v1/predictions/dashboard"
```

### 4.4 Get System Quarterly Predictions
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/predictions/quarterly/system?reporting_year=2024&risk_level=Low"
```

---

## 5. ERROR RESPONSES

### 5.1 Authentication Error
```json
{
    "detail": "Not authenticated"
}
```

### 5.2 Permission Error
```json
{
    "detail": "Authentication required to view predictions"
}
```

### 5.3 Validation Error
```json
{
    "detail": "Invalid page number"
}
```

### 5.4 Server Error
```json
{
    "detail": "Error fetching annual predictions: Database connection failed"
}
```

---

## 6. RESPONSE FIELD DESCRIPTIONS

### 6.1 Annual Prediction Fields
- `probability`: Default probability (0.0 - 1.0)
- `risk_level`: Low (<30%), Medium (30-70%), High (>70%)
- `confidence`: Model confidence score
- `long_term_debt_to_total_capital`: Financial ratio input
- `total_debt_to_ebitda`: Debt to earnings ratio
- `net_income_margin`: Profitability ratio
- `ebit_to_interest_expense`: Interest coverage ratio
- `return_on_assets`: Asset efficiency ratio

### 6.2 Quarterly Prediction Fields  
- `logistic_probability`: Logistic model prediction
- `gbm_probability`: Gradient boosting model prediction
- `ensemble_probability`: Combined model prediction
- `total_debt_to_ebitda`: Debt ratio
- `sga_margin`: Sales, general & admin margin
- `long_term_debt_to_total_capital`: Long-term debt ratio
- `return_on_capital`: Capital efficiency ratio

### 6.3 Access Level Values
- `personal`: User's own predictions
- `organization`: Organization-scoped predictions
- `system`: System-wide predictions available to all

This documentation reflects all recent changes including system data separation and dashboard prediction breakdowns.
