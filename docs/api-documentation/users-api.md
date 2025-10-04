# Users API

This document explains how to manage users using AccuNode's API. Users are the people who use the system, with different roles and access levels.

## Users Overview

In AccuNode, **users** are individuals with accounts who can access the system. Each user has a **role** that determines their permissions:

### Role Hierarchy (lowest to highest)
1. **user** - Basic access, limited permissions
2. **org_member** - Can access organization features 
3. **org_admin** - Can manage organization members
4. **tenant_admin** - Can manage multiple organizations
5. **super_admin** - Full system access

### Key Concepts
- **Profile Management**: Users can update their own information
- **Role-Based Access**: Different endpoints require different role levels
- **Organization Assignment**: Users can belong to organizations
- **Admin Management**: Higher-role users can manage lower-role users

## Base Information

- **Base URL**: `/api/v1/users`
- **Authentication**: Bearer token required
- **Access Control**: Role-based permissions

| Endpoint | Purpose | Min Role Required |
|----------|---------|------------------|
| GET /profile | View own profile | user |
| PUT /profile | Update own profile | user |
| GET /me | Detailed profile info | user |
| GET /users | List users | org_admin+ |
| POST /users | Create new user | org_admin+ |
| GET /users/{id} | View user details | org_admin+ |
| PUT /users/{id} | Update user | org_admin+ |
| PUT /users/{id}/role | Change user role | tenant_admin+ |
| DELETE /users/{id} | Delete user | tenant_admin+ |
| POST /users/{id}/activate | Activate user | org_admin+ |
| POST /users/{id}/deactivate | Deactivate user | org_admin+ |

## Profile Management

### 1. Get Your Profile 👤

**Endpoint**: `GET /api/v1/users/profile`

**What it does**: Returns your own user profile information

**Authentication**: Required (Bearer token)

**Request Example**:
```bash
GET /api/v1/users/profile
Authorization: Bearer your_jwt_token
```

**Response Example**:
```json
{
  "id": "user-abc123...",
  "email": "john@company.com",
  "username": "johndoe",
  "full_name": "John Doe",
  "role": "org_member", 
  "organization_id": "org-456def...",
  "tenant_id": "tenant-789ghi...",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-10-05T14:22:00Z",
  "last_login": "2024-10-05T09:15:00Z"
}
```

### 2. Update Your Profile ✏️

**Endpoint**: `PUT /api/v1/users/profile`

**What it does**: Updates your own profile information (cannot change email or role)

**Authentication**: Required (Bearer token)

**Request Example**:
```json
{
  "username": "john_doe_updated",
  "full_name": "John D. Doe"
}
```

**Response Example**:
```json
{
  "id": "user-abc123...",
  "email": "john@company.com",
  "username": "john_doe_updated",
  "full_name": "John D. Doe",
  "role": "org_member",
  "organization_id": "org-456def...",
  "tenant_id": "tenant-789ghi...",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-10-05T16:45:00Z",
  "last_login": "2024-10-05T09:15:00Z"
}
```

**What you can update**:
- ✅ Username (if not taken)
- ✅ Full name
- ❌ Email (security - contact admin)
- ❌ Role (contact admin)
- ❌ Organization assignment (contact admin)

### 3. Get Detailed Profile Info 📊

**Endpoint**: `GET /api/v1/users/me`

**What it does**: Returns comprehensive profile information based on your role

**Authentication**: Required (Bearer token)

**Response varies by role**:

**For regular users**:
```json
{
  "id": "user-abc123...",
  "email": "john@company.com",
  "username": "johndoe",
  "full_name": "John Doe",
  "role": "org_member",
  "organization_id": "org-456def...",
  "tenant_id": null,
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "last_login": "2024-10-05T09:15:00Z"
}
```

**For super_admin users**:
```json
{
  "id": "user-super123...",
  "email": "admin@accunode.com", 
  "username": "superadmin",
  "full_name": "System Administrator",
  "role": "super_admin",
  "organization_id": null,
  "tenant_id": null,
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "last_login": "2024-10-05T08:00:00Z",
  "system_overview": {
    "total_tenants": 5,
    "total_organizations": 23,
    "total_users": 156,
    "active_users": 142
  },
  "tenants": [
    {
      "id": "tenant-123...",
      "name": "Enterprise Corp",
      "organizations": [
        {
          "id": "org-456...",
          "name": "Marketing Department",
          "user_count": 12
        }
      ]
    }
  ]
}
```

