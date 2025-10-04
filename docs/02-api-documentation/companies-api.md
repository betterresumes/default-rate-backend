# Companies API

This document explains how to manage companies using AccuNode's API. Companies are the core entities for financial risk predictions.

## Companies Overview

In AccuNode, **companies** are the businesses you want to analyze for financial risk. Each company belongs to an **organization** and can have predictions for both annual and quarterly periods.

### Key Concepts
- **Company**: A business entity with financial data
- **Organization Access**: Only your organization members can see your companies
- **Predictions**: Annual (5 ratios) and Quarterly (4 ratios) risk scores
- **Risk Scoring**: 1-10 scale (1 = lowest risk, 10 = highest risk)

## Base Information

- **Base URL**: `/api/v1/companies`
- **Authentication**: Bearer token required
- **Access Control**: Organization-based (you only see companies in your organization)

| Endpoint | Purpose | Access Level |
|----------|---------|--------------|
| GET /companies | List your companies | org_member+ |
| POST /companies | Create new company | org_member+ |
| GET /companies/{id} | Get company details | org_member+ |
| PUT /companies/{id} | Update company | org_member+ |

## API Endpoints

### 1. List All Companies 📋

**Endpoint**: `GET /api/v1/companies`

**What it does**: Returns all companies in your organization with their latest prediction summaries

**Authentication**: Required (Bearer token)

**Query Parameters**:
| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `skip` | Integer | How many to skip (for pagination) | `0` |
| `limit` | Integer | How many to return (max 100) | `20` |

**Request Example**:
```bash
GET /api/v1/companies?skip=0&limit=20
Authorization: Bearer your_jwt_token
```

**Response Example**:
```json
{
  "companies": [
    {
      "id": "comp-abc123...",
      "name": "Tech Solutions Inc",
      "email": "info@techsolutions.com",
      "phone": "+1-555-0123",
      "address": "123 Business St, NY 10001",
      "organization_id": "org-456def...",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-10-05T14:22:00Z",
      "latest_annual_prediction": {
        "risk_score": 3.2,
        "prediction_date": "2024-10-01",
        "status": "low_risk"
      },
      "latest_quarterly_prediction": {
        "risk_score": 4.1,
        "prediction_date": "2024-10-01", 
        "status": "moderate_risk"
      }
    },
    {
      "id": "comp-def456...",
      "name": "Global Manufacturing Corp",
      "email": "contact@globalmfg.com",
      "phone": "+1-555-0456",
      "address": "456 Industry Blvd, CA 90210",
      "organization_id": "org-456def...",
      "created_at": "2024-02-20T09:15:00Z",
      "updated_at": "2024-09-28T11:45:00Z",
      "latest_annual_prediction": null,
      "latest_quarterly_prediction": null
    }
  ],
  "total": 2,
  "skip": 0,
  "limit": 20
}
```

**Risk Status Meanings**:
- **low_risk**: Score 1-3 (Green)
- **moderate_risk**: Score 4-6 (Yellow)  
- **high_risk**: Score 7-10 (Red)

### 2. Create New Company ➕

**Endpoint**: `POST /api/v1/companies`

**What it does**: Creates a new company in your organization

**Authentication**: Required (Bearer token)

**Request Example**:
```json
{
  "name": "Innovative Startups LLC",
  "email": "hello@innovativestartups.com",
  "phone": "+1-555-0789",
  "address": "789 Startup Ave, Austin TX 78701"
}
```

**Response Example**:
```json
{
  "id": "comp-ghi789...",
  "name": "Innovative Startups LLC",
  "email": "hello@innovativestartups.com", 
  "phone": "+1-555-0789",
  "address": "789 Startup Ave, Austin TX 78701",
  "organization_id": "org-456def...",
  "created_at": "2024-10-05T16:30:00Z",
  "updated_at": "2024-10-05T16:30:00Z"
}
```

**Validation Rules**:
- **name**: Required, 1-200 characters, must be unique in your organization
- **email**: Optional but if provided, must be valid format
- **phone**: Optional, any format accepted
- **address**: Optional, up to 500 characters

### 3. Get Company Details 🔍

**Endpoint**: `GET /api/v1/companies/{company_id}`

**What it does**: Returns detailed information for a specific company, including all predictions

**Authentication**: Required (Bearer token)

**Request Example**:
```bash
GET /api/v1/companies/comp-abc123...
Authorization: Bearer your_jwt_token
```

**Response Example**:
```json
{
  "id": "comp-abc123...",
  "name": "Tech Solutions Inc",
  "email": "info@techsolutions.com",
  "phone": "+1-555-0123", 
  "address": "123 Business St, NY 10001",
  "organization_id": "org-456def...",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-10-05T14:22:00Z",
  "annual_predictions": [
    {
      "id": "pred-annual-123...",
      "risk_score": 3.2,
      "prediction_date": "2024-10-01",
      "ratios": {
        "current_ratio": 2.1,
        "quick_ratio": 1.8,
        "debt_to_equity": 0.45,
        "return_on_assets": 0.12,
        "profit_margin": 0.08
      },
      "status": "low_risk",
      "created_at": "2024-10-01T09:00:00Z"
    }
  ],
  "quarterly_predictions": [
    {
      "id": "pred-quarterly-456...",
      "risk_score": 4.1, 
      "prediction_date": "2024-10-01",
      "ratios": {
        "debt_to_equity": 0.52,
        "current_ratio": 1.9,
        "return_on_equity": 0.15,
        "asset_turnover": 1.2
      },
      "status": "moderate_risk",
      "created_at": "2024-10-01T09:15:00Z"
    }
  ]
}
```

### 4. Update Company Information ✏️

**Endpoint**: `PUT /api/v1/companies/{company_id}`

