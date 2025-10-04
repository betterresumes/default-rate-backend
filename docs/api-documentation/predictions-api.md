# ML Predictions API

This document explains the ML Predictions API for AccuNode's default rate prediction system. The API provides financial risk assessment using machine learning models trained on company financial ratios.

## Overview

AccuNode offers two types of financial risk predictions:

### Annual Predictions 📅
- **Purpose**: Long-term financial risk assessment
- **Financial Ratios**: 5 key ratios (debt, profitability, efficiency)
- **Model**: Logistic Regression 
- **Output**: Probability score (0-1), risk level, confidence score

### Quarterly Predictions 📊  
- **Purpose**: Short-term financial risk assessment
- **Financial Ratios**: 4 key ratios (debt, margins, capital efficiency)
- **Model**: Ensemble (Logistic Regression + LightGBM)
- **Output**: Multiple probabilities, risk level, confidence score

## Base Information

- **Base URL**: `/api/v1/predictions`
- **Authentication**: Bearer JWT token required
- **Access Control**: Multi-tenant with 3-level hierarchy (personal/organization/system)
- **Rate Limiting**: Applied to all ML endpoints

## Core Endpoints

| HTTP Method | Endpoint | Purpose |
|-------------|----------|---------|
| POST | `/annual` | Create annual prediction |
| POST | `/quarterly` | Create quarterly prediction |
| GET | `/annual` | List annual predictions |
| GET | `/quarterly` | List quarterly predictions |
| PUT | `/annual/{prediction_id}` | Update annual prediction |
| PUT | `/quarterly/{prediction_id}` | Update quarterly prediction |
| DELETE | `/annual/{prediction_id}` | Delete annual prediction |
| DELETE | `/quarterly/{prediction_id}` | Delete quarterly prediction |

## Annual Predictions

Annual predictions assess long-term financial health using 5 key financial ratios.

### Required Financial Ratios

| Ratio Name | Description | Format | Example |
|------------|-------------|---------|---------|
| **Long-term Debt to Total Capital** | Leverage measure | Percentage (0-100) | 25.5 |
| **Total Debt to EBITDA** | Debt servicing ability | Ratio (≥0) | 2.3 |
| **Net Income Margin** | Profitability efficiency | Percentage (-100 to 100) | 8.2 |
| **EBIT to Interest Expense** | Interest coverage | Ratio (≥0) | 12.5 |
| **Return on Assets** | Asset efficiency | Percentage (-100 to 100) | 6.8 |

### 1. Create Annual Prediction

**Endpoint**: `POST /api/v1/predictions/annual`

Creates a new annual financial risk prediction with company data and financial ratios.

**Request Body**:
```json
{
  "company_symbol": "AAPL",
  "company_name": "Apple Inc.",
  "market_cap": 3000000.0,
  "sector": "Technology",
  "reporting_year": "2024",
  "reporting_quarter": "Q3",
  "long_term_debt_to_total_capital": 25.5,
  "total_debt_to_ebitda": 2.3,
  "net_income_margin": 8.2,
  "ebit_to_interest_expense": 12.5,
  "return_on_assets": 6.8
}
```

**Response Example**:
```json
{
  "success": true,
  "message": "Annual prediction created for AAPL",
  "prediction": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "company_id": "123e4567-e89b-12d3-a456-426614174000",
    "company_symbol": "AAPL",
    "company_name": "Apple Inc.",
    "sector": "Technology",
    "market_cap": 3000000.0,
    "reporting_year": "2024",
    "reporting_quarter": "Q3",
    
    "long_term_debt_to_total_capital": 25.5,
    "total_debt_to_ebitda": 2.3,
    "net_income_margin": 8.2,
    "ebit_to_interest_expense": 12.5,
    "return_on_assets": 6.8,
    
    "probability": 0.15,
    "risk_level": "Low Risk",
    "confidence": 0.89,
    
    "access_level": "personal",
    "organization_id": null,
    "organization_name": null,
    "created_by": "user123",
    "created_by_email": "user@example.com",
    "created_at": "2024-10-05T16:30:00Z"
  }
}
```

