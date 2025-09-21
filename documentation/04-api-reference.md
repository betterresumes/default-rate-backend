# 🔌 API Reference

## 🌐 Base Information

**Base URL**: `http://localhost:8000`  
**API Version**: v1  
**Documentation**: `http://localhost:8000/docs` (Interactive Swagger UI)  
**Authentication**: Bearer JWT tokens  

## 🔐 Authentication

All API endpoints (except public ones) require JWT authentication:

```bash
# Login to get token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Use token in subsequent requests
curl -X GET "http://localhost:8000/api/v1/users/profile" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 📚 Complete API Endpoints

### 1. 🔐 Authentication & Authorization

#### POST /api/v1/auth/register
Register a new user account.

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.doe@example.com",
    "username": "johndoe",
    "password": "SecurePass123",
    "full_name": "John Doe"
  }'
```

**Response**:
```json
{
  "id": "uuid-here",
  "email": "john.doe@example.com",
  "username": "johndoe",
  "full_name": "John Doe",
  "role": "user",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### POST /api/v1/auth/login
Authenticate user and receive JWT tokens.

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.doe@example.com",
    "password": "SecurePass123"
  }'
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "uuid-here",
    "email": "john.doe@example.com",
    "role": "user",
    "organization_id": null
  }
}
```

#### POST /api/v1/auth/join
Join an organization using invitation token.

```bash
curl -X POST "http://localhost:8000/api/v1/auth/join" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "join_token": "org_join_token_here"
  }'
```

#### POST /api/v1/auth/refresh
Refresh expired JWT token.

```bash
curl -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "your_refresh_token"
  }'
```

### 2. 👥 User Management

#### GET /api/v1/users/profile
Get current user's profile information.

```bash
curl -X GET "http://localhost:8000/api/v1/users/profile" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response**:
```json
{
  "id": "uuid-here",
  "email": "john.doe@example.com",
  "username": "johndoe",
  "full_name": "John Doe",
  "role": "org_member",
  "organization_id": "org-uuid",
  "organization_name": "HDFC Risk Division",
  "tenant_id": null,
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "last_login": "2024-01-15T10:30:00Z"
}
```

#### PUT /api/v1/users/profile
Update current user's profile.

```bash
curl -X PUT "http://localhost:8000/api/v1/users/profile" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "full_name": "John Updated Doe",
    "username": "johndoe_updated"
  }'
```

#### GET /api/v1/users/me
Alternative endpoint for current user info.

#### GET /api/v1/users (Admin Only)
List all users with pagination and filtering.

```bash
curl -X GET "http://localhost:8000/api/v1/users?page=1&limit=20&search=john&role=org_member&is_active=true" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

### 3. 🏢 Tenant Management (Super Admin Only)

#### POST /api/v1/tenants
Create a new tenant.

```bash
curl -X POST "http://localhost:8000/api/v1/tenants" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer SUPER_ADMIN_TOKEN" \
  -d '{
    "name": "Banking Corporation",
    "description": "Leading banking group"
  }'
```

#### GET /api/v1/tenants
List all tenants.

```bash
curl -X GET "http://localhost:8000/api/v1/tenants" \
  -H "Authorization: Bearer SUPER_ADMIN_TOKEN"
```

#### GET /api/v1/tenants/{tenant_id}
Get specific tenant details.

#### PUT /api/v1/tenants/{tenant_id}
Update tenant information.

#### DELETE /api/v1/tenants/{tenant_id}
Delete a tenant.

#### GET /api/v1/tenants/{tenant_id}/stats
Get tenant statistics and metrics.

### 4. 🏛️ Organization Management

#### POST /api/v1/organizations
Create a new organization.

```bash
curl -X POST "http://localhost:8000/api/v1/organizations" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TENANT_ADMIN_TOKEN" \
  -d '{
    "name": "HDFC Risk Assessment Division",
    "description": "Credit risk analysis team",
    "domain": "risk.hdfc.com",
    "default_role": "org_member",
    "max_users": 500,
    "allow_global_data_access": true
  }'
```