## User Management (Admin Functions)

### 4. List All Users 📋

**Endpoint**: `GET /api/v1/users`

**What it does**: Lists users (scope depends on your role)

**Min Role**: `org_admin`

**Query Parameters**:
| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `skip` | Integer | Records to skip (pagination) | `0` |
| `limit` | Integer | Records to return (max 100) | `20` |
| `role` | String | Filter by role | `org_member` |
| `is_active` | Boolean | Filter by active status | `true` |

**Request Example**:
```bash
GET /api/v1/users?skip=0&limit=20&role=org_member&is_active=true
Authorization: Bearer your_jwt_token
```

**Response Example**:
```json
{
  "users": [
    {
      "id": "user-abc123...",
      "email": "john@company.com",
      "username": "johndoe", 
      "full_name": "John Doe",
      "role": "org_member",
      "organization_id": "org-456def...",
      "tenant_id": "tenant-789ghi...",
      "is_active": true,
      "created_at": "2024-01-15T10:30:00Z",
      "last_login": "2024-10-05T09:15:00Z"
    }
  ],
  "total": 25,
  "skip": 0,
  "limit": 20,
  "filters_applied": {
    "role": "org_member",
    "is_active": true
  }
}
```

**Access Scope by Role**:
- **org_admin**: Users in their organization
- **tenant_admin**: Users in organizations within their tenant
- **super_admin**: All users in the system

### 5. Create New User 👥

**Endpoint**: `POST /api/v1/users`

**What it does**: Creates a new user (admin function)

**Min Role**: `org_admin`

**Request Example**:
```json
{
  "email": "newuser@company.com",
  "username": "newuser123",
  "full_name": "New User",
  "password": "SecurePass123!",
  "role": "org_member",
  "organization_id": "org-456def..."
}
```

**Response Example**:
```json
{
  "id": "user-new456...",
  "email": "newuser@company.com",
  "username": "newuser123",
  "full_name": "New User", 
  "role": "org_member",
  "organization_id": "org-456def...",
  "tenant_id": "tenant-789ghi...",
  "is_active": true,
  "created_at": "2024-10-05T17:00:00Z",
  "created_by": "user-admin123..."
}
```

**Role Assignment Rules**:
- **org_admin** can create: `user`, `org_member`
- **tenant_admin** can create: `user`, `org_member`, `org_admin`  
- **super_admin** can create: any role

### 6. Get User Details 🔍

**Endpoint**: `GET /api/v1/users/{user_id}`

**What it does**: Gets detailed information about a specific user

**Min Role**: `org_admin`

**Request Example**:
```bash
GET /api/v1/users/user-abc123...
Authorization: Bearer your_jwt_token
```

**Response Example**:
```json
{
  "id": "user-abc123...",
  "email": "john@company.com",
  "username": "johndoe",
  "full_name": "John Doe",
  "role": "org_member",
  "organization": {
    "id": "org-456def...",
    "name": "Tech Solutions Inc"
  },
  "tenant": {
    "id": "tenant-789ghi...", 
    "name": "Enterprise Corp"
  },
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-10-05T14:22:00Z",
  "last_login": "2024-10-05T09:15:00Z",
  "login_history": [
    {
      "timestamp": "2024-10-05T09:15:00Z",
      "ip_address": "192.168.1.100"
    }
  ]
}
```

### 7. Update User Information ✏️

**Endpoint**: `PUT /api/v1/users/{user_id}`

**What it does**: Updates another user's information (admin function)

**Min Role**: `org_admin`

**Request Example**:
```json
{
  "username": "updated_username",
  "full_name": "Updated Full Name",
  "is_active": false
}
```

**Response Example**:
```json
{
  "id": "user-abc123...",
  "email": "john@company.com",
  "username": "updated_username",
  "full_name": "Updated Full Name",
  "role": "org_member",
  "organization_id": "org-456def...",
  "tenant_id": "tenant-789ghi...",
  "is_active": false,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-10-05T17:15:00Z",
  "updated_by": "user-admin123..."
}
```

### 8. Change User Role 👑

**Endpoint**: `PUT /api/v1/users/{user_id}/role`

**What it does**: Changes a user's role (high-level admin function)

**Min Role**: `tenant_admin`

**Request Example**:
```json
{
  "new_role": "org_admin",
  "reason": "Promotion to department manager"
}
```

