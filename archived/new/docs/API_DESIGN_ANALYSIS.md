# 🎯 API Design Analysis & New Multi-Tenant API Structure

## 📊 **Current API Analysis**

### 🔍 **Existing APIs Found**
```
/auth/          - Authentication endpoints
/companies/     - Company management  
/predictions/   - Prediction management
```

### 📋 **Current Auth Endpoints** (`/auth/`)
```python
POST /auth/register          - User registration
POST /auth/login            - User login  
POST /auth/verify-otp       - Email verification
POST /auth/request-otp      - Request verification
POST /auth/reset-password   - Password reset
GET  /auth/me              - Get current user
PUT  /auth/me              - Update user profile
POST /auth/logout          - User logout
```

### 🏢 **Current Company Endpoints** (`/companies/`)
```python
GET  /companies/           - List companies (paginated)
POST /companies/           - Create company
GET  /companies/{id}       - Get company details
PUT  /companies/{id}       - Update company
DELETE /companies/{id}     - Delete company
```

### 📊 **Current Prediction Endpoints** (`/predictions/`)
```python
POST /predictions/annual    - Create annual prediction
POST /predictions/quarterly - Create quarterly prediction  
POST /predictions/unified   - Unified prediction endpoint
GET  /predictions/company/{id} - Get company predictions
POST /predictions/bulk      - Bulk predictions upload
GET  /predictions/jobs/{id} - Check bulk job status
```

---

## 🚨 **Problems with Current APIs**

### ❌ **Major Issues**
1. **No Organization Support**: All endpoints are global
2. **Old Authentication**: Using manual BCrypt+JWT (slow)
3. **No Data Isolation**: Users see all data
4. **No Invitation System**: Can't invite users to organizations
5. **No Role Management**: No organization-level permissions
6. **No Multi-tenant Filtering**: Data not filtered by organization

---

## 🎯 **New API Structure Needed**

### 🔐 **1. Authentication APIs** (FastAPI-Users)
```python
# FastAPI-Users auto-generated endpoints
POST /auth/register                    - Register new user
POST /auth/login                      - Login user  
POST /auth/logout                     - Logout user
POST /auth/forgot-password            - Request password reset
POST /auth/reset-password             - Reset password with token
POST /auth/request-verify-token       - Request email verification
POST /auth/verify                     - Verify email with token
GET  /auth/me                         - Get current user
PATCH /auth/me                        - Update user profile
```

### 🏢 **2. Organization Management APIs** (NEW)
```python
# Organization CRUD
GET    /organizations/                 - List user's organizations
POST   /organizations/                 - Create new organization
GET    /organizations/{org_id}         - Get organization details  
PUT    /organizations/{org_id}         - Update organization
DELETE /organizations/{org_id}         - Delete organization

# Organization Members
GET    /organizations/{org_id}/members - List organization members
PUT    /organizations/{org_id}/members/{user_id}/role - Update member role
DELETE /organizations/{org_id}/members/{user_id} - Remove member

# Organization Invitations  
POST   /organizations/{org_id}/invite  - Invite user to organization
GET    /organizations/{org_id}/invitations - List pending invitations
DELETE /organizations/{org_id}/invitations/{invite_id} - Cancel invitation
```

### 📧 **3. Invitation APIs** (NEW)
```python
GET  /invitations/                    - List my invitations
POST /invitations/accept              - Accept invitation
POST /invitations/decline             - Decline invitation
GET  /invitations/{token}             - Get invitation details
```

### 🏢 **4. Enhanced Company APIs** (Updated)
```python
# Organization-filtered companies
GET    /companies/                    - List companies (org + global)
POST   /companies/                    - Create company in organization
GET    /companies/{id}                - Get company details
PUT    /companies/{id}                - Update company
DELETE /companies/{id}                - Delete company

# Global companies (admin only)
GET    /companies/global              - List global companies
POST   /companies/global              - Create global company
PUT    /companies/global/{id}         - Update global company
```

### 📊 **5. Enhanced Prediction APIs** (Updated)
```python
# Organization-filtered predictions
GET    /predictions/                  - List predictions (org + personal + global)
POST   /predictions/annual            - Create annual prediction  
POST   /predictions/quarterly         - Create quarterly prediction
GET    /predictions/{id}              - Get prediction details
PUT    /predictions/{id}              - Update prediction
DELETE /predictions/{id}              - Delete prediction

# Personal predictions
GET    /predictions/personal          - List personal predictions
POST   /predictions/personal          - Create personal prediction

# Organization predictions  
GET    /predictions/organization      - List organization predictions
GET    /predictions/organization/{org_id} - List specific org predictions (admin)

# Bulk operations
POST   /predictions/bulk              - Bulk upload with org context
GET    /predictions/jobs/{id}         - Check bulk job status
```

### 👥 **6. User Management APIs** (Enhanced)
```python
# Profile management
GET    /users/me                      - Get my profile
PUT    /users/me                      - Update my profile
GET    /users/me/organizations        - List my organizations

# Admin user management
GET    /users/                        - List users (admin only)
GET    /users/{id}                    - Get user details (admin only)  
PUT    /users/{id}/global-role        - Update global role (super admin only)
PUT    /users/{id}/status             - Activate/deactivate user (admin only)
```

### 📊 **7. Analytics & Reporting APIs** (NEW)
```python
# Organization analytics
GET /analytics/organization/{org_id}/dashboard - Organization dashboard
GET /analytics/organization/{org_id}/predictions - Prediction analytics
GET /analytics/organization/{org_id}/companies - Company analytics

# Global analytics (admin only)
GET /analytics/global/dashboard        - Global system dashboard
GET /analytics/global/organizations    - Organization analytics
GET /analytics/global/users           - User analytics
```

---

## 🔧 **API Implementation Plan**

### 📅 **Phase 1: Core Authentication & Organizations**
1. ✅ **Replace auth endpoints** with FastAPI-Users
2. ✅ **Create organization management** endpoints
3. ✅ **Implement invitation system**
4. ✅ **Add role-based access control**

### 📅 **Phase 2: Enhanced Data APIs**  
1. ✅ **Update company endpoints** with organization filtering
2. ✅ **Update prediction endpoints** with multi-tenant support
3. ✅ **Add personal prediction support**
4. ✅ **Implement data isolation**

### 📅 **Phase 3: Advanced Features**
1. ✅ **Add user management** endpoints
2. ✅ **Create analytics dashboards**
3. ✅ **Implement bulk operations** with org context
4. ✅ **Add audit logging**

---

## 🔒 **Security & Permission Matrix**

### 🌍 **Global Permissions**
```python
super_admin:  All endpoints ✅
admin:        Organization creation, global company management ✅  
user:         Personal predictions, join organizations ✅
```

### 🏢 **Organization Permissions**
```python
org_admin:    Manage org, invite users, assign roles ✅
org_member:   Create predictions, view org data ✅
org_viewer:   Read-only access to org data ✅
```

### 📊 **Data Access Rules**
```python
Global Data:       Visible to all users ✅
Organization Data: Only org members ✅  
Personal Data:     Only creator ✅
Cross-org Access:  Only super_admin ✅
```

---

## 🎯 **Next Steps**

Want me to implement these APIs in order of priority?

1. **Start with FastAPI-Users auth endpoints** (replace current auth)
2. **Create organization management** endpoints  
3. **Add invitation system**
4. **Update existing company/prediction endpoints** with org filtering

Which phase should we start with?
