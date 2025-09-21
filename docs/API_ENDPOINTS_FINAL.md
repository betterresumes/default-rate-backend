# 📋 FINAL API ENDPOINTS - COMPLETE DOCUMENTATION

**Financial Default Risk Prediction API - Multi-Tenant v2.0.0**

## 🎯 **SUMMARY: 60 Total Endpoints Across 8 Sections**

---

## **1. 🔐 USER AUTHENTICATION** (5 endpoints) - *Public/User Access*

| Method | Endpoint | Description | Access Level |
|--------|----------|-------------|--------------|
| POST | `/api/v1/auth/register` | User registration | Public |
| POST | `/api/v1/auth/login` | User login | Public |
| POST | `/api/v1/auth/join` | Join organization with token | User |
| POST | `/api/v1/auth/refresh` | Refresh tokens | User |
| POST | `/api/v1/auth/logout` | User logout | User |

---

## **2. 👨‍💼 ADMIN AUTHENTICATION** (5 endpoints) - *Super Admin Only*

| Method | Endpoint | Description | Access Level |
|--------|----------|-------------|--------------|
| POST | `/api/v1/auth/admin/create-user` | Admin create user | Super Admin |
| POST | `/api/v1/auth/admin/impersonate/{user_id}` | Admin impersonate user | Super Admin |
| POST | `/api/v1/auth/admin/force-password-reset/{user_id}` | Admin force password reset | Super Admin |
| GET | `/api/v1/auth/admin/audit/login-history/{user_id}` | Admin get login history | Super Admin |
| POST | `/api/v1/auth/admin/bulk-activate` | Admin bulk activate users | Super Admin |

---

## **3. 🎯 TENANT ADMIN MANAGEMENT** (5 endpoints) - *Super Admin Only*

| Method | Endpoint | Description | Access Level | Priority |
|--------|----------|-------------|--------------|----------|
| POST | `/api/v1/tenant-admin/create-tenant-with-admin` | **Create tenant + admin atomically** | Super Admin | ⭐ HIGH |
| POST | `/api/v1/tenant-admin/assign-existing-user` | **Assign existing user as tenant admin** | Super Admin | ⭐ HIGH |
| POST | `/api/v1/tenant-admin/assign-user-to-organization` | **Assign any user to any org with role** | Super Admin | ⭐ HIGH |
| GET | `/api/v1/tenant-admin/tenant/{tenant_id}/admin-info` | Get tenant admin info | Super Admin | Medium |
| DELETE | `/api/v1/tenant-admin/remove-tenant-admin/{user_id}` | Remove tenant admin role | Super Admin | Low |

**🔥 Key APIs for HDFC Bank Case:**
- `create-tenant-with-admin`: For new tenant setup
- `assign-existing-user`: For connecting existing admin@hdfc.com to HDFC Bank tenant  
- `assign-user-to-organization`: For directly assigning users to organizations

---

## **4. 🏢 TENANT MANAGEMENT** (7 endpoints) - *Super Admin Only*

| Method | Endpoint | Description | Access Level |
|--------|----------|-------------|--------------|
| GET | `/api/v1/tenants` | List all tenants | Super Admin |
| POST | `/api/v1/tenants` | Create tenant | Super Admin |
| GET | `/api/v1/tenants/{tenant_id}` | Get tenant details | Super Admin |
| PUT | `/api/v1/tenants/{tenant_id}` | Update tenant | Super Admin |
| DELETE | `/api/v1/tenants/{tenant_id}` | Delete tenant | Super Admin |
| GET | `/api/v1/tenants/{tenant_id}/stats` | Get tenant statistics | Super Admin |
| GET | `/api/v1/tenants/{tenant_id}/admins` | Get tenant admins | Super Admin |

---

## **5. 🏛️ ORGANIZATION MANAGEMENT** (10 endpoints) - *Tenant Admin + Org Admin*

