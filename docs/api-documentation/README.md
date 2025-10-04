# API Documentation

Welcome to the AccuNode API documentation. This section provides comprehensive information about all available endpoints, authentication methods, and integration guidelines.

## 📚 API Documentation Structure

### Core API References
- **[Authentication API](./authentication-api.md)** - User registration, login, and token management
- **[Companies API](./companies-api.md)** - Company management and organization access
- **[Predictions API](./predictions-api.md)** - ML-powered financial risk predictions (annual + quarterly + bulk)
- **[Users API](./users-api.md)** - User management and profile administration
- **[Organizations API](./organizations-api.md)** - Organization CRUD, whitelists, join tokens, global access toggle
- **[Tenants API](./tenants-api.md)** - Tenant CRUD and statistics
- **[Scaling API](./scaling-api.md)** - Auto-scaling status, metrics, recommendations and controls
- **[Rate Limits](./rate-limits.md)** - Request throttling policies and limits
- **[Error Handling](./error-handling.md)** - Error formats and common responses
- **[Health Endpoint](./health-endpoints.md)** - System health and readiness

---

## ML Prediction Models

AccuNode provides two types of financial risk predictions:

### Annual Predictions
- Model: Logistic Regression with preprocessing
- Ratios: 5 (long_term_debt_to_total_capital, total_debt_to_ebitda, net_income_margin, ebit_to_interest_expense, return_on_assets)
- Output: Risk level + probability + confidence

### Quarterly Predictions
- Model: Ensemble (Logistic Regression + LightGBM)
- Ratios: 4 (total_debt_to_ebitda, sga_margin, long_term_debt_to_total_capital, return_on_capital)
- Output: Ensemble/logistic/gbm probabilities + risk level + confidence

---

## Organization-Based Access

Access control is organization-scoped. See the primer: `../core-application/access-model.md`.
- Read filters respect personal/organization/system scopes
- Updates to predictions are owner-only (creator can edit)
- Global visibility can be toggled per organization via global-data-access endpoints

---

## Development & Testing

- Local API: `http://localhost:8000`
- Interactive Docs: `http://localhost:8000/docs` (Swagger) and `/redoc`

Quick testing commands
```bash
# Health check
curl http://localhost:8000/health

# Open interactive documentation (macOS)
open http://localhost:8000/docs
```

---

## Integration Examples (curl)

```bash
# Auth: login
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"pass"}' \
  http://localhost:8000/api/v1/auth/login

# List companies
TOKEN="<jwt>"
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/companies

# Create annual prediction
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"company_id":"<uuid>","reporting_year":"2024","long_term_debt_to_total_capital":0.12,"total_debt_to_ebitda":2.1,"net_income_margin":0.08,"ebit_to_interest_expense":3.2,"return_on_assets":0.05}' \
  http://localhost:8000/api/v1/predictions/annual
```

---

## Authentication System

AccuNode uses JWT for secure API access.
- Include: `Authorization: Bearer <token>` header
- Default expiry: 60 minutes

Role-Based Access Control

| Role | Level | Can Access |
|------|-------|------------|
| user | 1 | Basic profile only |
| org_member | 2 | Companies, predictions (org scope) |
| org_admin | 3 | + User/whitelist in org |
| tenant_admin | 4 | + Tenant orgs/users |
| super_admin | 5 | Full system access |

---

## API Overview

Base URLs
```
Production:  https://api.accunode.com/api/v1
Staging:     https://staging-api.accunode.com/api/v1 (if configured)
Local:       http://localhost:8000/api/v1
```

Core routes (high-level)
- Auth: `/auth/*`
- Companies: `/companies/*`
- Predictions: `/predictions/*` (annual, quarterly, bulk)
- Users: `/users/*`
- Organizations: `/organizations/*`
- Tenants: `/tenants/*`
- Scaling: `/scaling/*`
- Health: `/health`

---

Last Updated: October 5, 2025
