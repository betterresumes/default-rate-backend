# 🏦 Financial Risk API - Updated Postman Collection

## 📋 Collection Overview

This updated Postman collection reflects the current **5-role system** and includes all the latest API endpoints with proper role-based access control.

### 🎯 Current Role System

1. **super_admin** - Full system access, can manage everything
2. **tenant_admin** - Attached to 1 tenant, can manage multiple orgs within that tenant  
3. **org_admin** - Attached to 1 organization, can manage users in that org
4. **org_member** - Attached to 1 organization, can access org resources and create predictions
5. **user** - No organization attachment, limited access

## 📁 Collection Structure

The collection is split into 2 parts for easier management:

### Part 1: Core Management (UPDATED_POSTMAN_COLLECTION_PART1.json)
- 🔐 **USER AUTHENTICATION** - Registration, login, organization joining
- 👨‍💼 **ADMIN AUTHENTICATION** - Super admin operations and user management
- 🎯 **TENANT ADMIN MANAGEMENT** - Tenant creation and user assignment
- 🏢 **TENANT MANAGEMENT** - Tenant CRUD operations and statistics

### Part 2: Business Operations (UPDATED_POSTMAN_COLLECTION_PART2.json)
- 🏛️ **ORGANIZATION MANAGEMENT** - Organization CRUD, join tokens, whitelists
- 👥 **USER MANAGEMENT** - Profile management and admin operations
- 🏭 **COMPANIES** - Company management with multi-tenant access
- 📊 **PREDICTIONS** - ML prediction endpoints with role-based access
- 📋 **API INFO** - Health check and documentation endpoints

## 🔧 Import Instructions

### Option 1: Import Both Parts Separately
1. Import `UPDATED_POSTMAN_COLLECTION_PART1.json` into Postman
2. Import `UPDATED_POSTMAN_COLLECTION_PART2.json` into Postman
3. Both collections share the same variables and can be used together

### Option 2: Combine Files (if needed)
If you want a single collection file, you can manually merge the `item` arrays from both files.

## 🚀 Testing Workflow

### 1. Super Admin Setup
```
1. Login as Super Admin → Get access token
2. Create Tenant with Admin → Get tenant_id and organization_id
3. Create additional users and assign roles
```

### 2. Tenant Admin Workflow
```
1. Login as Tenant Admin → Get access token
2. Create organizations within tenant
3. Manage users within tenant scope
4. Access tenant-scoped data
```

### 3. Organization Admin Workflow
```
1. Login as Org Admin → Get access token
2. Manage organization settings
3. Invite users to organization
4. Manage organization data
```

### 4. Organization Member Workflow
```
1. Login as Org Member → Get access token
2. Create companies and predictions
3. Access organization data
4. Use bulk upload features
```

### 5. Basic User Workflow
```
1. Register new account → Get user role
2. Join organization using token → Become org_member
3. Access organization resources
```

## ⚡ Key Features Updated

### Role-Based Access Control
- All endpoints now properly reflect the 5-role hierarchy
- Access descriptions updated for each endpoint
- Proper role validation in request examples

### Prediction System
- Updated to use `reporting_year` and `reporting_quarter` (not legacy `year`/`quarter`)
- Automatic company creation during prediction flow
- Multi-tenant organization context
- Bulk upload functionality with CSV support

### Company Management
- Multi-tenant access control
- Organization-scoped company creation
- Global vs organization-specific companies

### Authentication Flow
- Updated role assignments in user creation
- Proper tenant and organization relationships
- Join token functionality

## 🔄 Variables Used

Both collections use these shared variables:
- `base_url` - API server URL (default: http://localhost:8000)
- `access_token` - JWT authentication token
- `tenant_id` - Current tenant ID
- `organization_id` - Current organization ID  
- `user_id` - Current user ID
- `company_id` - Current company ID
- `prediction_id` - Current prediction ID

## 📝 Testing Notes

1. **Start with Super Admin** - Use super admin login to set up tenants and organizations
2. **Role Hierarchy** - Higher roles can access lower role functionality
3. **Organization Context** - Most business operations are scoped to user's organization
4. **Automatic Relationships** - Companies are automatically created during prediction flow
5. **Multi-tenant Isolation** - Data is properly isolated between tenants and organizations

## 🎯 Complete Testing Scenarios

The collection supports testing all major workflows:
- ✅ Multi-tenant setup and management
- ✅ Role-based user management  
- ✅ Organization lifecycle management
- ✅ Company and prediction CRUD operations
- ✅ Bulk data upload and processing
- ✅ Access control validation
- ✅ Authentication and authorization flows

Both files are ready to import into Postman and can be combined if needed for a unified collection.