**What it does**: Updates company information (name, contact details, etc.)

**Authentication**: Required (Bearer token)

**Request Example**:
```json
{
  "name": "Tech Solutions Inc (Updated)",
  "email": "newemail@techsolutions.com",
  "phone": "+1-555-9999",
  "address": "456 New Address St, NY 10002"
}
```

**Response Example**:
```json
{
  "id": "comp-abc123...",
  "name": "Tech Solutions Inc (Updated)",
  "email": "newemail@techsolutions.com", 
  "phone": "+1-555-9999",
  "address": "456 New Address St, NY 10002",
  "organization_id": "org-456def...",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-10-05T16:45:00Z"
}
```

**Update Rules**:
- All fields are optional in updates
- Only provide fields you want to change
- Name must still be unique in your organization
- Cannot change `organization_id` or system timestamps

## Access Control

### Organization-Based Access
AccuNode uses organization-based access control for companies:

```
Your Organization → Your Companies Only
├── You can see: All companies in your organization  
├── You can create: New companies (automatically assigned to your org)
├── You can update: Any company in your organization
└── You cannot see: Companies from other organizations
```

### Role Requirements
| Role | Can List | Can Create | Can View Details | Can Update |
|------|----------|------------|------------------|------------|
| **user** | ❌ No | ❌ No | ❌ No | ❌ No |
| **org_member** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **org_admin** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **tenant_admin** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **super_admin** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |

**Note**: Basic "user" role cannot access companies API. You need at least "org_member" role.

## Common Error Messages

| Error Code | Error Message | What It Means | What To Do |
|------------|---------------|---------------|------------|
| **401** | "Not authenticated" | Missing or invalid token | Include valid Bearer token |
| **403** | "User does not have organization access" | Your role is too low | Contact admin to upgrade role |
| **404** | "Company not found" | Company doesn't exist or not in your org | Check company ID and organization |
| **400** | "Company name already exists in organization" | Name is taken | Use different name |
| **422** | "Invalid email format" | Email format is wrong | Use valid email format |
| **422** | "Name is required and cannot be empty" | Missing company name | Provide company name |

## Integration Examples

### Using with JavaScript
```javascript
class CompaniesAPI {
  constructor(baseUrl, token) {
    this.baseUrl = baseUrl;
    this.token = token;
  }

  async listCompanies(skip = 0, limit = 20) {
    const response = await fetch(
      `${this.baseUrl}/api/v1/companies?skip=${skip}&limit=${limit}`,
      {
        headers: {
          'Authorization': `Bearer ${this.token}`,
          'Content-Type': 'application/json'
        }
      }
    );
    return response.json();
  }

  async createCompany(companyData) {
    const response = await fetch(`${this.baseUrl}/api/v1/companies`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(companyData)
    });
    return response.json();
  }

  async getCompany(companyId) {
    const response = await fetch(
      `${this.baseUrl}/api/v1/companies/${companyId}`,
      {
        headers: {
          'Authorization': `Bearer ${this.token}`,
          'Content-Type': 'application/json'
        }
      }
    );
    return response.json();
  }

  async updateCompany(companyId, updates) {
    const response = await fetch(
      `${this.baseUrl}/api/v1/companies/${companyId}`,
      {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${this.token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(updates)
      }
    );
    return response.json();
  }
}

// Usage example
const api = new CompaniesAPI('http://localhost:8000', 'your_jwt_token');

// List companies
const companies = await api.listCompanies(0, 10);
console.log(`Found ${companies.total} companies`);

// Create new company
const newCompany = await api.createCompany({
  name: 'My New Company',
  email: 'contact@mynewcompany.com',
  phone: '+1-555-1234'
});
```

### Using with Python
```python
import requests

class AccuNodeCompanies:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def list_companies(self, skip=0, limit=20):
        response = requests.get(
            f"{self.base_url}/api/v1/companies",
            headers=self.headers,
            params={'skip': skip, 'limit': limit}
        )
        return response.json()
    
    def create_company(self, name, email=None, phone=None, address=None):
        data = {'name': name}
        if email: data['email'] = email
        if phone: data['phone'] = phone  
        if address: data['address'] = address
        
        response = requests.post(
            f"{self.base_url}/api/v1/companies",
            headers=self.headers,
            json=data
        )
        return response.json()
    
    def get_company(self, company_id):
        response = requests.get(
            f"{self.base_url}/api/v1/companies/{company_id}",
            headers=self.headers
        )
        return response.json()
    
    def update_company(self, company_id, **updates):
        response = requests.put(
            f"{self.base_url}/api/v1/companies/{company_id}",
            headers=self.headers,
            json=updates
        )
        return response.json()

# Usage example
companies_api = AccuNodeCompanies('http://localhost:8000', 'your_jwt_token')

# List all companies
result = companies_api.list_companies()
print(f"Total companies: {result['total']}")

# Create new company
new_company = companies_api.create_company(
    name="Python Test Company",
    email="test@python.com"
)
print(f"Created company: {new_company['id']}")

# Get company details
details = companies_api.get_company(new_company['id'])
print(f"Company details: {details['name']}")
```

## Testing

### Test with curl
```bash
# List companies
curl -X GET http://localhost:8000/api/v1/companies \
  -H "Authorization: Bearer YOUR_TOKEN"

# Create company
curl -X POST http://localhost:8000/api/v1/companies \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Company","email":"test@example.com"}'

# Get company details  
curl -X GET http://localhost:8000/api/v1/companies/COMPANY_ID \
  -H "Authorization: Bearer YOUR_TOKEN"

# Update company
curl -X PUT http://localhost:8000/api/v1/companies/COMPANY_ID \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Updated Company Name"}'
```

The Companies API provides full CRUD operations for managing your business entities with organization-level access control and integrated prediction tracking.
