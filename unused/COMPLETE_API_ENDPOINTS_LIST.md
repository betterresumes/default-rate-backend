# 🏦 Complete API Endpoints List - Financial Default Risk Prediction API v2.0.0

## Base URL: `http://localhost:8000`

## 🔐 **1. USER AUTHENTICATION** (Public/User Access)
**Prefix:** `/api/v1/auth`

| Method | Endpoint | Description | Access Level |
|--------|----------|-------------|--------------|
| POST | `/api/v1/auth/register` | User registration | Public |
| POST | `/api/v1/auth/login` | User login | Public |
| POST | `/api/v1/auth/join` | Join organization via token | User |
| POST | `/api/v1/auth/refresh` | Refresh access token | User |
| POST | `/api/v1/auth/logout` | User logout | User |

## 👨‍💼 **2. ADMIN AUTHENTICATION** (Super Admin Only)
**Prefix:** `/api/v1/auth`

| Method | Endpoint | Description | Access Level |
|--------|----------|-------------|--------------|
| POST | `/api/v1/auth/create-user` | Admin create user | Super Admin |
| POST | `/api/v1/auth/impersonate/{user_id}` | Impersonate user | Super Admin |
| POST | `/api/v1/auth/force-password-reset/{user_id}` | Force password reset | Super Admin |
| GET | `/api/v1/auth/audit/login-history/{user_id}` | View login history | Super Admin |
| POST | `/api/v1/auth/bulk-activate` | Bulk activate users | Super Admin |

## 🎯 **3. TENANT ADMIN MANAGEMENT** (Super Admin Only)
**Prefix:** `/api/v1`

| Method | Endpoint | Description | Access Level |
|--------|----------|-------------|--------------|
| POST | `/api/v1/create-tenant-with-admin` | ⭐ Create tenant + admin atomically | Super Admin |
| POST | `/api/v1/assign-existing-user` | ⭐ Assign existing user as tenant admin | Super Admin |
| POST | `/api/v1/assign-user-to-organization` | ⭐ Assign user to organization | Super Admin |
| GET | `/api/v1/tenant/{tenant_id}/admin-info` | Get tenant admin info | Super Admin |
| DELETE | `/api/v1/remove-tenant-admin/{user_id}` | Remove tenant admin | Super Admin |

## 🏢 **4. TENANT MANAGEMENT** (Super Admin Only)
**Prefix:** `/api/v1/tenants`

| Method | Endpoint | Description | Access Level |
|--------|----------|-------------|--------------|
| POST | `/api/v1/tenants` | Create tenant | Super Admin |
| GET | `/api/v1/tenants` | List all tenants | Super Admin |
| GET | `/api/v1/tenants/{tenant_id}` | Get tenant details | Super Admin |
| PUT | `/api/v1/tenants/{tenant_id}` | Update tenant | Super Admin |
| DELETE | `/api/v1/tenants/{tenant_id}` | Delete tenant | Super Admin |
| GET | `/api/v1/tenants/{tenant_id}/stats` | Get tenant statistics | Super Admin |
| POST | `/api/v1/tenants/{tenant_id}/assign-admin` | Assign tenant admin | Super Admin |
| DELETE | `/api/v1/tenants/{tenant_id}/remove-admin/{user_id}` | Remove tenant admin | Super Admin |
| GET | `/api/v1/tenants/{tenant_id}/admins` | List tenant admins | Super Admin |

## 🏛️ **5. ORGANIZATION MANAGEMENT** (Tenant Admin + Org Admin)
**Prefix:** `/api/v1/organizations`

| Method | Endpoint | Description | Access Level |
|--------|----------|-------------|--------------|
| POST | `/api/v1/organizations` | Create organization | Tenant Admin |
| GET | `/api/v1/organizations/` | List organizations | Tenant Admin + |
| GET | `/api/v1/organizations/{org_id}` | Get organization details | Tenant Admin + |
| PUT | `/api/v1/organizations/{org_id}` | Update organization | Org Admin + |
| DELETE | `/api/v1/organizations/{org_id}` | Delete organization | Tenant Admin |
| POST | `/api/v1/organizations/{org_id}/regenerate-token` | Regenerate join token | Org Admin + |
| GET | `/api/v1/organizations/{org_id}/whitelist` | List whitelist | Org Admin + |
| POST | `/api/v1/organizations/{org_id}/whitelist` | Add to whitelist | Org Admin + |
| DELETE | `/api/v1/organizations/{org_id}/whitelist/{email}` | Remove from whitelist | Org Admin + |
| GET | `/api/v1/organizations/{org_id}/users` | List organization users | Org Admin + |
| GET | `/api/v1/organizations/{org_id}/details` | Get detailed org info | Org Admin + |
| GET | `/api/v1/organizations/{org_id}/admins` | List org admins | Org Admin + |
| PATCH | `/api/v1/organizations/{org_id}/global-data-access` | Toggle global data access | Super Admin |
| GET | `/api/v1/organizations/{org_id}/global-data-access` | Get global access status | Org Admin + |

## 👥 **6. USER MANAGEMENT** (Role-Based Scoped Access)
**Prefix:** `/api/v1/users`

| Method | Endpoint | Description | Access Level |
|--------|----------|-------------|--------------|
| GET | `/api/v1/users/profile` | Get own profile | User |
| PUT | `/api/v1/users/profile` | Update own profile | User |
| GET | `/api/v1/users/me` | Get current user info | User |
| POST | `/api/v1/users` | Create user (admin) | Admin |
| GET | `/api/v1/users` | List users (scoped) | Admin |
| GET | `/api/v1/users/{user_id}` | Get user details | Admin |
| PUT | `/api/v1/users/{user_id}` | Update user | Admin |
| DELETE | `/api/v1/users/{user_id}` | Delete user | Admin |
| PUT | `/api/v1/users/{user_id}/role` | Update user role | Admin |
| POST | `/api/v1/users/{user_id}/activate` | Activate user | Admin |
| POST | `/api/v1/users/{user_id}/deactivate` | Deactivate user | Admin |

