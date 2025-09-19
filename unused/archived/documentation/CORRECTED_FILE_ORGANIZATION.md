## 📁 CORRECTED FILE ORGANIZATION PLAN

### ✅ **CORE/MAIN FILES (KEEP IN ROOT & SRC):**

#### **Main Startup Files:**
- `start_api.py` - **MAIN STARTUP** (now includes ALL routers)
- `src/app.py` - **COMPLETE APP** (includes predictions, companies, celery)

#### **Core Database & Auth:**
- `src/database.py` - **MAIN DATABASE** models
- `src/schemas.py` - **MAIN SCHEMAS** 
- `src/email_service.py` - Email functionality

#### **Core Routers (ALL ESSENTIAL):**
- `src/routers/auth_multi_tenant.py` - **ACTIVE AUTH** router
- `src/routers/tenants.py` - **TENANT MANAGEMENT**
- `src/routers/organizations_multi_tenant.py` - **ORG MANAGEMENT**
- `src/routers/users.py` - **USER MANAGEMENT**
- `src/routers/companies.py` - **COMPANIES API** ⭐ CORE
- `src/routers/predictions.py` - **PREDICTIONS API** ⭐ CORE
- `src/routers/predictions.py.bak` - Backup of predictions

#### **Core Worker System:**
- `src/celery_app.py` - **CELERY SETUP** ⭐ CORE
- `src/tasks.py` - **BACKGROUND TASKS** ⭐ CORE  
- `src/workers.py` - **WORKER PROCESSES** ⭐ CORE

#### **Core Utilities:**
- `src/join_link_manager.py` - **JOIN LINK MANAGEMENT** ⭐ CORE
- `src/org_code_manager.py` - **ORG CODE MANAGEMENT** ⭐ CORE
- `src/ml_service.py` - **ML PREDICTIONS**
- `src/quarterly_ml_service.py` - **QUARTERLY ML**
- `src/services.py` - **CORE SERVICES**
- `src/tenant_utils.py` - **TENANT UTILITIES**

#### **Configuration Files:**
- `requirements.txt` - Main dependencies
- `Dockerfile` - Main Docker config
- `docker-compose.prod.yml` - Production compose
- `.env` - Environment config

---

### 🗂️ **FILES CORRECTLY MOVED TO "new" FOLDER:**

#### **✅ Unused/Alternative Auth Files:**
- `new/unused_routers/auth.py` - Old auth router
- `new/unused_routers/auth_new.py` - Alternative auth
- `new/unused_routers/auth_simple.py` - Simple auth  
- `new/unused_routers/auth_unified.py` - Unified auth
- `new/unused_src/auth.py` - Old auth file
- `new/unused_src/auth_fastapi_users.py` - FastAPI users auth
- `new/unused_src/auth_system.py` - Alternative auth system

#### **✅ Unused Schema Files:**
- `new/unused_src/schemas_new.py` - Alternative schemas
- `new/unused_src/schemas_backup.py` - Backup schemas

#### **✅ Unused Organization Files:**
- `new/unused_routers/organizations.py` - Old orgs router

#### **✅ Test Files:**
- `new/tests/test_all_apis.py`
- `new/tests/test_api.py` 
- `new/tests/test_clean_api.py`
- `new/tests/test_db.py`
- `new/tests/check_db.py`

#### **✅ Migration/Setup Scripts:**
- `new/migrations/migrate_*.py`
- `new/migrations/populate_data.py`
- `new/migrations/reset_and_migrate_db.py`
- `new/migrations/cleanup_*.py`
- `new/migrations/database_schema_new.py`

#### **✅ Alternative Configs:**
- `new/configs/Dockerfile.local`
- `new/configs/docker-compose.local.yml`
- `new/configs/requirements.local.txt`
- `new/configs/requirements.prod.txt`
- `new/configs/railway*.toml`
- `new/configs/nixpacks.toml`

#### **✅ Design Files:**
- `new/design.html`
- `new/design.tex`
- `new/resend_email_service.py`

---

### 🎯 **CURRENT API ENDPOINTS (COMPLETE):**

#### **Authentication (`/api/auth/`)**
- `POST /register` - Register new user
- `POST /login` - User login
- `POST /join` - Join organization (whitelist-based)
- `GET /me` - Get user profile
- `POST /refresh` - Refresh token
- `POST /logout` - Logout

#### **Tenant Management (`/api/tenants/`)**  
- `POST /` - Create tenant (Super Admin only)
- `GET /` - List tenants (Super Admin only)
- `PUT /{id}` - Update tenant
- `DELETE /{id}` - Delete tenant

#### **Organization Management (`/api/organizations/`)**
- `POST /` - Create organization  
- `GET /` - List organizations
- `PUT /{id}` - Update organization
- `DELETE /{id}` - Delete organization
- `POST /{id}/whitelist` - Add emails to whitelist
- `GET /{id}/whitelist` - View authorized emails

#### **User Management (`/api/users/`)**
- `GET /profile` - Get user profile
- `PUT /profile` - Update profile
- `GET /organization-members` - List organization members
- `PUT /members/{user_id}/role` - Change user role
- `PUT /members/{user_id}/activate` - Activate/deactivate user

#### **Companies API (`/api/v1/companies/`) ⭐ CORE**
- Company data management for predictions

#### **Predictions API (`/api/v1/predictions/`) ⭐ CORE**
- Annual and quarterly default risk predictions
- Background processing with Celery
- ML model integration

---

### ✅ **VERIFICATION:**
- ✅ **All core files preserved**
- ✅ **Predictions & Companies APIs included** 
- ✅ **Celery workers preserved**
- ✅ **Utility managers preserved**
- ✅ **Only unused/alternative files moved**
- ✅ **Complete API functionality maintained**
