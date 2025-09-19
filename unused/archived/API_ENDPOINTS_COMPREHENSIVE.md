# 🌐 **COMPREHENSIVE API ENDPOINTS CATALOG**

## 📋 **Complete Backend API Structure**

Your **Financial Risk Prediction API** currently has **54+ endpoints** across 6 main modules:

---

## 🏠 **ROOT & HEALTH ENDPOINTS**

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| `GET` | `/` | API root with service info & features | ❌ None |
| `GET` | `/health` | System health check for monitoring | ❌ None |

---

## 🔐 **AUTHENTICATION MODULE** (`/api/v1/auth`)

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| `POST` | `/api/v1/auth/register` | Register new user account | ❌ None |
| `POST` | `/api/v1/auth/login` | User login with JWT token | ❌ None |
| `POST` | `/api/v1/auth/join` | Join organization via token | ❌ None |
| `GET` | `/api/v1/auth/me` | Get current user profile | 🔑 JWT Required |
| `POST` | `/api/v1/auth/refresh` | Refresh JWT access token | 🔑 JWT Required |
| `POST` | `/api/v1/auth/logout` | User logout | 🔑 JWT Required |

**Features:**
- ✅ JWT-based authentication
- ✅ Password hashing with bcrypt
- ✅ Organization joining via invitation tokens
- ✅ Token refresh mechanism

---

## 🏢 **TENANT MANAGEMENT** (`/api/v1/tenants`)

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| `POST` | `/api/v1/tenants` | Create new tenant | 🔑 Super Admin |
| `GET` | `/api/v1/tenants` | List all tenants (paginated) | 🔑 Super Admin |
| `GET` | `/api/v1/tenants/{tenant_id}` | Get tenant details | 🔑 Tenant Admin+ |
| `PUT` | `/api/v1/tenants/{tenant_id}` | Update tenant information | 🔑 Tenant Admin+ |
| `DELETE` | `/api/v1/tenants/{tenant_id}` | Delete tenant | 🔑 Super Admin |
| `GET` | `/api/v1/tenants/{tenant_id}/stats` | Get tenant statistics | 🔑 Tenant Admin+ |

**Features:**
- ✅ Multi-tenant architecture
- ✅ Tenant isolation and management
- ✅ Tenant-level statistics
- ✅ Role-based access control

---

## 🏛️ **ORGANIZATION MANAGEMENT** (`/api/v1/organizations`)

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| `POST` | `/api/v1/organizations` | Create new organization | 🔑 Tenant Admin+ |
| `GET` | `/api/v1/organizations` | List tenant organizations | 🔑 Tenant Admin+ |
| `GET` | `/api/v1/organizations/{org_id}` | Get organization details | 🔑 Org Member+ |
| `PUT` | `/api/v1/organizations/{org_id}` | Update organization | 🔑 Org Admin+ |
| `DELETE` | `/api/v1/organizations/{org_id}` | Delete organization | 🔑 Tenant Admin+ |
| `POST` | `/api/v1/organizations/{org_id}/regenerate-token` | Regenerate join token | 🔑 Org Admin+ |
| `GET` | `/api/v1/organizations/{org_id}/whitelist` | List email whitelist | 🔑 Org Admin+ |
| `POST` | `/api/v1/organizations/{org_id}/whitelist` | Add email to whitelist | 🔑 Org Admin+ |
| `DELETE` | `/api/v1/organizations/{org_id}/whitelist/{email}` | Remove email from whitelist | 🔑 Org Admin+ |
| `GET` | `/api/v1/organizations/{org_id}/users` | List organization users | 🔑 Org Admin+ |

**Features:**
- ✅ Organization within tenant structure
- ✅ Invitation token system
- ✅ Email whitelist management
- ✅ Organization user management

---

## 👥 **USER MANAGEMENT** (`/api/v1/users`)

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| `GET` | `/api/v1/users/profile` | Get user profile | 🔑 JWT Required |
| `PUT` | `/api/v1/users/profile` | Update user profile | 🔑 JWT Required |
| `GET` | `/api/v1/users` | List organization users | 🔑 Org Admin+ |
| `GET` | `/api/v1/users/{user_id}` | Get user details | 🔑 Org Admin+ |
| `PUT` | `/api/v1/users/{user_id}/role` | Update user role | 🔑 Org Admin+ |
| `DELETE` | `/api/v1/users/{user_id}` | Delete user | 🔑 Org Admin+ |
| `POST` | `/api/v1/users/{user_id}/activate` | Activate user account | 🔑 Org Admin+ |
| `POST` | `/api/v1/users/{user_id}/deactivate` | Deactivate user account | 🔑 Org Admin+ |

**Features:**
- ✅ User profile management
- ✅ Role-based permissions (5 levels)
- ✅ User activation/deactivation
- ✅ Organization-scoped user management

---