**Response**:
```json
{
  "id": "org-uuid",
  "name": "HDFC Risk Assessment Division",
  "slug": "hdfc-risk-assessment-division",
  "join_token": "abc123xyz",
  "is_active": true,
  "member_count": 0,
  "max_users": 500,
  "allow_global_data_access": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### GET /api/v1/organizations
List accessible organizations with pagination and filtering.

```bash
curl -X GET "http://localhost:8000/api/v1/organizations?page=1&limit=10&search=HDFC&is_active=true" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### GET /api/v1/organizations/{org_id}
Get organization details.

#### PUT /api/v1/organizations/{org_id}
Update organization (Admin only).

#### DELETE /api/v1/organizations/{org_id}
Delete organization (Admin only).

#### POST /api/v1/organizations/{org_id}/regenerate-token
Generate new join token.

```bash
curl -X POST "http://localhost:8000/api/v1/organizations/{org_id}/regenerate-token" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ORG_ADMIN_TOKEN" \
  -d '{
    "role": "org_member",
    "expires_in_hours": 168
  }'
```

#### GET /api/v1/organizations/{org_id}/users
Get organization members.

#### GET /api/v1/organizations/{org_id}/whitelist
Get organization email whitelist.

#### POST /api/v1/organizations/{org_id}/whitelist
Add email to whitelist.

```bash
curl -X POST "http://localhost:8000/api/v1/organizations/{org_id}/whitelist" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ORG_ADMIN_TOKEN" \
  -d '{
    "email": "newmember@company.com",
    "role": "org_member"
  }'
```

### 5. 🏭 Company Management

#### GET /api/v1/companies
List accessible companies with pagination and filtering.

```bash
curl -X GET "http://localhost:8000/api/v1/companies?page=1&limit=10&sector=Banking&search=HDFC&sort_by=name&sort_order=asc" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response**:
```json
{
  "items": [
    {
      "id": "company-uuid",
      "symbol": "HDFC",
      "name": "HDFC Bank Limited",
      "market_cap": 5000000000.00,
      "sector": "Banking",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z",
      "annual_predictions": [
        {
          "id": "prediction-uuid",
          "reporting_year": "2024",
          "probability": 0.1234,
          "risk_level": "LOW",
          "confidence": 0.89,
          "created_at": "2024-01-15T14:30:00Z"
        }
      ],
      "quarterly_predictions": [
        {
          "id": "prediction-uuid",
          "reporting_year": "2024", 
          "reporting_quarter": "Q1",
          "probability": 0.1567,
          "risk_level": "LOW",
          "confidence": 0.91,
          "created_at": "2024-01-15T14:30:00Z"
        }
      ]
    }
  ],
  "total": 1,
  "page": 1,
  "size": 10,
  "pages": 1
}
```

#### POST /api/v1/companies
Create a new company.

```bash
curl -X POST "http://localhost:8000/api/v1/companies" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ORG_MEMBER_TOKEN" \
  -d '{
    "symbol": "HDFC",
    "name": "HDFC Bank Limited",
    "market_cap": 5000000000,
    "sector": "Banking"
  }'
```

#### GET /api/v1/companies/{company_id}
Get company details.

#### GET /api/v1/companies/search/{symbol}
Search company by symbol.

```bash
curl -X GET "http://localhost:8000/api/v1/companies/search/HDFC" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 6. 📊 Predictions - Core Operations

#### POST /api/v1/predictions/annual
Create annual default risk prediction with comprehensive company data.

```bash
curl -X POST "http://localhost:8000/api/v1/predictions/annual" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ORG_MEMBER_TOKEN" \
  -d '{
    "company_symbol": "HDFC",
    "company_name": "HDFC Bank Limited",
    "market_cap": 5000000000.0,
    "sector": "Banking",
    "reporting_year": "2024",
    "reporting_quarter": "Q1",
    "long_term_debt_to_total_capital": 0.35,
    "total_debt_to_ebitda": 2.5,
    "net_income_margin": 0.15,
    "ebit_to_interest_expense": 5.2,
    "return_on_assets": 0.08
  }'
```

**Response**:
```json
{
  "success": true,
  "message": "Annual prediction created successfully",
  "prediction_id": "prediction-uuid",
  "company": {
    "id": "company-uuid",
    "symbol": "HDFC",
    "name": "HDFC Bank Limited",
    "sector": "Banking"
  },
  "prediction": {
    "probability": 0.1234,
    "risk_level": "LOW",
    "confidence": 0.89,
    "reporting_year": "2024",
    "reporting_quarter": "Q1",
    "created_at": "2024-01-15T14:30:00Z"
  },
  "created_by": "user-uuid"
}
```

