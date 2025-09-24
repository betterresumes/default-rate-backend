# System-Level Predictions API Documentation

## Overview

Two new API endpoints have been added to provide access to system-level predictions data. These endpoints are designed to be accessible by **all user roles** and return only predictions with `access_level = "system"`.

## New Endpoints

### 1. Get System Annual Predictions
**Endpoint:** `GET /api/v1/predictions/annual/system`

**Description:** Retrieves paginated system-level annual predictions that are accessible to all authenticated users.

### 2. Get System Quarterly Predictions  
**Endpoint:** `GET /api/v1/predictions/quarterly/system`

**Description:** Retrieves paginated system-level quarterly predictions that are accessible to all authenticated users.

---

## API Specifications

### Authentication
- **Required:** Yes (Bearer token)
- **Roles Allowed:** All roles (`user`, `org_member`, `org_admin`, `tenant_admin`, `super_admin`)
- **Permission Level:** Minimum "user" role required

### Query Parameters

#### Common Parameters (Both Endpoints)
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `page` | integer | No | 1 | Page number for pagination |
| `size` | integer | No | 10 | Number of items per page |
| `company_symbol` | string | No | null | Filter by company symbol (partial match) |
| `reporting_year` | string | No | null | Filter by specific reporting year |
| `sector` | string | No | null | Filter by company sector (partial match) |
| `risk_level` | string | No | null | Filter by risk level (LOW, MEDIUM, HIGH, CRITICAL) |

#### Quarterly-Specific Parameters
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `reporting_quarter` | string | No | null | Filter by quarter (Q1, Q2, Q3, Q4) |

---

## Response Format

### Success Response Structure
```json
{
  "success": true,
  "message": "System-level [annual/quarterly] predictions retrieved successfully",
  "predictions": [
    {
      "id": "uuid-string",
      "company_id": "uuid-string",
      "company_symbol": "AAPL",
      "company_name": "Apple Inc.",
      "sector": "Technology",
      "market_cap": 2500000000000.00,
      "reporting_year": "2024",
      "reporting_quarter": "Q4",
      
      // Financial Input Data
      "long_term_debt_to_total_capital": 0.25,
      "total_debt_to_ebitda": 2.1,
      "net_income_margin": 0.15,
      "ebit_to_interest_expense": 12.5,
      "return_on_assets": 0.08,
      
      // ML Prediction Results
      "probability": 0.0234,
      "risk_level": "LOW",
      "confidence": 0.85,
      
      // System Metadata
      "access_level": "system",
      "created_by": "uuid-string",
      "created_by_email": "super_admin@company.com",
      "created_at": "2024-03-15T10:30:00Z",
      "predicted_at": "2024-03-15T10:30:05Z"
    }
  ],
  "pagination": {
    "total": 150,
    "page": 1,
    "size": 10,
    "pages": 15
  },
  "filters": {
    "access_level": "system",
    "company_symbol": null,
    "reporting_year": null,
    "sector": null,
    "risk_level": null
  }
}
```

### Annual Predictions Response Fields
| Field | Type | Description |
|-------|------|-------------|
| `long_term_debt_to_total_capital` | float | Long-term debt / total capital (%) |
| `total_debt_to_ebitda` | float | Total debt / EBITDA ratio |
| `net_income_margin` | float | Net income margin (%) |
| `ebit_to_interest_expense` | float | EBIT / interest expense ratio |
| `return_on_assets` | float | Return on assets (%) |
| `probability` | float | ML predicted default probability |

### Quarterly Predictions Response Fields
| Field | Type | Description |
|-------|------|-------------|
| `total_debt_to_ebitda` | float | Total debt / EBITDA ratio |
| `sga_margin` | float | SG&A margin (%) |
| `long_term_debt_to_total_capital` | float | Long-term debt / total capital (%) |
| `return_on_capital` | float | Return on capital (%) |
| `logistic_probability` | float | Logistic model probability |
| `gbm_probability` | float | Gradient Boosting Model probability |
| `ensemble_probability` | float | Combined model probability |

---

## Example Usage

### cURL Examples

#### Get System Annual Predictions
```bash
curl -X GET "http://localhost:8000/api/v1/predictions/annual/system?page=1&size=5&sector=Technology" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### Get System Quarterly Predictions with Filters
```bash
curl -X GET "http://localhost:8000/api/v1/predictions/quarterly/system?page=1&size=10&reporting_year=2024&risk_level=HIGH" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Python Example
```python
import requests

headers = {
    'Authorization': 'Bearer YOUR_JWT_TOKEN'
}

# Get system annual predictions
response = requests.get(
    'http://localhost:8000/api/v1/predictions/annual/system',
    headers=headers,
    params={
        'page': 1,
        'size': 20,
        'company_symbol': 'AAPL',
        'reporting_year': '2024'
    }
)

data = response.json()
predictions = data['predictions']
pagination = data['pagination']
```

### JavaScript Example
```javascript
const token = 'YOUR_JWT_TOKEN';

const fetchSystemPredictions = async (type = 'annual', filters = {}) => {
  const queryParams = new URLSearchParams({
    page: 1,
    size: 10,
    ...filters
  });
  
  const response = await fetch(
    `http://localhost:8000/api/v1/predictions/${type}/system?${queryParams}`,
    {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  
  return await response.json();
};

// Usage
const annualData = await fetchSystemPredictions('annual', {
  sector: 'Technology',
  risk_level: 'HIGH'
});

const quarterlyData = await fetchSystemPredictions('quarterly', {
  reporting_year: '2024',
  reporting_quarter: 'Q4'
});
```

---

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Authentication required to view system predictions"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Error fetching system annual predictions: [error message]"
}
```

---

## Key Features

### 🔓 **Universal Access**
- Available to all authenticated user roles
- No organization or role-based filtering
- Same data visible to everyone

### 📊 **System-Level Data Only**  
- Only returns predictions with `access_level = "system"`
- Typically created by super_admin users
- Represents reference/benchmark data

### 🔍 **Rich Filtering**
- Filter by company symbol, sector, year, quarter
- Risk level filtering (LOW, MEDIUM, HIGH, CRITICAL)
- Partial string matching for company names and sectors

### 📄 **Comprehensive Pagination**
- Standard pagination with page, size, total, pages
- Efficient database queries with proper indexing
- Ordered by creation date (newest first)

### 📈 **Complete Prediction Data**
- All financial input ratios
- ML model results and confidence scores
- Metadata about prediction creation

---

## Use Cases

### 🎯 **Benchmarking**
Organizations can compare their predictions against system-wide reference data to understand market trends.

### 📊 **Market Research**  
Access to broader market prediction data for research and analysis purposes.

### 📈 **Public Dashboards**
Display system-wide statistics and trends that don't contain sensitive organizational data.

### 🔍 **Reference Data**
Common industry predictions that serve as baselines for comparison across all users.

---

## Implementation Notes

- **Database Performance**: Uses proper JOIN queries with indexing on `access_level` field
- **Security**: Maintains authentication requirements while allowing cross-organizational access
- **Data Consistency**: Returns same format as regular prediction endpoints for easy integration
- **Scalability**: Implements pagination to handle large datasets efficiently

---

## Testing

These endpoints can be tested using:
1. Postman collection (import the existing collection and add these endpoints)
2. cURL commands as shown above  
3. Frontend integration for dashboard displays
4. API testing tools like Insomnia or Bruno

The endpoints follow the same patterns as existing prediction APIs, making integration straightforward for existing client applications.
