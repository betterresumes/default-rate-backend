# 🚀 AccuNode - Complete API Documentation

## 📋 **Table of Contents**
1. [API Overview](#api-overview)
2. [Authentication & Authorization](#authentication--authorization)
3. [Prediction APIs](#prediction-apis)
4. [Company Management APIs](#company-management-apis)
5. [User & Organization APIs](#user--organization-apis)
6. [Bulk Operations APIs](#bulk-operations-apis)
7. [Analytics & Dashboard APIs](#analytics--dashboard-apis)
8. [System & Health APIs](#system--health-apis)
9. [Error Handling](#error-handling)
10. [Code Examples](#code-examples)

---

## 🎯 **API Overview**

### **Base Information**
- **Base URL**: `https://AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com`
- **API Version**: `v1`
- **Protocol**: HTTPS only
- **Content Type**: `application/json`
- **Authentication**: JWT Bearer tokens

### **API Structure**
```
/api/v1/
├── auth/                    # Authentication endpoints
├── predictions/            # ML prediction endpoints  
├── companies/              # Company management
├── users/                  # User management
├── organizations/          # Organization management
├── tenants/                # Tenant management (admin)
├── debug/                  # Debug & diagnostics
└── health/                 # Health checks
```

### **Standard Response Format**
```json
{
    "success": true,
    "message": "Operation completed successfully",
    "data": { /* Response payload */ },
    "pagination": { /* For paginated responses */ },
    "timestamp": "2025-01-05T10:30:00Z"
}
```

### **Rate Limiting**
| Endpoint Type | Rate Limit | Window |
|---------------|------------|--------|
| **ML Predictions** | 10 requests | 1 minute |
| **Data Queries** | 100 requests | 1 minute |
| **File Uploads** | 5 requests | 1 minute |
| **Authentication** | 20 requests | 1 minute |
| **Analytics** | 50 requests | 1 minute |

---

## 🔐 **Authentication & Authorization**

### **1. User Registration**

#### **Public Registration**
```http
POST /api/v1/auth/register
Content-Type: application/json

{
    "email": "john.doe@company.com",
    "username": "johndoe", 
    "full_name": "John Doe",
    "password": "SecurePass123",
    "first_name": "John",
    "last_name": "Doe"
}
```

**Response (201 Created):**
```json
{
    "success": true,
    "message": "Registration successful. Please check your email to verify your account.",
    "data": {
        "user_id": "123e4567-e89b-12d3-a456-426614174000",
        "email": "john.doe@company.com",
        "status": "pending_verification",
        "verification_sent": true
    }
}
```

#### **Email Verification**
```http
GET /api/v1/auth/verify-email?token={verification_token}
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Email verified successfully. You can now log in.",
    "data": {
        "user_id": "123e4567-e89b-12d3-a456-426614174000",
        "email": "john.doe@company.com", 
        "status": "verified",
        "verified_at": "2025-01-05T10:30:00Z"
    }
}
```

### **2. Authentication**

#### **Login**
```http
POST /api/v1/auth/token
Content-Type: application/x-www-form-urlencoded

username=john.doe@company.com&password=SecurePass123
```

**Response (200 OK):**
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer",
    "expires_in": 3600,
    "user": {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "email": "john.doe@company.com",
        "role": "user",
        "organization_id": null,
        "full_name": "John Doe"
    }
}
```

#### **Token Refresh**
```http
POST /api/v1/auth/refresh
Authorization: Bearer {current_token}
```

#### **Profile Information**
```http
GET /api/v1/auth/me
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
    "success": true,
    "data": {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "email": "john.doe@company.com",
        "username": "johndoe",
        "full_name": "John Doe",
        "role": "org_member",
        "organization_id": "456e7890-e89b-12d3-a456-426614174001",
        "organization_name": "Tech Corp Inc",
        "created_at": "2025-01-01T00:00:00Z",
        "last_login": "2025-01-05T10:30:00Z"
    }
}
```

### **3. Authorization Headers**
```http
# All authenticated requests must include:
Authorization: Bearer {access_token}
Content-Type: application/json
```

---

## 📊 **Prediction APIs**

### **1. Create Annual Prediction**

#### **Single Prediction**
```http
POST /api/v1/predictions/annual
Authorization: Bearer {access_token}
Content-Type: application/json

{
    "company_symbol": "AAPL",
    "company_name": "Apple Inc.",
    "sector": "Technology", 
    "market_cap": 2800000000000,
    "reporting_year": "2024",
    "long_term_debt_to_total_capital": 0.25,
    "total_debt_to_ebitda": 1.2,
    "net_income_margin": 0.23,
    "ebit_to_interest_expense": 15.6,
    "return_on_assets": 0.18
}
```

**Response (201 Created):**
```json
{
    "success": true,
    "message": "Annual prediction created for AAPL",
    "prediction": {
        "id": "789e1234-e89b-12d3-a456-426614174002",
        "company_id": "456e7890-e89b-12d3-a456-426614174003",
        "company_symbol": "AAPL",
        "company_name": "Apple Inc.",
        "sector": "Technology",
        "market_cap": 2800000000000,
        "reporting_year": "2024",
        "financial_ratios": {
            "long_term_debt_to_total_capital": 0.25,
            "total_debt_to_ebitda": 1.2,
            "net_income_margin": 0.23,
            "ebit_to_interest_expense": 15.6,
            "return_on_assets": 0.18
        },
        "ml_results": {
            "probability": 0.15,
            "risk_level": "Low",
            "confidence": 0.89
        },
        "access_level": "organization",
        "organization_id": "456e7890-e89b-12d3-a456-426614174001",
        "organization_name": "Tech Corp Inc", 
        "created_by": "123e4567-e89b-12d3-a456-426614174000",
        "predicted_at": "2025-01-05T10:30:00Z"
    }
}
```

### **2. Create Quarterly Prediction**

```http
POST /api/v1/predictions/quarterly
Authorization: Bearer {access_token}
Content-Type: application/json

{
    "company_symbol": "MSFT",
    "company_name": "Microsoft Corporation",
    "sector": "Technology",
    "market_cap": 2500000000000,
    "reporting_year": "2024", 
    "reporting_quarter": "Q3",
    "current_ratio": 2.1,
    "quick_ratio": 2.0,
    "debt_to_equity": 0.35,
    "inventory_turnover": 8.5,
    "receivables_turnover": 6.2,
    "working_capital_to_total_assets": 0.12
}
```

**Response (201 Created):**
```json
{
    "success": true,
    "message": "Quarterly prediction created for MSFT",
    "prediction": {
        "id": "789e5678-e89b-12d3-a456-426614174004",
        "company_id": "456e7890-e89b-12d3-a456-426614174005", 
        "company_symbol": "MSFT",
        "company_name": "Microsoft Corporation",
        "sector": "Technology",
        "market_cap": 2500000000000,
        "reporting_year": "2024",
        "reporting_quarter": "Q3",
        "financial_ratios": {
            "current_ratio": 2.1,
            "quick_ratio": 2.0,
            "debt_to_equity": 0.35,
            "inventory_turnover": 8.5,
            "receivables_turnover": 6.2,
            "working_capital_to_total_assets": 0.12
        },
        "ml_results": {
            "logistic_probability": 0.12,
            "gbm_probability": 0.09,
            "ensemble_probability": 0.10,
            "risk_level": "Low",
            "confidence": 0.92
        },
        "access_level": "organization",
        "organization_id": "456e7890-e89b-12d3-a456-426614174001",
        "predicted_at": "2025-01-05T10:30:00Z"
    }
}
```

### **3. Retrieve Predictions**

#### **Get Annual Predictions (Paginated)**
```http
GET /api/v1/predictions/annual?page=1&size=10&company_symbol=AAPL&reporting_year=2024
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
    "success": true,
    "predictions": [
        {
            "id": "789e1234-e89b-12d3-a456-426614174002",
            "company_id": "456e7890-e89b-12d3-a456-426614174003",
            "company_symbol": "AAPL",
            "company_name": "Apple Inc.",
            "sector": "Technology",
            "market_cap": 2800000000000,
            "reporting_year": "2024",
            "probability": 0.15,
            "risk_level": "Low",
            "confidence": 0.89,
            "access_level": "organization",
            "organization_id": "456e7890-e89b-12d3-a456-426614174001",
            "organization_name": "Tech Corp Inc",
            "created_by": "123e4567-e89b-12d3-a456-426614174000",
            "created_by_email": "john.doe@company.com",
            "created_at": "2025-01-05T10:30:00Z"
        }
    ],
    "pagination": {
        "total": 25,
        "page": 1,
        "size": 10,
        "pages": 3
    }
}
```

#### **Get Quarterly Predictions**
```http
GET /api/v1/predictions/quarterly?page=1&size=10&reporting_year=2024&reporting_quarter=Q3
Authorization: Bearer {access_token}
```

#### **Get System-Level Predictions** (Public Data)
```http
# Annual system predictions (accessible to all users)
GET /api/v1/predictions/annual/system?page=1&size=10&sector=Technology&risk_level=Low

# Quarterly system predictions  
GET /api/v1/predictions/quarterly/system?page=1&size=10&sector=Healthcare
```

---

## 🏢 **Company Management APIs**

### **1. Get Companies**

#### **List All Companies (Paginated)**
```http
GET /api/v1/companies?page=1&limit=20&sector=Technology&search=Apple&sort_by=market_cap&sort_order=desc
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
    "success": true,
    "data": {
        "items": [
            {
                "id": "456e7890-e89b-12d3-a456-426614174003",
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "sector": "Technology", 
                "market_cap": 2800000000000,
                "access_level": "organization",
                "organization_id": "456e7890-e89b-12d3-a456-426614174001",
                "created_at": "2025-01-01T00:00:00Z",
                "annual_predictions": [
                    {
                        "id": "789e1234-e89b-12d3-a456-426614174002",
                        "reporting_year": "2024",
                        "risk_level": "Low",
                        "probability": 0.15,
                        "confidence": 0.89
                    }
                ],
                "quarterly_predictions": [
                    {
                        "id": "789e5678-e89b-12d3-a456-426614174004", 
                        "reporting_year": "2024",
                        "reporting_quarter": "Q3",
                        "risk_level": "Low",
                        "ensemble_probability": 0.10
                    }
                ]
            }
        ],
        "total": 150,
        "page": 1,
        "size": 20,
        "pages": 8
    }
}
```

### **2. Get Company Details**

#### **Company by ID**
```http
GET /api/v1/companies/{company_id}
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
    "success": true,
    "data": {
        "id": "456e7890-e89b-12d3-a456-426614174003",
        "symbol": "AAPL", 
        "name": "Apple Inc.",
        "sector": "Technology",
        "market_cap": 2800000000000,
        "access_level": "organization",
        "organization_id": "456e7890-e89b-12d3-a456-426614174001",
        "created_at": "2025-01-01T00:00:00Z",
        "statistics": {
            "total_predictions": 8,
            "annual_predictions": 4,
            "quarterly_predictions": 4,
            "average_risk_level": "Low",
            "latest_prediction": "2025-01-05T10:30:00Z"
        },
        "predictions": {
            "annual": [
                {
                    "id": "789e1234-e89b-12d3-a456-426614174002",
                    "reporting_year": "2024",
                    "probability": 0.15,
                    "risk_level": "Low",
                    "confidence": 0.89,
                    "financial_ratios": {
                        "long_term_debt_to_total_capital": 0.25,
                        "total_debt_to_ebitda": 1.2,
                        "net_income_margin": 0.23,
                        "ebit_to_interest_expense": 15.6,
                        "return_on_assets": 0.18
                    },
                    "created_at": "2025-01-05T10:30:00Z"
                }
            ],
            "quarterly": [
                {
                    "id": "789e5678-e89b-12d3-a456-426614174004",
                    "reporting_year": "2024",
                    "reporting_quarter": "Q3", 
                    "ensemble_probability": 0.10,
                    "logistic_probability": 0.12,
                    "gbm_probability": 0.09,
                    "risk_level": "Low",
                    "confidence": 0.92,
                    "created_at": "2025-01-05T10:30:00Z"
                }
            ]
        }
    }
}
```

---

## 👥 **User & Organization APIs**

### **1. Organization Management**

#### **Create Organization**
```http
POST /api/v1/organizations
Authorization: Bearer {access_token}
Content-Type: application/json

{
    "name": "Tech Innovations Inc",
    "domain": "techinnovations.com", 
    "description": "Leading technology innovation company"
}
```

#### **Join Organization**
```http
POST /api/v1/organizations/join
Authorization: Bearer {access_token}
Content-Type: application/json

{
    "join_code": "TECH2024-ABC123",
    "organization_name": "Tech Innovations Inc"
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "message": "Successfully joined Tech Innovations Inc",
    "data": {
        "organization_id": "456e7890-e89b-12d3-a456-426614174001",
        "organization_name": "Tech Innovations Inc",
        "user_role": "org_member", 
        "joined_at": "2025-01-05T10:30:00Z"
    }
}
```

#### **List Organizations**
```http
GET /api/v1/organizations?page=1&size=10
Authorization: Bearer {access_token}
```

### **2. User Management**

#### **List Organization Users**
```http
GET /api/v1/users?organization_id={org_id}&role=org_member&page=1&size=20
Authorization: Bearer {access_token}
```

#### **Update User Role** (Admin only)
```http
PUT /api/v1/users/{user_id}/role
Authorization: Bearer {access_token}
Content-Type: application/json

{
    "role": "org_admin",
    "updated_by_reason": "Promotion to admin role"
}
```

---

## 📁 **Bulk Operations APIs**

### **1. Bulk Upload Predictions**

#### **Upload CSV File**
```http
POST /api/v1/predictions/bulk-upload
Authorization: Bearer {access_token}
Content-Type: multipart/form-data

file=@predictions.csv&prediction_type=annual
```

**CSV Format (Annual):**
```csv
company_symbol,company_name,sector,market_cap,reporting_year,long_term_debt_to_total_capital,total_debt_to_ebitda,net_income_margin,ebit_to_interest_expense,return_on_assets
AAPL,Apple Inc.,Technology,2800000000000,2024,0.25,1.2,0.23,15.6,0.18
MSFT,Microsoft Corporation,Technology,2500000000000,2024,0.30,1.5,0.25,12.8,0.16
GOOGL,Alphabet Inc.,Technology,1800000000000,2024,0.15,0.9,0.21,18.2,0.14
```

**CSV Format (Quarterly):**
```csv
company_symbol,company_name,sector,market_cap,reporting_year,reporting_quarter,current_ratio,quick_ratio,debt_to_equity,inventory_turnover,receivables_turnover,working_capital_to_total_assets
AAPL,Apple Inc.,Technology,2800000000000,2024,Q3,2.1,2.0,0.35,8.5,6.2,0.12
MSFT,Microsoft Corporation,Technology,2500000000000,2024,Q3,1.9,1.8,0.42,7.2,5.8,0.15
```

**Response (202 Accepted):**
```json
{
    "success": true,
    "message": "Bulk upload job started successfully",
    "job": {
        "job_id": "bulk-123e4567-e89b-12d3-a456-426614174006",
        "status": "processing",
        "total_rows": 150,
        "prediction_type": "annual",
        "started_at": "2025-01-05T10:30:00Z",
        "estimated_completion": "2025-01-05T10:35:00Z"
    }
}
```

### **2. Job Management**

#### **List Bulk Jobs**
```http
GET /api/v1/predictions/jobs?status=completed&limit=20&offset=0
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
    "success": true,
    "jobs": [
        {
            "id": "bulk-123e4567-e89b-12d3-a456-426614174006",
            "status": "completed",
            "job_type": "annual",
            "total_rows": 150,
            "successful_rows": 147,
            "failed_rows": 3,
            "created_at": "2025-01-05T10:30:00Z",
            "started_at": "2025-01-05T10:30:05Z",
            "completed_at": "2025-01-05T10:34:22Z",
            "processing_time": "4 minutes 17 seconds"
        }
    ],
    "pagination": {
        "total": 12,
        "limit": 20,
        "offset": 0,
        "has_next": false
    }
}
```

#### **Get Job Status**
```http
GET /api/v1/predictions/jobs/{job_id}
Authorization: Bearer {access_token}
```

#### **Get Job Results**
```http
POST /api/v1/predictions/jobs/{job_id}/results
Authorization: Bearer {access_token}
Content-Type: application/json

{
    "include_predictions": true,
    "include_errors": true,
    "include_companies": false
}
```

**Response (200 OK):**
```json
{
    "success": true,
    "job_summary": {
        "id": "bulk-123e4567-e89b-12d3-a456-426614174006",
        "status": "completed",
        "total_rows": 150,
        "successful_rows": 147,
        "failed_rows": 3,
        "processing_time": "4 minutes 17 seconds"
    },
    "results": {
        "predictions_created": [
            {
                "id": "789e1234-e89b-12d3-a456-426614174007",
                "company_symbol": "AAPL",
                "reporting_year": "2024",
                "probability": 0.15,
                "risk_level": "Low"
            }
        ],
        "errors": [
            {
                "row": 45,
                "company_symbol": "INVALID",
                "error": "Invalid market cap value: negative number not allowed"
            }
        ],
        "summary": {
            "by_risk_level": {
                "Low": 89,
                "Medium": 45,
                "High": 13
            },
            "by_sector": {
                "Technology": 67,
                "Healthcare": 34,
                "Finance": 28,
                "Energy": 18
            }
        }
    }
}
```

#### **Cancel Job**
```http
DELETE /api/v1/predictions/jobs/{job_id}
Authorization: Bearer {access_token}
```

---

## 📈 **Analytics & Dashboard APIs**

### **1. Dashboard Data**

#### **Personal Dashboard**
```http
GET /api/v1/predictions/dashboard
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
    "success": true,
    "dashboard": {
        "scope": "personal",
        "user_name": "John Doe",
        "organization_name": "Tech Corp Inc",
        "summary": {
            "total_companies": 25,
            "total_predictions": 87,
            "annual_predictions": 52,
            "quarterly_predictions": 35,
            "average_default_rate": 0.2145,
            "high_risk_companies": 8,
            "sectors_covered": ["Technology", "Healthcare", "Finance"]
        },
        "recent_activity": {
            "last_prediction": "2025-01-05T10:30:00Z",
            "predictions_this_week": 12,
            "predictions_this_month": 43
        },
        "risk_distribution": {
            "Low": 54,
            "Medium": 25,
            "High": 8
        },
        "top_companies": [
            {
                "company_symbol": "AAPL",
                "company_name": "Apple Inc.", 
                "prediction_count": 8,
                "latest_risk_level": "Low"
            }
        ]
    }
}
```

#### **Organization Dashboard**
```http
GET /api/v1/predictions/dashboard?include_platform_stats=true
Authorization: Bearer {access_token}
```

### **2. Statistics & Analytics**

#### **Prediction Statistics**
```http
GET /api/v1/predictions/stats
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
    "success": true,
    "generated_at": "2025-01-05T10:30:00Z",
    "summary": {
        "total_predictions": 12567,
        "annual_predictions": 7834,
        "quarterly_predictions": 4733,
        "total_companies": 2341,
        "total_users": 145,
        "total_organizations": 23,
        "recent_activity": {
            "last_7_days": {
                "annual": 234,
                "quarterly": 156,
                "total": 390
            }
        }
    },
    "breakdown": {
        "by_access_level": {
            "personal": 6234,
            "organization": 4567, 
            "system": 1766
        },
        "by_risk_level": {
            "Low": 8934,
            "Medium": 2987,
            "High": 646
        },
        "by_sector": {
            "Technology": 4567,
            "Healthcare": 2341,
            "Finance": 2987,
            "Energy": 1456,
            "Others": 1216
        }
    },
    "user_context": {
        "personal": {
            "annual": 52,
            "quarterly": 35,
            "total": 87
        },
        "organization": {
            "annual": 234,
            "quarterly": 178,
            "total": 412
        },
        "accessible_total": {
            "annual": 2156,
            "quarterly": 1432,
            "total": 3588
        }
    },
    "top_contributors": [
        {
            "user_id": "123e4567-e89b-12d3-a456-426614174000",
            "user_name": "John Doe",
            "organization_name": "Tech Corp Inc",
            "annual_predictions": 156,
            "quarterly_predictions": 89,
            "total_predictions": 245
        }
    ],
    "most_predicted_companies": [
        {
            "company_symbol": "AAPL",
            "company_name": "Apple Inc.",
            "sector": "Technology",
            "annual_predictions": 23,
            "quarterly_predictions": 18,
            "total_predictions": 41
        }
    ]
}
```

### **3. Export & Reporting**

#### **Export Predictions**
```http
GET /api/v1/predictions/export?format=csv&date_from=2024-01-01&date_to=2024-12-31&prediction_type=annual
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```csv
Content-Type: text/csv
Content-Disposition: attachment; filename="annual_predictions_2024.csv"

id,company_symbol,company_name,sector,reporting_year,probability,risk_level,confidence,created_at,created_by
789e1234-e89b-12d3-a456-426614174002,AAPL,Apple Inc.,Technology,2024,0.15,Low,0.89,2025-01-05T10:30:00Z,john.doe@company.com
...
```

---

## ⚡ **System & Health APIs**

### **1. Health Checks**

#### **API Health**
```http
GET /health
```

**Response (200 OK):**
```json
{
    "status": "healthy",
    "timestamp": "2025-01-05T10:30:00Z",
    "version": "1.0.0",
    "environment": "production",
    "services": {
        "database": "connected",
        "redis": "connected", 
        "ml_models": "loaded"
    },
    "uptime": "72h 15m 32s"
}
```

#### **Detailed System Health**
```http
GET /api/v1/health/detailed
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
    "status": "healthy",
    "checks": {
        "database": {
            "status": "healthy",
            "response_time": "12ms",
            "connections": {
                "active": 15,
                "max": 20
            }
        },
        "redis": {
            "status": "healthy", 
            "response_time": "3ms",
            "memory_usage": "245MB",
            "connected_clients": 8
        },
        "ml_models": {
            "annual_model": {
                "status": "loaded",
                "last_prediction": "2025-01-05T10:29:45Z",
                "model_version": "v2.1"
            },
            "quarterly_model": {
                "status": "loaded",
                "last_prediction": "2025-01-05T10:28:12Z", 
                "model_version": "v1.8"
            }
        },
        "celery_workers": {
            "active_workers": 2,
            "pending_tasks": 5,
            "processed_tasks": 1547
        }
    },
    "metrics": {
        "requests_per_minute": 45,
        "average_response_time": "156ms",
        "error_rate": "0.02%"
    }
}
```

### **2. Debug Endpoints**

#### **Debug Prediction Ownership**
```http
GET /api/v1/predictions/debug/prediction/{prediction_id}
Authorization: Bearer {access_token}
```

#### **Debug Job Analysis**
```http
GET /api/v1/predictions/jobs/{job_id}/debug
Authorization: Bearer {access_token}
```

---

## ❌ **Error Handling**

### **Standard Error Response Format**
```json
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid input data provided",
        "details": {
            "field": "market_cap",
            "issue": "Value must be greater than 0"
        }
    },
    "timestamp": "2025-01-05T10:30:00Z",
    "request_id": "req_123e4567-e89b-12d3-a456"
}
```

### **HTTP Status Codes**

| Code | Meaning | Usage |
|------|---------|-------|
| **200** | OK | Successful GET requests |
| **201** | Created | Successful POST requests (resource created) |
| **202** | Accepted | Async operations started (bulk uploads) |
| **400** | Bad Request | Invalid request data or parameters |
| **401** | Unauthorized | Missing or invalid authentication |
| **403** | Forbidden | Insufficient permissions for resource |
| **404** | Not Found | Resource does not exist |
| **409** | Conflict | Resource already exists (duplicate) |
| **422** | Unprocessable Entity | Valid format but invalid data |
| **429** | Too Many Requests | Rate limit exceeded |
| **500** | Internal Server Error | Server-side error |
| **503** | Service Unavailable | Temporary service downtime |

### **Common Error Codes**

#### **Authentication Errors**
```json
// 401 - Missing token
{
    "success": false,
    "error": {
        "code": "MISSING_TOKEN", 
        "message": "Authentication token required"
    }
}

// 401 - Invalid token
{
    "success": false,
    "error": {
        "code": "INVALID_TOKEN",
        "message": "Token is invalid or expired"
    }
}

// 403 - Insufficient permissions
{
    "success": false,
    "error": {
        "code": "INSUFFICIENT_PERMISSIONS",
        "message": "You don't have permission to access this resource"
    }
}
```

#### **Validation Errors**
```json
// 400 - Invalid data format
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Input validation failed",
        "details": [
            {
                "field": "market_cap",
                "message": "Value must be greater than 0"
            },
            {
                "field": "reporting_year", 
                "message": "Must be a valid 4-digit year"
            }
        ]
    }
}
```

#### **Rate Limiting Errors**
```json
// 429 - Rate limit exceeded
{
    "success": false,
    "error": {
        "code": "RATE_LIMIT_EXCEEDED",
        "message": "Too many requests. Try again later.",
        "details": {
            "limit": 10,
            "window": "1 minute",
            "retry_after": 45
        }
    }
}
```

#### **Resource Errors**
```json
// 409 - Duplicate prediction
{
    "success": false,
    "error": {
        "code": "DUPLICATE_PREDICTION",
        "message": "Prediction already exists for this company and reporting period",
        "details": {
            "existing_prediction_id": "789e1234-e89b-12d3-a456-426614174002"
        }
    }
}

// 404 - Resource not found
{
    "success": false,
    "error": {
        "code": "RESOURCE_NOT_FOUND",
        "message": "The requested resource was not found"
    }
}
```

---

## 💻 **Code Examples**

### **1. Python Client Examples**

#### **Basic Authentication & Prediction**
```python
import requests
import json

# Base URL
BASE_URL = "https://AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com/api/v1"

class AccuNodeClient:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.token = None
        self.session = requests.Session()
    
    def login(self, email, password):
        """Authenticate and store token"""
        response = self.session.post(
            f"{self.base_url}/auth/token",
            data={
                "username": email,
                "password": password
            }
        )
        response.raise_for_status()
        
        data = response.json()
        self.token = data["access_token"]
        
        # Set authorization header for future requests
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}"
        })
        
        return data["user"]
    
    def create_annual_prediction(self, prediction_data):
        """Create annual prediction"""
        response = self.session.post(
            f"{self.base_url}/predictions/annual",
            json=prediction_data
        )
        response.raise_for_status()
        return response.json()
    
    def create_quarterly_prediction(self, prediction_data):
        """Create quarterly prediction"""
        response = self.session.post(
            f"{self.base_url}/predictions/quarterly",
            json=prediction_data
        )
        response.raise_for_status()
        return response.json()
    
    def get_predictions(self, prediction_type="annual", **filters):
        """Get predictions with optional filters"""
        response = self.session.get(
            f"{self.base_url}/predictions/{prediction_type}",
            params=filters
        )
        response.raise_for_status()
        return response.json()
    
    def bulk_upload(self, file_path, prediction_type="annual"):
        """Upload CSV file for bulk predictions"""
        with open(file_path, 'rb') as file:
            files = {'file': file}
            data = {'prediction_type': prediction_type}
            
            response = self.session.post(
                f"{self.base_url}/predictions/bulk-upload",
                files=files,
                data=data
            )
        response.raise_for_status()
        return response.json()

# Usage example
client = AccuNodeClient()

# Login
user = client.login("john.doe@company.com", "SecurePass123")
print(f"Logged in as: {user['full_name']}")

# Create annual prediction
annual_data = {
    "company_symbol": "AAPL",
    "company_name": "Apple Inc.",
    "sector": "Technology",
    "market_cap": 2800000000000,
    "reporting_year": "2024",
    "long_term_debt_to_total_capital": 0.25,
    "total_debt_to_ebitda": 1.2,
    "net_income_margin": 0.23,
    "ebit_to_interest_expense": 15.6,
    "return_on_assets": 0.18
}

result = client.create_annual_prediction(annual_data)
print(f"Prediction created: {result['prediction']['id']}")
print(f"Risk Level: {result['prediction']['ml_results']['risk_level']}")
print(f"Default Probability: {result['prediction']['ml_results']['probability']:.3f}")

# Get all predictions
predictions = client.get_predictions(
    prediction_type="annual",
    page=1,
    size=10,
    company_symbol="AAPL"
)
print(f"Found {predictions['pagination']['total']} predictions")
```

### **2. JavaScript/Node.js Examples**

```javascript
const axios = require('axios');

class AccuNodeAPI {
    constructor(baseURL = 'https://AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com/api/v1') {
        this.baseURL = baseURL;
        this.token = null;
        this.client = axios.create({
            baseURL: this.baseURL
        });
        
        // Response interceptor for error handling
        this.client.interceptors.response.use(
            response => response,
            error => {
                if (error.response?.status === 401) {
                    console.error('Authentication failed - token may be expired');
                }
                return Promise.reject(error);
            }
        );
    }
    
    async login(email, password) {
        try {
            const response = await this.client.post('/auth/token', {
                username: email,
                password: password
            }, {
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            });
            
            this.token = response.data.access_token;
            
            // Set default authorization header
            this.client.defaults.headers.common['Authorization'] = `Bearer ${this.token}`;
            
            return response.data.user;
        } catch (error) {
            throw new Error(`Login failed: ${error.response?.data?.error?.message}`);
        }
    }
    
    async createAnnualPrediction(predictionData) {
        try {
            const response = await this.client.post('/predictions/annual', predictionData);
            return response.data;
        } catch (error) {
            throw new Error(`Prediction failed: ${error.response?.data?.error?.message}`);
        }
    }
    
    async bulkUpload(filePath, predictionType = 'annual') {
        const FormData = require('form-data');
        const fs = require('fs');
        
        const form = new FormData();
        form.append('file', fs.createReadStream(filePath));
        form.append('prediction_type', predictionType);
        
        try {
            const response = await this.client.post('/predictions/bulk-upload', form, {
                headers: {
                    ...form.getHeaders()
                }
            });
            return response.data;
        } catch (error) {
            throw new Error(`Bulk upload failed: ${error.response?.data?.error?.message}`);
        }
    }
    
    async getJobStatus(jobId) {
        try {
            const response = await this.client.get(`/predictions/jobs/${jobId}`);
            return response.data;
        } catch (error) {
            throw new Error(`Failed to get job status: ${error.response?.data?.error?.message}`);
        }
    }
    
    async getDashboard() {
        try {
            const response = await this.client.get('/predictions/dashboard');
            return response.data;
        } catch (error) {
            throw new Error(`Failed to get dashboard: ${error.response?.data?.error?.message}`);
        }
    }
}

// Usage example
(async () => {
    const api = new AccuNodeAPI();
    
    try {
        // Login
        const user = await api.login('john.doe@company.com', 'SecurePass123');
        console.log(`Logged in as: ${user.full_name}`);
        
        // Create prediction
        const predictionResult = await api.createAnnualPrediction({
            company_symbol: 'AAPL',
            company_name: 'Apple Inc.',
            sector: 'Technology',
            market_cap: 2800000000000,
            reporting_year: '2024',
            long_term_debt_to_total_capital: 0.25,
            total_debt_to_ebitda: 1.2,
            net_income_margin: 0.23,
            ebit_to_interest_expense: 15.6,
            return_on_assets: 0.18
        });
        
        console.log('Prediction Result:', {
            id: predictionResult.prediction.id,
            risk_level: predictionResult.prediction.ml_results.risk_level,
            probability: predictionResult.prediction.ml_results.probability
        });
        
        // Get dashboard
        const dashboard = await api.getDashboard();
        console.log('Dashboard Summary:', dashboard.dashboard.summary);
        
    } catch (error) {
        console.error('Error:', error.message);
    }
})();
```

### **3. cURL Examples**

#### **Authentication**
```bash
# Login and get token
curl -X POST "https://AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com/api/v1/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=john.doe@company.com&password=SecurePass123"

# Store token (replace with actual token from response)
export TOKEN="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

#### **Create Predictions**
```bash
# Annual prediction
curl -X POST "https://AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com/api/v1/predictions/annual" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "company_symbol": "AAPL",
    "company_name": "Apple Inc.",
    "sector": "Technology",
    "market_cap": 2800000000000,
    "reporting_year": "2024",
    "long_term_debt_to_total_capital": 0.25,
    "total_debt_to_ebitda": 1.2,
    "net_income_margin": 0.23,
    "ebit_to_interest_expense": 15.6,
    "return_on_assets": 0.18
  }'

# Quarterly prediction  
curl -X POST "https://AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com/api/v1/predictions/quarterly" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "company_symbol": "MSFT", 
    "company_name": "Microsoft Corporation",
    "sector": "Technology",
    "market_cap": 2500000000000,
    "reporting_year": "2024",
    "reporting_quarter": "Q3",
    "current_ratio": 2.1,
    "quick_ratio": 2.0,
    "debt_to_equity": 0.35,
    "inventory_turnover": 8.5,
    "receivables_turnover": 6.2,
    "working_capital_to_total_assets": 0.12
  }'