**Response Example**:
```json
{
  "success": true,
  "user_id": "user-abc123...",
  "previous_role": "org_member",
  "new_role": "org_admin",
  "changed_by": "user-admin123...",
  "changed_at": "2024-10-05T17:30:00Z",
  "reason": "Promotion to department manager"
}
```

**Role Change Rules**:
- **tenant_admin** can promote up to `org_admin`
- **super_admin** can assign any role
- Cannot demote users with equal or higher roles
- Role changes are logged for audit

### 9. Deactivate User 🚫

**Endpoint**: `POST /api/v1/users/{user_id}/deactivate`

**What it does**: Deactivates a user account (they cannot login)

**Min Role**: `org_admin`

**Request Example**:
```json
{
  "reason": "Employee left company"
}
```

**Response Example**:
```json
{
  "success": true,
  "message": "User deactivated successfully",
  "user_id": "user-abc123...",
  "deactivated_by": "user-admin123...",
  "deactivated_at": "2024-10-05T17:45:00Z",
  "reason": "Employee left company"
}
```

### 10. Activate User ✅

**Endpoint**: `POST /api/v1/users/{user_id}/activate`

**What it does**: Reactivates a previously deactivated user

**Min Role**: `org_admin`

**Request Example**:
```json
{
  "reason": "Employee returned from leave"
}
```

**Response Example**:
```json
{
  "success": true,
  "message": "User activated successfully", 
  "user_id": "user-abc123...",
  "activated_by": "user-admin123...",
  "activated_at": "2024-10-05T18:00:00Z",
  "reason": "Employee returned from leave"
}
```

### 11. Delete User 🗑️

**Endpoint**: `DELETE /api/v1/users/{user_id}`

**What it does**: Permanently deletes a user (cannot be undone)

**Min Role**: `tenant_admin`

**Request Example**:
```bash
DELETE /api/v1/users/user-abc123...
Authorization: Bearer your_jwt_token
```

**Response Example**:
```json
{
  "success": true,
  "message": "User deleted successfully",
  "user_id": "user-abc123...",
  "deleted_by": "user-admin123...",
  "deleted_at": "2024-10-05T18:15:00Z"
}
```

**⚠️ Warning**: Deletion is permanent and cannot be reversed!

## Access Control Matrix

### What Each Role Can Do

| Action | user | org_member | org_admin | tenant_admin | super_admin |
|--------|------|------------|-----------|--------------|-------------|
| View own profile | ✅ | ✅ | ✅ | ✅ | ✅ |
| Update own profile | ✅ | ✅ | ✅ | ✅ | ✅ |
| List users | ❌ | ❌ | ✅ Org only | ✅ Tenant | ✅ All |
| Create users | ❌ | ❌ | ✅ Lower roles | ✅ Lower roles | ✅ All |
| View user details | ❌ | ❌ | ✅ Org only | ✅ Tenant | ✅ All |
| Update users | ❌ | ❌ | ✅ Org only | ✅ Tenant | ✅ All |
| Change roles | ❌ | ❌ | ❌ | ✅ Up to org_admin | ✅ All |
| Activate/Deactivate | ❌ | ❌ | ✅ Org only | ✅ Tenant | ✅ All |
| Delete users | ❌ | ❌ | ❌ | ✅ Tenant | ✅ All |

### Role Promotion Paths

```
user → org_member → org_admin → tenant_admin → super_admin
  ↑         ↑           ↑            ↑            ↑
Granted  Joins Org   Promoted   Tenant Access  System Admin
```

## Common Error Messages

| Error Code | Error Message | What It Means | What To Do |
|------------|---------------|---------------|------------|
| **403** | "Insufficient permissions" | Your role is too low | Contact admin for role upgrade |
| **403** | "Cannot modify user outside organization" | User not in your scope | Check user's organization |
| **400** | "Username already taken" | Username exists | Choose different username |
| **400** | "Cannot promote user to higher role than yourself" | Role hierarchy violation | Use higher-role admin |
| **400** | "Cannot deactivate user with equal or higher role" | Role protection | Use higher-role admin |
| **404** | "User not found" | Invalid user ID | Check user exists and you have access |
| **422** | "Invalid email format" | Email format error | Use valid email format |

## Integration Examples