#### POST /api/v1/predictions/quarterly
Create quarterly default risk prediction with comprehensive company data.

```bash
curl -X POST "http://localhost:8000/api/v1/predictions/quarterly" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ORG_MEMBER_TOKEN" \
  -d '{
    "company_symbol": "HDFC",
    "company_name": "HDFC Bank Limited",
    "market_cap": 5000000000.0,
    "sector": "Banking",
    "reporting_year": "2024",
    "reporting_quarter": "Q1",
    "total_debt_to_ebitda": 2.3,
    "sga_margin": 0.25,
    "long_term_debt_to_total_capital": 0.32,
    "return_on_capital": 0.12
  }'
```

**Response**:
```json
{
  "success": true,
  "message": "Quarterly prediction created successfully",
  "prediction_id": "prediction-uuid",
  "company": {
    "id": "company-uuid",
    "symbol": "HDFC",
    "name": "HDFC Bank Limited",
    "sector": "Banking"
  },
  "prediction": {
    "probability": 0.1567,
    "risk_level": "LOW",
    "confidence": 0.91,
    "reporting_year": "2024",
    "reporting_quarter": "Q1",
    "created_at": "2024-01-15T14:30:00Z"
  },
  "created_by": "user-uuid"
}
```

#### GET /api/v1/predictions/annual
Get annual predictions with filtering and pagination.

