## 📁 FILE ORGANIZATION ANALYSIS

### ✅ **MAIN/ACTIVE FILES (Keep in root):**

#### **Core Application Files:**
- `start_api.py` - **MAIN STARTUP** (imports auth_multi_tenant, tenants, organizations_multi_tenant, users)
- `src/database.py` - **MAIN DATABASE** models
- `src/auth_multi_tenant.py` - **ACTIVE AUTH** router
- `src/tenants.py` - **ACTIVE TENANTS** router  
- `src/organizations_multi_tenant.py` - **ACTIVE ORGS** router
- `src/users.py` - **ACTIVE USERS** router
- `src/schemas.py` - **MAIN SCHEMAS** (used by active routers)

#### **Core Support Files:**
- `src/email_service.py` - Email functionality
- `src/ml_service.py` - ML predictions
- `src/quarterly_ml_service.py` - Quarterly ML
- `src/services.py` - Core services

#### **Configuration Files:**
- `requirements.txt` - Main dependencies
- `Dockerfile` - Main Docker config
- `docker-compose.prod.yml` - Production compose
- `.env` - Environment config
- `README.md` - Main documentation

---

### 🗂️ **FILES TO MOVE TO "new" FOLDER:**

#### **Unused/Alternative Auth Files:**
- `src/routers/auth.py` - Old auth router
- `src/routers/auth_new.py` - Alternative auth
- `src/routers/auth_simple.py` - Simple auth
- `src/routers/auth_unified.py` - Unified auth
- `src/auth.py` - Old auth file
- `src/auth_fastapi_users.py` - FastAPI users auth
- `src/auth_system.py` - Alternative auth system

#### **Unused Schema Files:**
- `src/schemas_new.py` - Alternative schemas
- `src/schemas_backup.py` - Backup schemas

#### **Unused Organization Files:**
- `src/routers/organizations.py` - Old orgs router (replaced by organizations_multi_tenant.py)

#### **Test Files:**
- `test_all_apis.py`
- `test_api.py` 
- `test_clean_api.py`
- `test_db.py`
- `check_db.py`

#### **Migration/Setup Scripts:**
- `migrate_database.py`
- `migrate_to_multitenant.py`
- `populate_data.py`
- `reset_and_migrate_db.py`
- `cleanup_invitations.py`
- `cleanup_otp.py`
- `database_schema_new.py`
- `resend_email_service.py`

#### **Documentation Files (Markdown):**
- `API_DESIGN_ANALYSIS.md`
- `API_DOCUMENTATION.md`
- `API_TESTING_REPORT.md`
- `APPLICATION_DESIGN.md`
- `AUTH_SYSTEM_OVERVIEW.md`
- `COMPLETE_API_TEST_PLAN.md`
- `COMPLETE_DESIGN_OVERVIEW.md`
- `DATABASE_DESIGN.md`
- `ENHANCED_PREDICTIONS_SYSTEM.md`
- `FINAL_DATA_ACCESS_RULES.md`
- `INVITATIONS_CLEANUP_SUMMARY.md`
- `MULTI_TENANT_ARCHITECTURE.md`
- `ORGANIZATION_CODE_SYSTEM.md`
- `PERMISSION_MATRIX.md`
- `SECURE_AUTH_FLOW.md`
- `SYSTEM_ARCHITECTURE.md`
- `SYSTEM_OVERVIEW.md`
- `UNIFIED_PREDICTION_API_DESIGN.md`
- `USER_FLOWS.md`

#### **Alternative Docker/Config Files:**
- `Dockerfile.local`
- `docker-compose.local.yml`
- `requirements.local.txt`
- `requirements.prod.txt`

#### **Design Files:**
- `design.html`
- `design.tex`

#### **Railway Config:**
- `railway.toml`
- `railway-worker.toml`
- `nixpacks.toml`

---

### 🎯 **ORGANIZATION STRATEGY:**
1. **Keep essential files** for running the current multi-tenant API
2. **Move all documentation** to new/docs subfolder
3. **Move all test files** to new/tests subfolder  
4. **Move unused routers** to new/unused_routers subfolder
5. **Move migration scripts** to new/migrations subfolder
6. **Move alternative configs** to new/configs subfolder
