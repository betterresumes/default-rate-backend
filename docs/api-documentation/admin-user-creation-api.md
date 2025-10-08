# Admin User Creation API

This document explains how administrators can create users with different roles using AccuNode's Admin API.

## Overview

The Admin User Creation API allows privileged users (Super Admin, Tenant Admin, Org Admin) to create new user accounts with specific roles. This is different from public registration, which always creates users with the basic "user" role.

## Base Information

- **Base URL**: `/api/v1/auth/admin`
- **Authentication Required**: Yes (Bearer token)
- **Rate Limits**: Protected by `@rate_limit_user_create` decorator

## User Role Hierarchy

AccuNode uses a hierarchical role system with the following roles (from highest to lowest privilege):

1. **`super_admin`** - System-wide administration, can manage everything
2. **`tenant_admin`** - Manages entire tenant and all organizations within it
3. **`org_admin`** - Manages specific organization and its members
4. **`org_member`** - Member of specific organization with limited permissions
5. **`user`** - Basic user with no organizational affiliation (default)

## API Endpoint

### Create User (Admin Only)

**Endpoint**: `POST /api/v1/auth/admin/create-user`

**Access Control**: 
- **Super Admin**: Can create users with **ANY** role
- **Tenant Admin**: Can create users with roles: `user`, `org_admin`, `org_member`
- **Org Admin**: Can create users with roles: `user`, `org_member`

**Authentication**: Include Bearer token in Authorization header
```
Authorization: Bearer {your_jwt_token}
```

## Request Schema

### Required Fields
- `email` (EmailStr) - Must be unique across the system
- `password` (string) - Must be at least 8 characters with 1 letter and 1 number
- `full_name` (string) - User's display name

### Optional Fields
- `username` (string) - Auto-generated from email if not provided
- `role` (string) - Defaults to "user" if not specified
- `first_name` (string) - User's first name
- `last_name` (string) - User's last name

### Request Example
```json
{
    "email": "user@example.com",
    "username": "username123",
    "full_name": "Full Name",
    "password": "SecurePass123!",
    "role": "super_admin",
    "first_name": "First",
    "last_name": "Last"
}
```

## Role Assignment Rules

### Super Admin Privileges
```json
// Super Admin can create ANY role
{
    "role": "super_admin"      // ✅ Allowed
}
{
    "role": "tenant_admin"     // ✅ Allowed
}
{
    "role": "org_admin"        // ✅ Allowed
}
{
    "role": "org_member"       // ✅ Allowed
}
{
    "role": "user"             // ✅ Allowed
}
```

### Tenant Admin Privileges
```json
// Tenant Admin can create limited roles
{
    "role": "user"             // ✅ Allowed
}
{
    "role": "org_admin"        // ✅ Allowed
}
{
    "role": "org_member"       // ✅ Allowed
}
{
    "role": "super_admin"      // ❌ Forbidden
}
{
    "role": "tenant_admin"     // ❌ Forbidden
}
```

### Org Admin Privileges
```json
// Org Admin can create basic roles only
{
    "role": "user"             // ✅ Allowed
}
{
    "role": "org_member"       // ✅ Allowed
}
{
    "role": "org_admin"        // ❌ Forbidden
}
{
    "role": "tenant_admin"     // ❌ Forbidden
}
{
    "role": "super_admin"      // ❌ Forbidden
}
```

## Response Schema

### Success Response (201 Created)
```json
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "username": "username123",
    "full_name": "Full Name",
    "role": "super_admin",
    "organization_id": null,
    "tenant_id": null,
    "is_active": true,
    "created_at": "2025-10-09T12:00:00Z",
    "last_login": null
}
```

## Usage Examples

### 1. Create Super Admin
```bash
curl -X POST "http://localhost:8000/api/v1/auth/admin/create-user" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "superadmin@accunode.ai",
    "password": "SuperAdmin2024!",
    "full_name": "Super Administrator",
    "role": "super_admin"
  }'
```