| Method | Endpoint | Description | Access Level |
|--------|----------|-------------|--------------|
| GET | `/api/v1/organizations` | List organizations | Tenant Admin + Org Admin |
| POST | `/api/v1/organizations` | Create organization | Tenant Admin + Org Admin |
| GET | `/api/v1/organizations/{org_id}` | Get organization details | Tenant Admin + Org Admin |
| PUT | `/api/v1/organizations/{org_id}` | Update organization | Tenant Admin + Org Admin |
| DELETE | `/api/v1/organizations/{org_id}` | Delete organization | Tenant Admin + Org Admin |
| POST | `/api/v1/organizations/{org_id}/regenerate-token` | Regenerate join token | Tenant Admin + Org Admin |
| GET | `/api/v1/organizations/{org_id}/whitelist` | Get organization whitelist | Tenant Admin + Org Admin |
| POST | `/api/v1/organizations/{org_id}/whitelist` | Add to whitelist | Tenant Admin + Org Admin |
| DELETE | `/api/v1/organizations/{org_id}/whitelist/{email}` | Remove from whitelist | Tenant Admin + Org Admin |
| GET | `/api/v1/organizations/{org_id}/users` | Get organization users | Tenant Admin + Org Admin |

---

## **6. 👥 USER MANAGEMENT** (9 endpoints) - *Role-Based Access*

### Self-Service (Any User)
| Method | Endpoint | Description | Access Level |
|--------|----------|-------------|--------------|
| GET | `/api/v1/users/profile` | Get current user profile | Any User |
| PUT | `/api/v1/users/profile` | Update current user profile | Any User |

### Admin Operations (Super Admin + Tenant Admin + Org Admin)
| Method | Endpoint | Description | Access Level |
|--------|----------|-------------|--------------|
| GET | `/api/v1/users` | List users (scoped by role) | Admin Roles |
| POST | `/api/v1/users` | Create user | Admin Roles |
| GET | `/api/v1/users/{user_id}` | Get user details | Admin Roles |
| PUT | `/api/v1/users/{user_id}` | Update user | Admin Roles |
| DELETE | `/api/v1/users/{user_id}` | Remove user | Admin Roles |
| PUT | `/api/v1/users/{user_id}/role` | Update user role | Admin Roles |
| POST | `/api/v1/users/{user_id}/activate` | Activate user | Admin Roles |
| POST | `/api/v1/users/{user_id}/deactivate` | Deactivate user | Admin Roles |

---

## **7. 🏭 COMPANIES** (4 endpoints) - *Org Members + Above*

| Method | Endpoint | Description | Access Level |
|--------|----------|-------------|--------------|
| GET | `/api/v1/companies/` | Get companies (paginated) | Members + |
| POST | `/api/v1/companies/` | Create company | Members + |
| GET | `/api/v1/companies/{company_id}` | Get company by ID | Members + |
| GET | `/api/v1/companies/search/{symbol}` | Get company by symbol | Members + |

---

## **8. 📊 PREDICTIONS** (15 endpoints) - *Org Members + Above*

### Core Prediction APIs (High Priority)
| Method | Endpoint | Description | Access Level | Priority |
|--------|----------|-------------|--------------|----------|
| POST | `/api/v1/predictions/unified-predict` | **Main prediction API** | Members + | ⭐ HIGH |
| GET | `/api/v1/predictions/companies` | **Get companies with predictions** | Members + | ⭐ HIGH |
| GET | `/api/v1/predictions/summary` | **Get summary stats** | Members + | ⭐ HIGH |

### Individual Prediction Types (Optional)
| Method | Endpoint | Description | Access Level |
|--------|----------|-------------|--------------|
| POST | `/api/v1/predictions/predict-annual` | Annual predictions | Members + |
| POST | `/api/v1/predictions/predict-quarterly` | Quarterly predictions | Members + |