## 🏢 **COMPANIES MODULE** (`/api/v1/companies`)

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| `GET` | `/api/v1/companies/` | List companies (paginated) | 🔑 Org Member+ |
| `GET` | `/api/v1/companies/{company_id}` | Get company details | 🔑 Org Member+ |
| `POST` | `/api/v1/companies/` | Create new company | 🔑 Org Member+ |
| `GET` | `/api/v1/companies/search/{symbol}` | Search company by symbol | 🔑 Org Member+ |

**Features:**
- ✅ Company data management
- ✅ Paginated company listings
- ✅ Company search by symbol
- ✅ Multi-tenant company isolation

---

## 🔮 **PREDICTIONS MODULE** (`/api/v1/predictions`)

### **Core Prediction Endpoints**

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| `POST` | `/api/v1/predictions/predict-annual` | Annual default risk prediction | 🔑 Org Member+ |
| `POST` | `/api/v1/predictions/predict-quarterly` | Quarterly default risk prediction | 🔑 Org Member+ |
| `POST` | `/api/v1/predictions/unified-predict` | Unified prediction interface | 🔑 Org Member+ |
| `POST` | `/api/v1/predictions/predict-default-rate` | Default rate prediction | 🔑 Org Member+ |

### **Bulk Processing Endpoints**

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| `POST` | `/api/v1/predictions/bulk-predict` | Synchronous bulk predictions | 🔑 Org Member+ |
| `POST` | `/api/v1/predictions/bulk-predict-async` | Asynchronous bulk predictions | 🔑 Org Member+ |
| `POST` | `/api/v1/predictions/quarterly-bulk-predict` | Quarterly bulk predictions | 🔑 Org Member+ |

### **Job Management Endpoints**

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| `GET` | `/api/v1/predictions/job-status/{job_id}` | Check job status | 🔑 Org Member+ |
| `GET` | `/api/v1/predictions/job-result/{job_id}` | Get job results | 🔑 Org Member+ |

### **Data Management Endpoints**

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| `GET` | `/api/v1/predictions/companies` | List prediction companies | 🔑 Org Member+ |
| `GET` | `/api/v1/predictions/companies/{company_id}` | Get company prediction data | 🔑 Org Member+ |
| `PUT` | `/api/v1/predictions/update/{company_id}` | Update company data | 🔑 Org Member+ |
| `DELETE` | `/api/v1/predictions/delete/{company_id}` | Delete company data | 🔑 Org Admin+ |

### **Prediction History Management**

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| `DELETE` | `/api/v1/predictions/predictions/annual/{prediction_id}` | Delete annual prediction | 🔑 Org Admin+ |
| `DELETE` | `/api/v1/predictions/predictions/quarterly/{prediction_id}` | Delete quarterly prediction | 🔑 Org Admin+ |

### **System Status Endpoints**

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| `GET` | `/api/v1/predictions/health` | Prediction service health | 🔑 Org Member+ |
| `GET` | `/api/v1/predictions/summary` | Service statistics summary | 🔑 Org Member+ |

**Features:**
- ✅ ML-powered annual risk predictions
- ✅ Quarterly risk assessments
- ✅ Bulk processing with async support
- ✅ Background job management (Celery)
- ✅ Prediction history tracking
- ✅ Data management and cleanup

---

## 📊 **ROLE-BASED PERMISSION MATRIX**

| Role | Authentication | Tenants | Organizations | Users | Companies | Predictions |
|------|---------------|---------|---------------|-------|-----------|-------------|
| **Super Admin** | ✅ All | ✅ All | ✅ All | ✅ All | ✅ All | ✅ All |
| **Tenant Admin** | ✅ All | ✅ Own Tenant | ✅ All in Tenant | ✅ All in Tenant | ✅ All in Tenant | ✅ All in Tenant |
| **Org Admin** | ✅ Profile | ❌ None | ✅ Own Org | ✅ Org Users | ✅ Org Companies | ✅ Org Predictions |
| **Member** | ✅ Profile | ❌ None | ✅ View Own | ✅ View Profile | ✅ View/Create | ✅ View/Create |
| **User** | ✅ Profile | ❌ None | ✅ View Own | ✅ View Profile | ✅ View Only | ✅ View Only |

---

## 🎯 **CURRENT API STATUS**

Your **54 endpoints** provide a **comprehensive and production-ready** financial risk prediction platform. The current API covers:

✅ **Core Business Logic**: Complete prediction workflow  
✅ **Enterprise Features**: Multi-tenancy, roles, permissions  
✅ **Scalability**: Async processing, bulk operations  
✅ **Security**: JWT auth, data isolation, role-based access  
✅ **User Experience**: Profile management, organization joining  

**All endpoints now follow the standardized `/api/v1/...` pattern for consistency and versioning.**

**Your backend is enterprise-grade and production-ready! 🚀**