### 2. Update Annual Prediction

**Endpoint**: `PUT /api/v1/predictions/annual/{prediction_id}`

Updates an existing annual prediction. Users can only update predictions they created.

**Request Body**: Same format as create endpoint
**Response**: Updated prediction object with new ML results

### 3. Delete Annual Prediction

**Endpoint**: `DELETE /api/v1/predictions/annual/{prediction_id}`

Deletes an annual prediction. Users can only delete predictions they created.

## Quarterly Predictions

Quarterly predictions provide short-term financial risk assessment using 4 key ratios and an ensemble ML model.

### Required Financial Ratios

| Ratio Name | Description | Format | Example |
|------------|-------------|---------|---------|
| **Total Debt to EBITDA** | Debt servicing capacity | Ratio (≥0) | 2.8 |
| **SG&A Margin** | Operational efficiency | Percentage (-100 to 100) | 15.3 |
| **Long-term Debt to Total Capital** | Capital structure | Percentage (0-100) | 28.7 |
| **Return on Capital** | Capital efficiency | Percentage (-100 to 100) | 12.4 |

### 1. Create Quarterly Prediction

**Endpoint**: `POST /api/v1/predictions/quarterly`

Creates a new quarterly financial risk prediction using ensemble ML models.

**Request Body**:
```json
{
  "company_symbol": "MSFT",
  "company_name": "Microsoft Corporation",
  "market_cap": 2800000.0,
  "sector": "Technology",
  "reporting_year": "2024",
  "reporting_quarter": "Q2",
  "total_debt_to_ebitda": 2.8,
  "sga_margin": 15.3,
  "long_term_debt_to_total_capital": 28.7,
  "return_on_capital": 12.4
}
```

**Response Example**:
```json
{
  "success": true,
  "message": "Quarterly prediction created for MSFT",
  "prediction": {
    "id": "440e8400-e29b-41d4-a716-446655440001",
    "company_id": "223e4567-e89b-12d3-a456-426614174001",
    "company_symbol": "MSFT",
    "company_name": "Microsoft Corporation",
    "sector": "Technology",
    "market_cap": 2800000.0,
    "reporting_year": "2024",
    "reporting_quarter": "Q2",
    
    "total_debt_to_ebitda": 2.8,
    "sga_margin": 15.3,
    "long_term_debt_to_total_capital": 28.7,
    "return_on_capital": 12.4,
    
    "logistic_probability": 0.18,
    "gbm_probability": 0.22,
    "ensemble_probability": 0.20,
    "risk_level": "Low Risk",
    "confidence": 0.85,
    
    "access_level": "organization",
    "organization_id": "org123",
    "organization_name": "Tech Corp",
    "created_by": "user456",
    "created_by_email": "analyst@techcorp.com",
    "created_at": "2024-10-05T16:45:00Z"
  }
}
```

### 2. Update Quarterly Prediction

**Endpoint**: `PUT /api/v1/predictions/quarterly/{prediction_id}`

Updates an existing quarterly prediction. Users can only update predictions they created.

### 3. Delete Quarterly Prediction

**Endpoint**: `DELETE /api/v1/predictions/quarterly/{prediction_id}`

Deletes a quarterly prediction. Users can only delete predictions they created.

## List Predictions

### Get Annual Predictions

**Endpoint**: `GET /api/v1/predictions/annual`

Retrieves paginated list of annual predictions (personal + organization data, excludes system data).

**Query Parameters**:
- `page` (integer): Page number (default: 1)
- `size` (integer): Items per page (default: 10)  
- `company_symbol` (string): Filter by company symbol
- `reporting_year` (string): Filter by reporting year