### Bulk Operations (Advanced Users)
| Method | Endpoint | Description | Access Level |
|--------|----------|-------------|--------------|
| POST | `/api/v1/predictions/bulk-predict` | Bulk predict from file | Members + |
| POST | `/api/v1/predictions/bulk-predict-async` | Bulk predict async | Members + |
| GET | `/api/v1/predictions/job-status/{job_id}` | Get job status | Members + |
| GET | `/api/v1/predictions/job-result/{job_id}` | Get job result | Members + |

### Management Operations
| Method | Endpoint | Description | Access Level |
|--------|----------|-------------|--------------|
| PUT | `/api/v1/predictions/update/{company_id}` | Update company prediction | Members + |
| DELETE | `/api/v1/predictions/delete/{company_id}` | Delete company and predictions | Members + |

---

## 🔐 **ROLE-BASED ACCESS CONTROL MATRIX**

| **Role** | **Description** | **Access Scope** |
|----------|-----------------|------------------|
| **Super Admin** | System administrator | All endpoints, full system access |
| **Tenant Admin** | Tenant administrator | Organizations, users, companies, predictions within tenant |
| **Org Admin** | Organization administrator | Users, companies, predictions within organization |
| **Member** | Organization member | Companies, predictions within organization |
| **User** | Basic user | Profile management only |

---

## 🚀 **QUICK START WORKFLOW - HDFC BANK CASE**

### **Step 1: Fix Existing Setup** (Your Current Situation)
```bash
# 1. Login as Super Admin
POST /api/v1/auth/login
{
  "email": "superadmin@system.com",
  "password": "your_password"
}

# 2. Connect admin@hdfc.com to HDFC Bank tenant
POST /api/v1/tenant-admin/assign-existing-user
{
  "user_email": "admin@hdfc.com",
  "tenant_id": "19c27efd-bbcb-48f8-9f0e-15408c681229"
}
```

### **Step 2: Use HDFC Bank System**
```bash
# 3. Login as HDFC Bank admin
POST /api/v1/auth/login
{
  "email": "admin@hdfc.com", 
  "password": "hdfc_password"
}

# 4. Create HDFC organizations
POST /api/v1/organizations
{
  "name": "HDFC Retail Banking",
  "description": "Retail banking division"
}

# 5. Add companies to analyze
POST /api/v1/companies/
{
  "name": "Target Company Ltd",
  "symbol": "TARGET",
  "sector": "Technology"
}

# 6. Run ML predictions
POST /api/v1/predictions/unified-predict
{
  "company_id": "company_uuid",
  "prediction_type": "annual"
}

# 7. View results
GET /api/v1/predictions/companies
GET /api/v1/predictions/summary
```

---

## 🎯 **ESSENTIAL ENDPOINTS FOR HDFC BANK (7 CORE APIs)**

1. `POST /api/v1/auth/login` - Authentication
2. `POST /api/v1/tenant-admin/assign-existing-user` - Fix HDFC setup ⭐
3. `POST /api/v1/organizations` - Create organizations
4. `POST /api/v1/companies/` - Add companies
5. `POST /api/v1/predictions/unified-predict` - Run predictions ⭐
6. `GET /api/v1/predictions/companies` - View results
7. `GET /api/v1/predictions/summary` - View statistics

---

## 📊 **ENDPOINT COUNT BY SECTION**

- **Predictions**: 15 endpoints (26%)
- **Organization Management**: 10 endpoints (17%)
- **User Management**: 9 endpoints (15%)
- **Tenant Management**: 7 endpoints (12%)
- **User Authentication**: 5 endpoints (8%)
- **Admin Authentication**: 5 endpoints (8%)
- **Companies**: 4 endpoints (7%)
- **Tenant Admin Management**: 5 endpoints (8%)

**Total: 60 endpoints across 8 sections**

---

*Updated: September 19, 2025*  
*API Documentation for Financial Default Risk Prediction System v2.0.0*