```bash
curl -X GET "http://localhost:8000/api/v1/predictions/annual?page=1&size=10&company_symbol=HDFC&reporting_year=2024" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response**:
```json
{
  "success": true,
  "predictions": [
    {
      "id": "prediction-uuid",
      "company": {
        "id": "company-uuid",
        "symbol": "HDFC",
        "name": "HDFC Bank Limited",
        "sector": "Banking"
      },
      "reporting_year": "2024",
      "reporting_quarter": "Q1",
      "probability": 0.1234,
      "risk_level": "LOW",
      "confidence": 0.89,
      "financial_ratios": {
        "long_term_debt_to_total_capital": 0.35,
        "total_debt_to_ebitda": 2.5,
        "net_income_margin": 0.15,
        "ebit_to_interest_expense": 5.2,
        "return_on_assets": 0.08
      },
      "created_at": "2024-01-15T14:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "size": 10,
    "total": 1,
    "pages": 1
  }
}
```

#### GET /api/v1/predictions/quarterly
Get quarterly predictions with filtering and pagination.

```bash
curl -X GET "http://localhost:8000/api/v1/predictions/quarterly?page=1&size=10&company_symbol=HDFC&reporting_year=2024&reporting_quarter=Q1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response**:
```json
{
  "success": true,
  "predictions": [
    {
      "id": "prediction-uuid", 
      "company": {
        "id": "company-uuid",
        "symbol": "HDFC",
        "name": "HDFC Bank Limited",
        "sector": "Banking"
      },
      "reporting_year": "2024",
      "reporting_quarter": "Q1",
      "probability": 0.1567,
      "risk_level": "LOW",
      "confidence": 0.91,
      "financial_ratios": {
        "total_debt_to_ebitda": 2.3,
        "sga_margin": 0.25,
        "long_term_debt_to_total_capital": 0.32,
        "return_on_capital": 0.12
      },
      "created_at": "2024-01-15T14:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "size": 10,
    "total": 1,
    "pages": 1
  }
}
```

### 7. 📋 Bulk Operations

#### POST /api/v1/predictions/bulk-upload
Synchronous bulk upload (small files).

```bash
curl -X POST "http://localhost:8000/api/v1/predictions/bulk-upload" \
  -H "Authorization: Bearer ORG_MEMBER_TOKEN" \
  -F "file=@predictions.csv" \
  -F "prediction_type=annual"
```

#### POST /api/v1/predictions/annual/bulk-upload-async
Async annual bulk upload (large files).

```bash
curl -X POST "http://localhost:8000/api/v1/predictions/annual/bulk-upload-async" \
  -H "Authorization: Bearer ORG_MEMBER_TOKEN" \
  -F "file=@annual_predictions.csv"
```

**Response**:
```json
{
  "job_id": "job-uuid",
  "status": "queued",
  "message": "Bulk upload job queued successfully",
  "estimated_processing_time": "5-10 minutes",
  "total_rows": 1500,
  "job_type": "annual"
}
```

#### POST /api/v1/predictions/quarterly/bulk-upload-async
Async quarterly bulk upload.

```bash
curl -X POST "http://localhost:8000/api/v1/predictions/quarterly/bulk-upload-async" \
  -H "Authorization: Bearer ORG_MEMBER_TOKEN" \
  -F "file=@quarterly_predictions.csv"
```

### 8. ⚙️ Job Management

#### POST /api/v1/predictions/bulk-upload
Synchronous bulk prediction upload from CSV file.

```bash
curl -X POST "http://localhost:8000/api/v1/predictions/bulk-upload" \
  -H "Authorization: Bearer ORG_MEMBER_TOKEN" \
  -F "file=@predictions.csv" \
  -F "prediction_type=annual"
```

**CSV Format**:
```csv
company_symbol,company_name,market_cap,sector,reporting_year,reporting_quarter,long_term_debt_to_total_capital,total_debt_to_ebitda,net_income_margin,ebit_to_interest_expense,return_on_assets
HDFC,HDFC Bank Limited,5000000000,Banking,2024,Q1,0.35,2.5,0.15,5.2,0.08
```

#### POST /api/v1/predictions/annual/bulk-upload-async
Asynchronous bulk upload for annual predictions.

```bash
curl -X POST "http://localhost:8000/api/v1/predictions/annual/bulk-upload-async" \
  -H "Authorization: Bearer ORG_MEMBER_TOKEN" \
  -F "file=@annual_predictions.csv"
```

**Response**:
```json
{
  "success": true,
  "job_id": "job-uuid-123",
  "message": "Bulk upload job started. Use job_id to check status.",
  "status_url": "/api/v1/predictions/jobs/job-uuid-123/status"
}
```

#### POST /api/v1/predictions/quarterly/bulk-upload-async
Asynchronous bulk upload for quarterly predictions.

```bash
curl -X POST "http://localhost:8000/api/v1/predictions/quarterly/bulk-upload-async" \
  -H "Authorization: Bearer ORG_MEMBER_TOKEN" \
  -F "file=@quarterly_predictions.csv"
```

#### GET /api/v1/predictions/jobs/{job_id}/status
Get bulk upload job status.

```bash
curl -X GET "http://localhost:8000/api/v1/predictions/jobs/job-uuid/status" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response**:
```json
{
  "job": {
    "id": "job-uuid",
    "status": "processing",
    "job_type": "annual",
    "progress": {
      "total_rows": 1500,
      "processed_rows": 750,
      "successful_rows": 740,
      "failed_rows": 10,
      "percentage": 50
    },
    "timing": {
      "started_at": "2024-01-15T14:00:00Z",
      "estimated_completion": "2024-01-15T14:08:00Z"
    },
    "errors": [
      {
        "row": 45,
        "error": "Invalid financial metric value",
        "details": "net_income_margin cannot be negative"
      }
    ]
  }
}
```

#### GET /api/v1/predictions/jobs
List all jobs for current user/organization.

```bash
curl -X GET "http://localhost:8000/api/v1/predictions/jobs?status=completed&skip=0&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 8.1 ✏️ Prediction Management

#### PUT /api/v1/predictions/annual/{prediction_id}
Update an annual prediction.

```bash
curl -X PUT "http://localhost:8000/api/v1/predictions/annual/prediction-uuid" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ORG_MEMBER_TOKEN" \
  -d '{
    "long_term_debt_to_total_capital": 0.40,
    "total_debt_to_ebitda": 2.8,
    "net_income_margin": 0.18,
    "ebit_to_interest_expense": 5.5,
    "return_on_assets": 0.09
  }'
```

#### DELETE /api/v1/predictions/annual/{prediction_id}
Delete an annual prediction.

```bash
curl -X DELETE "http://localhost:8000/api/v1/predictions/annual/prediction-uuid" \
  -H "Authorization: Bearer ORG_MEMBER_TOKEN"
```

#### PUT /api/v1/predictions/quarterly/{prediction_id}
Update a quarterly prediction.

```bash
curl -X PUT "http://localhost:8000/api/v1/predictions/quarterly/prediction-uuid" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ORG_MEMBER_TOKEN" \
  -d '{
    "total_debt_to_ebitda": 2.1,
    "sga_margin": 0.22,
    "long_term_debt_to_total_capital": 0.30,
    "return_on_capital": 0.14
  }'
```

#### DELETE /api/v1/predictions/quarterly/{prediction_id}
Delete a quarterly prediction.

```bash
curl -X DELETE "http://localhost:8000/api/v1/predictions/quarterly/prediction-uuid" \
  -H "Authorization: Bearer ORG_MEMBER_TOKEN"
```

### 9. 👑 Super Admin Operations

#### POST /api/v1/create-tenant-with-admin
Create tenant and admin user atomically.

```bash
curl -X POST "http://localhost:8000/api/v1/create-tenant-with-admin" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer SUPER_ADMIN_TOKEN" \
  -d '{
    "tenant_name": "Banking Corporation",
    "tenant_description": "Leading banking group",
    "admin_email": "admin@banking-corp.com",
    "admin_password": "AdminPass123",
    "admin_first_name": "John",
    "admin_last_name": "Admin",
    "create_default_org": true,
    "default_org_name": "Main Division"
  }'
```

#### POST /api/v1/assign-existing-user
Assign existing user as tenant admin.

```bash
curl -X POST "http://localhost:8000/api/v1/assign-existing-user" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer SUPER_ADMIN_TOKEN" \
  -d '{
    "user_email": "existing.user@example.com",
    "tenant_id": "tenant-uuid",
    "role": "tenant_admin"
  }'
```

#### POST /api/v1/assign-user-to-organization
Assign user to organization with role.

```bash
curl -X POST "http://localhost:8000/api/v1/assign-user-to-organization" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer SUPER_ADMIN_TOKEN" \
  -d '{
    "user_email": "user@example.com",
    "organization_id": "org-uuid",
    "role": "org_admin"
  }'
```

### 10. 🌐 System Endpoints

#### GET /
Root endpoint with system information.

```bash
curl -X GET "http://localhost:8000/"
```

#### GET /health
System health check.

```bash
curl -X GET "http://localhost:8000/health"
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T14:30:00Z",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "redis": "connected",
    "celery": "active"
  }
}
```

## 🔒 Authentication Patterns

### Token Management
```javascript
// Frontend token management example
class AuthService {
  async login(email, password) {
    const response = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    
    const data = await response.json();
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    return data;
  }
  
  async makeAuthenticatedRequest(url, options = {}) {
    const token = localStorage.getItem('access_token');
    return fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        'Authorization': `Bearer ${token}`
      }
    });
  }
}
```

## 📁 CSV File Formats

### Annual Predictions CSV Format
```csv
company_symbol,company_name,market_cap,sector,reporting_year,long_term_debt_to_total_capital,total_debt_to_ebitda,net_income_margin,ebit_to_interest_expense,return_on_assets
HDFC,HDFC Bank Limited,5000000000,Banking,2024,0.35,2.5,0.15,5.2,0.08
ICICI,ICICI Bank Limited,4500000000,Banking,2024,0.32,2.3,0.14,5.8,0.09
```

### Quarterly Predictions CSV Format
```csv
company_symbol,company_name,market_cap,sector,reporting_year,reporting_quarter,total_debt_to_ebitda,sga_margin,long_term_debt_to_total_capital,return_on_capital
HDFC,HDFC Bank Limited,5000000000,Banking,2024,Q1,2.3,0.25,0.32,0.12
ICICI,ICICI Bank Limited,4500000000,Banking,2024,Q1,2.1,0.23,0.30,0.13
```

## ⚡ Rate Limits & Performance

- **Authentication**: 10 requests/minute per IP
- **Regular APIs**: 100 requests/minute per user
- **Bulk Upload**: 5 concurrent jobs per organization
- **File Size Limit**: 50MB for bulk uploads
- **Timeout**: 30 seconds for sync operations, 30 minutes for async jobs

---

This API reference covers all 62+ working endpoints with complete examples for frontend integration.