### 2. Create Tenant Admin
```bash
curl -X POST "http://localhost:8000/api/v1/auth/admin/create-user" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "tenantadmin@company.com",
    "password": "TenantAdmin2024!",
    "full_name": "Tenant Administrator", 
    "role": "tenant_admin"
  }'
```

### 3. Create Organization Admin
```bash
curl -X POST "http://localhost:8000/api/v1/auth/admin/create-user" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "orgadmin@company.com",
    "password": "OrgAdmin2024!",
    "full_name": "Organization Administrator",
    "role": "org_admin"
  }'
```

### 4. Create Organization Member
```bash
curl -X POST "http://localhost:8000/api/v1/auth/admin/create-user" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "member@company.com",
    "password": "Member2024!",
    "full_name": "Organization Member",
    "role": "org_member"
  }'
```

### 5. Create Basic User
```bash
curl -X POST "http://localhost:8000/api/v1/auth/admin/create-user" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "basicuser@company.com",
    "password": "BasicUser2024!",
    "full_name": "Basic User",
    "role": "user"
  }'
```

## Python Integration Example

```python
import requests
from typing import Dict, Any

class AdminUserManager:
    def __init__(self, base_url: str, admin_token: str):
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {admin_token}',
            'Content-Type': 'application/json'
        }
    
    def create_user(self, 
                   email: str, 
                   password: str, 
                   full_name: str, 
                   role: str = "user",
                   username: str = None,
                   first_name: str = None,
                   last_name: str = None) -> Dict[str, Any]:
        """Create a new user with specified role"""
        
        user_data = {
            "email": email,
            "password": password,
            "full_name": full_name,
            "role": role
        }
        
        # Add optional fields if provided
        if username:
            user_data["username"] = username
        if first_name:
            user_data["first_name"] = first_name  
        if last_name:
            user_data["last_name"] = last_name
        
        response = requests.post(
            f"{self.base_url}/api/v1/auth/admin/create-user",
            headers=self.headers,
            json=user_data
        )
        
        if response.status_code == 201:
            return response.json()
        else:
            raise Exception(f"Failed to create user: {response.status_code} - {response.text}")

# Usage Example
admin_manager = AdminUserManager(
    base_url="http://localhost:8000",
    admin_token="your_super_admin_token_here"
)

# Create different types of users
super_admin = admin_manager.create_user(
    email="new.superadmin@company.com",
    password="SuperSecure2024!",
    full_name="New Super Admin",
    role="super_admin"
)

tenant_admin = admin_manager.create_user(
    email="new.tenantadmin@company.com", 
    password="TenantSecure2024!",
    full_name="New Tenant Admin",
    role="tenant_admin"
)

org_admin = admin_manager.create_user(
    email="new.orgadmin@company.com",
    password="OrgSecure2024!", 
    full_name="New Org Admin",
    role="org_admin"
)
```

## JavaScript Integration Example

```javascript
class AdminUserManager {
    constructor(baseUrl, adminToken) {
        this.baseUrl = baseUrl.replace(/\/$/, '');
        this.headers = {
            'Authorization': `Bearer ${adminToken}`,
            'Content-Type': 'application/json'
        };
    }
    
    async createUser({
        email,
        password,
        fullName,
        role = 'user',
        username = null,
        firstName = null,
        lastName = null
    }) {
        const userData = {
            email,
            password,
            full_name: fullName,
            role
        };
        
        // Add optional fields if provided
        if (username) userData.username = username;
        if (firstName) userData.first_name = firstName;
        if (lastName) userData.last_name = lastName;
        
        const response = await fetch(
            `${this.baseUrl}/api/v1/auth/admin/create-user`,
            {
                method: 'POST',
                headers: this.headers,
                body: JSON.stringify(userData)
            }
        );
        
        if (response.status === 201) {
            return await response.json();
        } else {
            const error = await response.text();
            throw new Error(`Failed to create user: ${response.status} - ${error}`);
        }
    }
}

// Usage Example
const adminManager = new AdminUserManager(
    'http://localhost:8000',
    'your_super_admin_token_here'
);

// Create different types of users
try {
    const superAdmin = await adminManager.createUser({
        email: 'new.superadmin@company.com',
        password: 'SuperSecure2024!',
        fullName: 'New Super Admin',
        role: 'super_admin'
    });
    
    console.log('Super admin created:', superAdmin);
    
    const tenantAdmin = await adminManager.createUser({
        email: 'new.tenantadmin@company.com',
        password: 'TenantSecure2024!',
        fullName: 'New Tenant Admin', 
        role: 'tenant_admin'
    });
    
    console.log('Tenant admin created:', tenantAdmin);
    
} catch (error) {
    console.error('Error creating user:', error.message);
}
```

