# API Endpoints Organization Summary

## Overview
I've separated your authentication endpoints into two distinct sections for better organization and security:

## 1. **User Authentication** (`/api/v1/auth/`)
**File**: `app/api/v1/auth_multi_tenant.py`
**Tag**: "User Authentication"

### Public/User Endpoints:
- `POST /api/v1/auth/register` - User registration (public)
- `POST /api/v1/auth/login` - User login (public)

### Organization Management:
- `POST /api/v1/auth/join` - Join organization with token (authenticated users)

### Token Management:
- `POST /api/v1/auth/refresh` - Refresh access token (authenticated users)
- `POST /api/v1/auth/logout` - User logout (authenticated users)

---

## 2. **Admin Authentication** (`/api/v1/auth/admin/`)
**File**: `app/api/v1/auth_admin.py`
**Tag**: "Admin Authentication"

### Admin User Management:
- `POST /api/v1/auth/admin/create-user` - Create user with role assignment (Admin only)
- `POST /api/v1/auth/admin/force-password-reset/{user_id}` - Reset user password (Admin only)

### Super Admin Features:
- `POST /api/v1/auth/admin/impersonate/{user_id}` - Impersonate user (Super Admin only)

### Admin Auditing:
- `GET /api/v1/auth/admin/audit/login-history/{user_id}` - View user login history (Admin only)

### Bulk Operations:
- `POST /api/v1/auth/admin/bulk-activate` - Bulk activate users (Admin only)

---

## 3. **Permission Levels**

### Available in Admin Router:
- `require_super_admin()` - Super admin only
- `require_tenant_admin()` - Tenant admin or above  
- `require_org_admin()` - Organization admin or above
- `require_any_admin()` - Any admin level

### Permission Hierarchy:
1. **super_admin** - Full system access
2. **tenant_admin** - Manage users in their tenant
3. **org_admin** - Manage users in their organization  
4. **member/user** - Basic user access

---

## 4. **API Documentation Sections**

When you visit `/docs`, you'll now see:

### "User Authentication" Section:
- Registration, login, organization joining
- Token management
- Public and user-level endpoints

### "Admin Authentication" Section:  
- User creation and management
- Password resets and impersonation
- Auditing and bulk operations
- Admin-only endpoints clearly separated

---

## 5. **Security Benefits**

✅ **Clear Separation**: Admin functions are clearly separated from user functions
✅ **Permission Validation**: Each admin endpoint validates appropriate permissions
✅ **Audit Trail**: Admin actions are logged for security
✅ **Self-Protection**: Admins cannot remove/deactivate themselves
✅ **Scope Limitation**: Admins can only manage users within their scope

---

## 6. **Usage Examples**

### Regular User Registration:
```bash
POST /api/v1/auth/register
{
  "email": "user@example.com",
  "password": "securepass123",
  "full_name": "John Doe"
}
```

### Admin Creating User:
```bash
POST /api/v1/auth/admin/create-user
Authorization: Bearer <admin_token>
{
  "email": "newuser@example.com", 
  "password": "temppass123",
  "full_name": "Jane Smith",
  "global_role": "user"
}
```

### Admin Password Reset:
```bash
POST /api/v1/auth/admin/force-password-reset/user-id-123
Authorization: Bearer <admin_token>
{
  "new_password": "newpass123"
}
```

This organization makes your API much cleaner and more secure by clearly separating admin functions from regular user operations!