## 🏭 **7. COMPANIES** (Org Members+)
**Prefix:** `/api/v1/companies`

| Method | Endpoint | Description | Access Level |
|--------|----------|-------------|--------------|
| GET | `/api/v1/companies/` | List companies (paginated) | Org Member + |
| GET | `/api/v1/companies/{company_id}` | Get company details | Org Member + |
| POST | `/api/v1/companies/` | Create company | Org Member + |
| GET | `/api/v1/companies/search/{symbol}` | Search company by symbol | Org Member + |

## 📊 **8. PREDICTIONS** (Org Members+)
**Prefix:** `/api/v1/predictions`

### Core Prediction APIs
| Method | Endpoint | Description | Access Level |
|--------|----------|-------------|--------------|
| POST | `/api/v1/predictions/annual` | ⭐ Create annual prediction | Org Member + |
| POST | `/api/v1/predictions/quarterly` | ⭐ Create quarterly prediction | Org Member + |
| GET | `/api/v1/predictions/annual` | ⭐ List annual predictions | Org Member + |
| GET | `/api/v1/predictions/quarterly` | ⭐ List quarterly predictions | Org Member + |

### Bulk Operations
| Method | Endpoint | Description | Access Level |
|--------|----------|-------------|--------------|
| POST | `/api/v1/predictions/bulk-upload` | Sync bulk upload | Org Member + |
| POST | `/api/v1/predictions/annual/bulk-upload-async` | Async annual bulk upload | Org Member + |
| POST | `/api/v1/predictions/quarterly/bulk-upload-async` | Async quarterly bulk upload | Org Member + |
| GET | `/api/v1/predictions/jobs/{job_id}/status` | Get bulk job status | Org Member + |
| GET | `/api/v1/predictions/jobs` | List bulk jobs | Org Member + |

### Prediction Management
| Method | Endpoint | Description | Access Level |
|--------|----------|-------------|--------------|
| PUT | `/api/v1/predictions/annual/{prediction_id}` | Update annual prediction | Org Member + |
| DELETE | `/api/v1/predictions/annual/{prediction_id}` | Delete annual prediction | Org Member + |
| PUT | `/api/v1/predictions/quarterly/{prediction_id}` | Update quarterly prediction | Org Member + |
| DELETE | `/api/v1/predictions/quarterly/{prediction_id}` | Delete quarterly prediction | Org Member + |

## 🌐 **9. SYSTEM ENDPOINTS**

| Method | Endpoint | Description | Access Level |
|--------|----------|-------------|--------------|
| GET | `/` | API root information | Public |
| GET | `/health` | Health check | Public |
| GET | `/docs` | OpenAPI documentation | Public |
| GET | `/redoc` | ReDoc documentation | Public |

---

## 🔐 **Role Hierarchy & Access Control**

### Roles (Hierarchy: High → Low)
1. **Super Admin** (4) → Full system access
2. **Tenant Admin** (3) → Tenant-scoped management  
3. **Org Admin** (2) → Organization-scoped management
4. **Org Member** (1) → Company & prediction access
5. **User** (0) → Basic profile access only

### Security Implementation
- **Organization Isolation**: Users see only their organization's data
- **Dynamic Global Access**: Controlled by `allow_global_data_access` flag
- **Role-Based Filtering**: All endpoints filter data based on user role
- **Tenant Scoping**: Tenant admins restricted to their tenant's organizations

### Access Patterns
- **Super Admin**: Sees everything globally
- **Tenant Admin**: Sees all orgs in their tenant + global data if org allows
- **Org Admin/Member**: Sees org data + global data if org allows + own predictions
- **User (no org)**: Sees only their own predictions/companies

---

## 🚀 **Quick Start for HDFC Bank Case**

1. **Login as Super Admin**
   ```bash
   POST /api/v1/auth/login
   {
     "email": "admin@system.com",
     "password": "admin123"
   }
   ```

2. **Assign Existing User as Tenant Admin**
   ```bash
   POST /api/v1/assign-existing-user
   {
     "email": "admin@hdfc.com",
     "tenant_id": "{tenant_id}"
   }
   ```

3. **Create HDFC Organizations**
   ```bash
   POST /api/v1/organizations
   {
     "name": "HDFC Corporate",
     "tenant_id": "{tenant_id}"
   }
   ```

4. **Run ML Predictions**
   ```bash
   POST /api/v1/predictions/annual
   {
     "company_symbol": "HDFC",
     "company_name": "HDFC Bank",
     "market_cap": 850000,
     "sector": "Banking",
     "reporting_year": "2024",
     "long_term_debt_to_total_capital": 15.5,
     "total_debt_to_ebitda": 2.3,
     "net_income_margin": 22.1,
     "ebit_to_interest_expense": 8.5,
     "return_on_assets": 1.8
   }
   ```

---

## 📝 **Notes for Testing**

- All endpoints require proper JWT authentication (except public ones)
- Use `Authorization: Bearer {token}` header
- Paginated endpoints support `page`, `size`, `search`, `sort_by`, `sort_order` query params
- Role-based access is strictly enforced - ensure correct user role for testing
- Organization isolation is complete - cross-org data access blocked unless global access enabled

**Total Endpoints: 71 API endpoints** 
**Security Features: 5-role hierarchy, organization isolation, dynamic global access control**
