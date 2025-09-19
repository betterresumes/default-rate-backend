# Complete Postman Collection for Multi-Tenant Financial Risk API

## 📋 Overview

This comprehensive Postman collection includes all working APIs for the multi-tenant financial risk prediction system with proper environment variables, authentication, and sample data.

## 🚀 Quick Setup

### 1. Import Collection
- Import `COMPLETE_POSTMAN_COLLECTION_FINAL.json` into Postman
- The collection includes all necessary environment variables

### 2. Environment Variables
The collection automatically manages these variables:
- `baseUrl`: API base URL (default: http://localhost:8000)
- `token`: JWT access token (auto-populated after login)
- `userId`: Current user ID (auto-populated)
- `organizationId`: Organization ID (auto-populated)
- `tenantId`: Tenant ID (auto-populated)
- `companyId`: Company ID (auto-populated)
- `predictionId`: Prediction ID (auto-populated)
- `jobId`: Background job ID (auto-populated)

### 3. Authentication Setup
1. Start with **Register User** to create a super admin
2. Use **Login User** to get authentication token
3. Token is automatically stored and used for subsequent requests

## 📂 Collection Structure

### 🔐 Authentication (4 endpoints)
- **Register User**: Create new user account
- **Login User**: Authenticate and get JWT token
- **Register Organization User**: Create user with organization membership
- **Get Current User**: Get current user profile

### 🏢 Tenants (4 endpoints)
- **Create Tenant**: Create new tenant
- **List Tenants**: Get paginated tenant list
- **Get Tenant by ID**: Get specific tenant details
- **Update Tenant**: Modify tenant information

### 🏛️ Organizations (6 endpoints)
- **Create Organization**: Create new organization
- **List Organizations**: Get paginated organization list
- **Get Organization by ID**: Get specific organization details
- **Update Organization**: Modify organization information
- **Enable Global Data Access**: Configure global data access
- **Get Global Data Access Status**: Check access permissions

### 🏢 Companies (4 endpoints)
- **Create Company**: Create new company record
- **List Companies**: Get paginated company list
- **Get Company by Symbol**: Get specific company by symbol
- **Search Companies**: Search companies with filters

### 📊 Annual Predictions (6 endpoints)
- **Create Annual Prediction**: Create single annual prediction
- **Get Annual Predictions**: List predictions with pagination
- **Get Annual Predictions with Filters**: Filter by symbol/year
- **Update Annual Prediction**: Modify existing prediction
- **Delete Annual Prediction**: Remove prediction
- **Bulk Upload Annual (Async)**: Upload CSV file asynchronously

### 📈 Quarterly Predictions (6 endpoints)
- **Create Quarterly Prediction**: Create single quarterly prediction
- **Get Quarterly Predictions**: List predictions with pagination
- **Get Quarterly Predictions with Filters**: Filter by symbol/year/quarter
- **Update Quarterly Prediction**: Modify existing prediction
- **Delete Quarterly Prediction**: Remove prediction
- **Bulk Upload Quarterly (Async)**: Upload CSV file asynchronously

### 🔄 Job Management (3 endpoints)
- **Get Job Status**: Check background job progress
- **List All Jobs**: Get all background jobs
- **List Jobs by Status**: Filter jobs by status

### 📊 Legacy Bulk Upload (1 endpoint)
- **Bulk Upload (Synchronous)**: Synchronous bulk upload (for smaller files)

## 🔧 Usage Guide

### Basic Workflow
1. **Authentication**: Register → Login
2. **Setup**: Create Tenant → Create Organization
3. **Data**: Create/Upload Predictions
4. **Monitor**: Check Job Status for async uploads

### Role-Based Access
- **super_admin**: Full access to all endpoints
- **tenant_admin**: Tenant-specific administration
- **org_admin**: Organization administration + prediction management
- **org_member**: Basic prediction operations
- **user**: Limited read access

### Sample Data Files
- `sample_annual_predictions.csv`: Template for annual predictions
- `sample_quarterly_predictions.csv`: Template for quarterly predictions

## 📄 CSV File Formats

### Annual Predictions CSV
```csv
company_symbol,company_name,market_cap,sector,reporting_year,reporting_quarter,long_term_debt_to_total_capital,total_debt_to_ebitda,net_income_margin,ebit_to_interest_expense,return_on_assets
AAPL,Apple Inc.,3000000,Technology,2024,Q1,0.25,1.8,0.15,12.5,0.18
```

### Quarterly Predictions CSV
```csv
company_symbol,company_name,market_cap,sector,reporting_year,reporting_quarter,total_debt_to_ebitda,sga_margin,long_term_debt_to_total_capital,return_on_capital
AAPL,Apple Inc.,3000000,Technology,2024,Q1,1.8,0.12,0.25,0.28
```

## ⚡ Advanced Features

### Async Bulk Upload
- Upload up to 10,000 rows
- Real-time progress tracking
- Background processing with job management
- Error handling and reporting

### Multi-Tenant Support
- Organization-scoped data access
- Global data sharing capabilities
- Role-based permissions
- Tenant isolation

### Comprehensive CRUD
- Full Create, Read, Update, Delete operations
- Pagination and filtering
- Search capabilities
- Data validation

## 🔍 Testing Tips

### Test Sequences
1. **Authentication Flow**: Register → Login → Get User
2. **Organization Setup**: Create Tenant → Create Org → Enable Global Access
3. **Prediction Workflow**: Create → Read → Update → Delete
4. **Bulk Upload**: Upload File → Monitor Job → Check Results

### Common Use Cases
- **Financial Analyst**: Create individual predictions
- **Data Manager**: Bulk upload historical data
- **Organization Admin**: Manage team access and data
- **System Admin**: Global data management

## 📊 Response Examples

### Successful Prediction Creation
```json
{
  "success": true,
  "message": "Annual prediction created for AAPL",
  "prediction": {
    "id": "uuid-here",
    "company_symbol": "AAPL",
    "company_name": "Apple Inc.",
    "reporting_year": "2024",
    "reporting_quarter": "Q1",
    "probability": 0.85,
    "risk_level": "Low",
    "confidence": 0.92
  }
}
```

### Job Status Response
```json
{
  "success": true,
  "job": {
    "id": "job-uuid",
    "status": "processing",
    "progress_percentage": 45.5,
    "processed_rows": 455,
    "total_rows": 1000,
    "successful_rows": 440,
    "failed_rows": 15
  }
}
```

## 🛠️ Troubleshooting

### Common Issues
1. **401 Unauthorized**: Login to refresh token
2. **403 Forbidden**: Check user role permissions
3. **404 Not Found**: Verify resource IDs
4. **400 Bad Request**: Check request body format

### File Upload Issues
- Ensure CSV headers match required format
- Check file size (max 10,000 rows)
- Verify file encoding (UTF-8)

## 📈 Performance Notes

- Async uploads recommended for files > 100 rows
- Pagination used for large result sets
- Background processing prevents timeouts
- Real-time job monitoring available

## 🔒 Security Features

- JWT token authentication
- Role-based access control
- Organization data isolation
- Input validation and sanitization
- SQL injection protection

This collection provides complete coverage of the financial risk prediction API with enterprise-grade features including async processing, multi-tenant architecture, and comprehensive CRUD operations.