## Password Requirements

All passwords must meet these security requirements:

- ✅ **Minimum 8 characters**
- ✅ **At least 1 letter** (a-z or A-Z)
- ✅ **At least 1 number** (0-9)
- ✅ **No maximum length limit**

### Valid Password Examples
- `Password123!`
- `MySecure2024Pass`
- `Admin@User456`

### Invalid Password Examples
- `password` (no numbers)
- `12345678` (no letters)
- `Pass123` (too short)

## Username Generation Rules

If no username is provided, the system automatically generates one:

1. **Extract from email**: `john.doe@company.com` → `john_doe`
2. **Clean special characters**: Replace non-alphanumeric chars with underscores
3. **Handle duplicates**: Add incremental numbers (`john_doe_1`, `john_doe_2`)
4. **Fallback**: Use "user" if extraction fails
5. **Maximum attempts**: 100 tries before giving up

## Error Responses

### Common Error Codes

| Status | Error Message | Cause | Solution |
|--------|---------------|-------|----------|
| **400** | "Email already registered" | Email is taken | Use different email |
| **400** | "Username 'xyz' is already taken" | Username conflicts | Choose different username |
| **400** | "Password must be at least 8 characters" | Password too short | Use longer password |
| **400** | "Password must contain at least one letter" | Missing letters | Add letters to password |
| **400** | "Password must contain at least one number" | Missing numbers | Add numbers to password |
| **403** | "Super admin privileges required" | Insufficient permissions | Login as super admin |
| **403** | "Tenant admins can only create users with 'user', 'org_admin', or 'org_member' roles" | Role restriction violation | Use allowed role for your level |
| **429** | "Too many requests" | Rate limit exceeded | Wait and retry |

### Error Response Format
```json
{
    "detail": "Email already registered"
}
```

## Security Considerations

### Authentication Security
- **Token Required**: All requests must include valid Bearer token
- **Role Validation**: System enforces role hierarchy restrictions  
- **Permission Checks**: Each request validates user's permission to create specified role

### Password Security
- **Hashing**: Passwords are hashed using bcrypt with salt
- **No Storage**: Plain text passwords are never stored
- **Validation**: Real-time password strength checking

### Rate Limiting
- **Protection**: Prevents abuse and automated attacks
- **Configurable**: Limits can be adjusted via middleware settings
- **Fair Usage**: Ensures system availability for all users

## Best Practices

### For Super Admins
1. **Principle of Least Privilege**: Create users with minimum required role
2. **Strong Passwords**: Enforce strong password policies
3. **Regular Audits**: Monitor user creation activities
4. **Secure Tokens**: Protect admin tokens and rotate regularly

### For Development
1. **Test Environment**: Use separate credentials for testing
2. **Error Handling**: Implement proper error handling in integrations
3. **Logging**: Log user creation events for audit trails
4. **Validation**: Validate inputs before API calls

### For Production
1. **Environment Variables**: Store tokens in environment variables, not code
2. **HTTPS Only**: Always use HTTPS in production
3. **Monitoring**: Set up alerts for unusual user creation patterns
4. **Backup**: Maintain backups of user data

## Related APIs

- **[Authentication API](authentication-api.md)** - User login and registration
- **[Users API](users-api.md)** - User management and updates
- **[Organizations API](organizations-api.md)** - Organization management
- **[Tenants API](tenants-api.md)** - Tenant management

## Support

For additional support or questions about the Admin User Creation API:
- Check the error messages and solutions above
- Review the related API documentation
- Contact your system administrator
- File a support ticket if issues persist