**Response Example**:
```json
{
  "success": true,
  "predictions": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "company_symbol": "AAPL",
      "company_name": "Apple Inc.",
      "probability": 0.15,
      "risk_level": "Low Risk",
      "created_at": "2024-10-05T16:30:00Z"
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

### Get Quarterly Predictions

**Endpoint**: `GET /api/v1/predictions/quarterly`

Similar to annual predictions with additional `reporting_quarter` filter.

### Get System Predictions

**Endpoints**: 
- `GET /api/v1/predictions/annual/system`
- `GET /api/v1/predictions/quarterly/system`

Retrieves system-level predictions (accessible to all authenticated users).

## Risk Assessment

### Risk Levels

The ML models classify financial risk into these categories:

| Risk Level | Probability Range | Meaning |
|------------|------------------|---------|
| **Low Risk** | 0.0 - 0.3 | Strong financial health, low default probability |
| **Medium Risk** | 0.3 - 0.7 | Moderate financial concerns, requires monitoring |
| **High Risk** | 0.7 - 1.0 | Significant financial stress, high default probability |

### Model Outputs

**Annual Model**:
- Single probability score (0-1)
- Risk level classification
- Confidence score (0-1)

**Quarterly Ensemble Model**:
- Logistic regression probability
- LightGBM probability  
- Ensemble (weighted) probability
- Risk level classification
- Confidence score (0-1)

## Access Control

### Multi-Tenant Architecture

AccuNode uses a 3-level access control system:

1. **Personal**: User's own predictions
2. **Organization**: Shared within user's organization  
3. **System**: Global predictions (admin-created)

### Permission Rules

- **Users** can create/edit/delete their own predictions
- **Organization members** can view org predictions
- **Super admins** can edit any prediction
- System predictions are read-only for non-admins

### Role Hierarchy

| Role | Permissions |
|------|-------------|
| `user` | Personal predictions only |
| `org_member` | Personal + view organization |  
| `org_admin` | Personal + full organization access |
| `tenant_admin` | Cross-organization access |
| `super_admin` | Full system access |

## Bulk Upload

### Async Bulk Upload

For processing large datasets, AccuNode provides asynchronous bulk upload endpoints using Celery workers.

**Endpoints**:
- `POST /api/v1/predictions/annual/bulk-upload-async`
- `POST /api/v1/predictions/quarterly/bulk-upload-async`

**Request**: Multipart form data with CSV/Excel file
**Response**: Job tracking information

**Example Response**:
```json
{
  "success": true,
  "message": "Bulk upload job started successfully using Celery workers",
  "job_id": "job-123e4567-e89b-12d3-a456-426614174000",
  "task_id": "celery-task-456",
  "total_rows": 1000,
  "estimated_time_minutes": 5,
  "queue_priority": "normal",
  "current_system_load": "moderate"
}
```

### Job Management

**Check Job Status**: `GET /api/v1/predictions/jobs/{job_id}/status`
**List Jobs**: `GET /api/v1/predictions/jobs`
**Get Job Results**: `POST /api/v1/predictions/jobs/{job_id}/results`
**Cancel Job**: `POST /api/v1/predictions/jobs/{job_id}/cancel`
**Delete Job**: `DELETE /api/v1/predictions/jobs/{job_id}`

### CSV Format Requirements

**Annual Predictions CSV Columns**:
```
company_symbol,company_name,market_cap,sector,reporting_year,long_term_debt_to_total_capital,total_debt_to_ebitda,net_income_margin,ebit_to_interest_expense,return_on_assets
```

**Quarterly Predictions CSV Columns**:
```
company_symbol,company_name,market_cap,sector,reporting_year,reporting_quarter,total_debt_to_ebitda,sga_margin,long_term_debt_to_total_capital,return_on_capital
```

## Error Handling

### HTTP Status Codes

| Status | Meaning | Common Causes |
|--------|---------|---------------|
| `200` | Success | Request processed successfully |
| `400` | Bad Request | Invalid input data, missing required fields |
| `401` | Unauthorized | Missing or invalid JWT token |
| `403` | Forbidden | Insufficient permissions, not prediction owner |
| `404` | Not Found | Prediction or company not found |
| `422` | Validation Error | Invalid financial ratio values |
| `429` | Rate Limited | Too many requests |
| `500` | Server Error | Internal ML model or database error |

### Error Response Format

```json
{
  "detail": "You can only update predictions that you created"
}
```

### Validation Errors (422)

```json
{
  "detail": [
    {
      "loc": ["body", "market_cap"],
      "msg": "ensure this value is greater than 0",
      "type": "value_error.number.not_gt"
    }
  ]
}
```

## Rate Limiting

### Endpoint Categories

| Category | Rate Limit | Endpoints |
|----------|------------|-----------|
| **ML Predictions** | 10/min per user | POST/PUT prediction endpoints |
| **Data Read** | 100/min per user | GET prediction lists |
| **Bulk Upload** | 5/min per user | Bulk upload endpoints |
| **Analytics** | 30/min per user | Statistics, dashboard endpoints |

### Rate Limit Headers

```http
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 8  
X-RateLimit-Reset: 1609459200
```

## Example Usage

### Python SDK Example

```python
import requests