```

#### **Bulk Upload**
```bash
# Upload CSV file
curl -X POST "https://AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com/api/v1/predictions/bulk-upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@predictions.csv" \
  -F "prediction_type=annual"
```

#### **Get Data**
```bash
# Get predictions with filters
curl -X GET "https://AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com/api/v1/predictions/annual?page=1&size=10&company_symbol=AAPL" \
  -H "Authorization: Bearer $TOKEN"

# Get dashboard
curl -X GET "https://AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com/api/v1/predictions/dashboard" \
  -H "Authorization: Bearer $TOKEN"

# Get statistics
curl -X GET "https://AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com/api/v1/predictions/stats" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🔧 **Development & Testing**

### **API Testing with Postman**

1. **Import Collection**: Create Postman collection with all endpoints
2. **Environment Variables**: Set up variables for `base_url`, `token`, etc.
3. **Authentication Flow**: Set up pre-request scripts to handle token refresh
4. **Test Scripts**: Add automated tests for response validation

### **Rate Limiting Testing**
```bash
# Test rate limits
for i in {1..15}; do
  curl -X POST "https://AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com/api/v1/predictions/annual" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"company_symbol": "TEST'$i'", ...}' &
done
```

This completes the comprehensive API documentation. Would you like me to continue with the next documentation section, such as:

3. **AWS Infrastructure Detailed Guide**
4. **Local Development Setup Guide**  
5. **Production Deployment & Operations Guide**

Which section should I work on next?
