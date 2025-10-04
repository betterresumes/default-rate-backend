# API Documentation

Welcome to the AccuNode API documentation. This section provides comprehensive information about all available endpoints, authentication methods, and integration guidelines.

## 📚 API Documentation Structure

### Core API References
- **[Authentication API](./authentication-api.md)** - User registration, login, and token management
- **[Companies API](./companies-api.md)** - Company management and organization access
- **[Predictions API](./predictions-api.md)** - ML-powered financial risk predictions
- **[Users API](./users-api.md)** - User management and profile administration

---

## � ML Prediction Models

AccuNode provides two types of financial risk predictions:

### Annual Predictions 📅
- **Model**: Logistic Regression with binned scoring
- **Ratios**: 5 financial ratios (current, quick, debt-to-equity, ROA, profit margin)
- **Purpose**: Long-term risk assessment
- **Accuracy**: 85%+ on validation data

### Quarterly Predictions 📈
- **Model**: Ensemble (Logistic Regression + LightGBM)
- **Ratios**: 4 financial ratios (debt-to-equity, current, ROE, asset turnover)  
- **Purpose**: Short-term risk assessment
- **Accuracy**: 82%+ on validation data

### Risk Scoring
- **Scale**: 1-10 (1 = lowest risk, 10 = highest risk)
- **Categories**: Low Risk (1-3), Moderate Risk (4-6), High Risk (7-10)

---

## 🏢 Organization-Based Access

AccuNode uses **organization-based access control**:

### How It Works
```
Your Organization
├── Your Companies Only
├── Your Team's Predictions  
└── Organization User Management
```

- **See**: Only companies in your organization
- **Create**: New companies automatically assigned to your org
- **Predict**: Only for companies you can access
- **Manage**: Users within your organization scope

---

## 🧪 Development & Testing

### Development Environment
- **Local API**: `http://localhost:8000`
- **Interactive Docs**: `http://localhost:8000/docs` (Swagger)
- **Alternative Docs**: `http://localhost:8000/redoc`

### Test Data Available
- Sample companies with financial data
- Test users with different roles
- Pre-generated predictions for reference

### Quick Testing Commands
```bash
# Health check
curl http://localhost:8000/health

# API info
curl http://localhost:8000/api/v1/info

# Interactive documentation
open http://localhost:8000/docs
```

---

## 📱 Integration Examples

### JavaScript/React
```javascript
const api = new AccuNodeAPI('http://localhost:8000', token);
const companies = await api.companies.list();
const prediction = await api.predictions.annual(companyId, ratios);
```

### Python
```python
from accunode import AccuNodeAPI
api = AccuNodeAPI('http://localhost:8000', token)
companies = api.companies.list()
prediction = api.predictions.annual(company_id, **ratios)
```

### curl
```bash
# Set token variable
TOKEN="your_jwt_token_here"

# List companies
curl -H "Authorization: Bearer $TOKEN" 
  http://localhost:8000/api/v1/companies
```

---

## 🆘 Getting Help

### Documentation Resources
- **API Reference**: Detailed endpoint documentation in each API file
- **Examples**: Code samples in multiple programming languages
- **Error Codes**: Comprehensive error handling guides

### Development Support
- **Interactive API**: Use `/docs` endpoint for live testing
- **Health Endpoints**: `/health` for system status
- **Debug Mode**: Additional logging in development environment

---

**System**: FastAPI 2.0.0 "Default Rate Backend API"  
**Database**: PostgreSQL with 6 main models  
**Authentication**: JWT with 5-role hierarchy  
**ML Models**: Annual (5 ratios) + Quarterly (4 ratios)  
**Architecture**: Multi-tenant with organization-based access control

---

## � Authentication System

AccuNode uses **JWT (JSON Web Tokens)** for secure API access:

### How It Works
1. **Register/Login** → Receive JWT token
2. **Include Token** → `Authorization: Bearer <token>` header
3. **Token Expires** → After 60 minutes
4. **Renewal** → Login again for new token

### Role-Based Access Control

| Role | Level | Can Access |
|------|-------|------------|
| **user** | 1 | Basic profile only |
| **org_member** | 2 | Companies, predictions |
| **org_admin** | 3 | + User management in org |
| **tenant_admin** | 4 | + Multiple organizations |
| **super_admin** | 5 | + Full system access |

**Important**: You need at least `org_member` role to access companies and predictions!
- Common integration issues

### ⚡ **[RATE_LIMITING.md](./RATE_LIMITING.md)**
- Rate limiting policies and thresholds
- Usage quota management
- Performance optimization tips
- Monitoring and alerts

---

## 🚀 **Quick Start Guide**

### **For API Consumers**
1. **Authentication**: Start with [AUTHENTICATION_API.md](./AUTHENTICATION_API.md)
2. **Core Usage**: Review [PREDICTION_API.md](./PREDICTION_API.md)
3. **Error Handling**: Study [ERROR_HANDLING.md](./ERROR_HANDLING.md)

### **For Integration Developers**
1. **Complete Reference**: Use [API_REFERENCE.md](./API_REFERENCE.md)
2. **Bulk Operations**: Implement [BULK_OPERATIONS_API.md](./BULK_OPERATIONS_API.md)
3. **Rate Limits**: Configure [RATE_LIMITING.md](./RATE_LIMITING.md)

### **For Multi-tenant Applications**
1. **Organizations**: Setup [USER_ORGANIZATION_API.md](./USER_ORGANIZATION_API.md)
2. **User Management**: Implement [AUTHENTICATION_API.md](./AUTHENTICATION_API.md)
3. **Data Access**: Understand [API_REFERENCE.md](./API_REFERENCE.md) access controls

---

## 📊 **API Overview**

### **Base URL**
```
Production:  https://api.accunode.com/api/v1
Staging:     https://staging-api.accunode.com/api/v1
Local:       http://localhost:8000/api/v1
```

### **Authentication**
```http
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
```

### **Core Endpoints Summary**
```
Authentication:
POST   /auth/register          # User registration
POST   /auth/login            # User authentication
POST   /auth/refresh          # Token refresh

Predictions:
GET    /predictions/annual     # List annual predictions
POST   /predictions/annual     # Create annual prediction
GET    /predictions/quarterly  # List quarterly predictions
POST   /predictions/quarterly  # Create quarterly prediction

Companies:
GET    /companies             # List companies
POST   /companies             # Create company
GET    /companies/{id}        # Get company details

Users & Organizations:
GET    /users/profile         # User profile
PUT    /users/profile         # Update profile
GET    /users/organizations   # User organizations

Bulk Operations:
POST   /bulk/upload           # Bulk CSV upload
GET    /bulk/jobs/{id}        # Job status
```

---

**Last Updated**: October 5, 2025