class AccuNodeAPI:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {'Authorization': f'Bearer {token}'}
    
    def create_annual_prediction(self, data):
        response = requests.post(
            f"{self.base_url}/api/v1/predictions/annual",
            headers=self.headers,
            json=data
        )
        return response.json()

# Usage
api = AccuNodeAPI('http://localhost:8000', 'your_jwt_token')

prediction_data = {
    "company_symbol": "AAPL",
    "company_name": "Apple Inc.",
    "market_cap": 3000000.0,
    "sector": "Technology", 
    "reporting_year": "2024",
    "long_term_debt_to_total_capital": 25.5,
    "total_debt_to_ebitda": 2.3,
    "net_income_margin": 8.2,
    "ebit_to_interest_expense": 12.5,
    "return_on_assets": 6.8
}

result = api.create_annual_prediction(prediction_data)
print(f"Risk Level: {result['prediction']['risk_level']}")
```
|------|-------------------|---------------------|
| **user** | ❌ No | ❌ No |
| **org_member** | ✅ Yes | ✅ Yes |
| **org_admin** | ✅ Yes | ✅ Yes |
| **tenant_admin** | ✅ Yes | ✅ Yes |
| **super_admin** | ✅ Yes | ✅ Yes |

### Ratio Validation Rules

**All ratios must be**:
- ✅ Numeric values (decimals allowed)
- ✅ Non-null (required fields)
- ✅ Within reasonable business ranges

**Specific validations**:
- **Current Ratio**: Must be > 0 (typically 0.5 - 10.0)
- **Quick Ratio**: Must be > 0 (typically 0.3 - 8.0)  
- **Debt to Equity**: Must be ≥ 0 (typically 0.0 - 5.0)
- **Return on Assets**: Can be negative (typically -1.0 to 1.0)
- **Profit Margin**: Can be negative (typically -1.0 to 1.0)
- **Return on Equity**: Can be negative (typically -2.0 to 2.0)
- **Asset Turnover**: Must be > 0 (typically 0.1 - 5.0)

## Model Information

The ML Predictions API provides state-of-the-art financial risk assessment powered by machine learning models trained on real financial data.

### Annual Model
- **Algorithm**: Logistic Regression with preprocessing
- **Features**: 5 financial ratios (long_term_debt_to_total_capital, total_debt_to_ebitda, net_income_margin, ebit_to_interest_expense, return_on_assets)
- **Output**: Risk level prediction with probability scores

### Quarterly Model
- **Algorithm**: Ensemble (Logistic Regression + LightGBM)
- **Features**: 4 financial ratios (total_debt_to_ebitda, sga_margin, long_term_debt_to_total_capital, return_on_capital)
- **Output**: Default probability with confidence metrics