### Using with JavaScript
```javascript
class UsersAPI {
  constructor(baseUrl, token) {
    this.baseUrl = baseUrl;
    this.token = token;
  }

  async getMyProfile() {
    const response = await fetch(`${this.baseUrl}/api/v1/users/profile`, {
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      }
    });
    return response.json();
  }

  async updateMyProfile(updates) {
    const response = await fetch(`${this.baseUrl}/api/v1/users/profile`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(updates)
    });
    return response.json();
  }

  async listUsers(filters = {}) {
    const params = new URLSearchParams(filters);
    const response = await fetch(
      `${this.baseUrl}/api/v1/users?${params}`,
      {
        headers: {
          'Authorization': `Bearer ${this.token}`,
          'Content-Type': 'application/json'
        }
      }
    );
    return response.json();
  }

  async createUser(userData) {
    const response = await fetch(`${this.baseUrl}/api/v1/users`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(userData)
    });
    return response.json();
  }

  async changeUserRole(userId, newRole, reason) {
    const response = await fetch(
      `${this.baseUrl}/api/v1/users/${userId}/role`,
      {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${this.token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ new_role: newRole, reason })
      }
    );
    return response.json();
  }
}

// Usage examples
const usersAPI = new UsersAPI('http://localhost:8000', 'your_jwt_token');

// Get my profile
const profile = await usersAPI.getMyProfile();
console.log(`Hello, ${profile.full_name}!`);

// Update my profile
await usersAPI.updateMyProfile({
  full_name: "John Updated Doe"
});

// List organization members (if admin)
const users = await usersAPI.listUsers({ role: 'org_member' });
console.log(`Found ${users.total} organization members`);
```

### Using with Python
```python
import requests

class AccuNodeUsers:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def get_my_profile(self):
        response = requests.get(
            f"{self.base_url}/api/v1/users/profile",
            headers=self.headers
        )
        return response.json()
    
    def update_my_profile(self, **updates):
        response = requests.put(
            f"{self.base_url}/api/v1/users/profile",
            headers=self.headers,
            json=updates
        )
        return response.json()
    
    def list_users(self, **filters):
        response = requests.get(
            f"{self.base_url}/api/v1/users",
            headers=self.headers,
            params=filters
        )
        return response.json()
    
    def create_user(self, email, username, full_name, password, 
                   role='org_member', organization_id=None):
        data = {
            'email': email,
            'username': username, 
            'full_name': full_name,
            'password': password,
            'role': role
        }
        if organization_id:
            data['organization_id'] = organization_id
            
        response = requests.post(
            f"{self.base_url}/api/v1/users",
            headers=self.headers,
            json=data
        )
        return response.json()
    
    def change_user_role(self, user_id, new_role, reason=None):
        data = {'new_role': new_role}
        if reason:
            data['reason'] = reason
            
        response = requests.put(
            f"{self.base_url}/api/v1/users/{user_id}/role",
            headers=self.headers,
            json=data
        )
        return response.json()
    
    def deactivate_user(self, user_id, reason=None):
        data = {'reason': reason} if reason else {}
        response = requests.post(
            f"{self.base_url}/api/v1/users/{user_id}/deactivate",
            headers=self.headers,
            json=data
        )
        return response.json()

# Usage example
users_api = AccuNodeUsers('http://localhost:8000', 'your_jwt_token')

# Get my profile
profile = users_api.get_my_profile()
print(f"Current role: {profile['role']}")

# Create new user (if admin)
new_user = users_api.create_user(
    email="newteam@company.com",
    username="newteam",
    full_name="New Team Member", 
    password="SecurePass123!",
    role="org_member"
)
print(f"Created user: {new_user['id']}")

# List organization users
users = users_api.list_users(is_active=True)
print(f"Active users: {users['total']}")
```

## Testing

### Test with curl
```bash
# Get my profile
curl -X GET http://localhost:8000/api/v1/users/profile \
  -H "Authorization: Bearer YOUR_TOKEN"

# Update my profile  
curl -X PUT http://localhost:8000/api/v1/users/profile \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Updated Name"}'

# List users (admin only)
curl -X GET http://localhost:8000/api/v1/users?limit=10 \
  -H "Authorization: Bearer YOUR_TOKEN"

# Create user (admin only)
curl -X POST http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"testuser","full_name":"Test User","password":"SecurePass123!","role":"org_member"}'
```

The Users API provides comprehensive user management with role-based access control, ensuring secure and appropriate access to user data and administrative functions.
