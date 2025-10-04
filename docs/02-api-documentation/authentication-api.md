# Authentication API

This document explains how to register, login, and manage user authentication with AccuNode's API.

## Authentication Overview

AccuNode uses **JWT (JSON Web Tokens)** for authentication. Here's how it works:

1. **Register** → Create a new account
2. **Login** → Get a security token
3. **Use Token** → Include token in all API requests
4. **Token Expires** → Login again after 60 minutes

## Base Information

- **Base URL**: `/api/v1/auth`
- **Token Expiration**: 60 minutes
- **Rate Limits**: See table below

| Endpoint | Limit | Time Window |
|----------|-------|-------------|
| Register | 10 requests | 10 minutes |
| Login | 20 requests | 5 minutes |  
| Change Password | 5 requests | 15 minutes |

## API Endpoints

### 1. User Registration 📝

**Endpoint**: `POST /api/v1/auth/register`

**What it does**: Creates a new user account (always gets "user" role for security)

**Request Example**:
```json
{
  "email": "john@company.com",
  "password": "mypassword123", 
  "full_name": "John Smith",
  "username": "johnsmith"
}
```

**Response Example**:
```json
{
  "id": "abc123...",
  "email": "john@company.com",
  "username": "johnsmith", 
  "full_name": "John Smith",
  "role": "user",
  "is_active": true,
  "created_at": "2024-10-05T10:30:00Z"
}
```

**Password Requirements**:
- ✅ At least 8 characters
- ✅ At least 1 letter  
- ✅ At least 1 number

**What happens if username is missing?**
- System creates one from your email
- `john.doe@company.com` becomes `john_doe`
- If taken, adds number: `john_doe_1`, `john_doe_2`, etc.

### 2. User Login 🔐

**Endpoint**: `POST /api/v1/auth/login`

**What it does**: Authenticates user and returns a security token

**Request Example**:
```json
{
  "email": "john@company.com",
  "password": "mypassword123"
}
```

**Response Example**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "abc123...",
    "email": "john@company.com",
    "role": "user",
    "organization_id": null
  }
}
```

**How to use the token**:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### 3. Change Password 🔒

**Endpoint**: `POST /api/v1/auth/change-password`

**Authentication Required**: Yes (include Bearer token)

**Request Example**:
```json
{
  "current_password": "myoldpassword123",
  "new_password": "mynewpassword456"
}
```

**Response Example**:
```json
{
  "success": true,
  "message": "Password changed successfully"
}
```

### 4. Join Organization 🏢

**Endpoint**: `POST /api/v1/auth/join-organization`

**Authentication Required**: Yes (include Bearer token)

**What it does**: Adds user to an organization using an invitation token

**Request Example**:
```json
{
  "join_token": "ABC123XYZ789"
}
```

**Response Example**:
```json
{
  "success": true,
  "message": "Successfully joined Tech Solutions Inc",
  "organization_id": "org123...",
  "organization_name": "Tech Solutions Inc", 
  "user_role": "org_member"
}
```

**How to get a join token**:
- Organization admin creates it in AccuNode
- They share the token with you (email, Slack, etc.)
- You enter it using this API

## Security Features

### Token Security
- **Algorithm**: HS256 (industry standard)
- **Expiration**: 60 minutes (configurable)
- **Content**: User ID, role, organization info
- **Validation**: System checks if user still exists and is active

### Password Security  
- **Hashing**: Bcrypt with salt (impossible to reverse)
- **Storage**: Only encrypted version is stored
- **Validation**: Real-time strength checking

### Rate Limiting Protection
- **Login**: Prevents brute force attacks
- **Registration**: Prevents spam accounts
- **Password Change**: Prevents automated attacks

## Common Error Messages

| Error Code | Error Message | What It Means | What To Do |
|------------|---------------|---------------|------------|
| **400** | "Email already registered" | That email is taken | Use a different email |
| **400** | "Username already taken" | Username is not available | Choose different username or leave blank |
| **400** | "Password must be at least 8 characters" | Password too short | Use longer password |
| **400** | "Password must contain at least one letter" | Password needs letters | Add letters to password |
| **400** | "Password must contain at least one number" | Password needs numbers | Add numbers to password |
| **401** | "Could not validate credentials" | Wrong email/password | Check email and password |
| **401** | "User account is disabled" | Account was deactivated | Contact administrator |
| **429** | "Too many requests" | Rate limit hit | Wait and try again |

## Integration Examples

### Using with JavaScript
```javascript
// Register new user
async function registerUser(email, password, fullName) {
  const response = await fetch('/api/v1/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      email, 
      password, 
      full_name: fullName 
    })
  });
  return response.json();
}

// Login user
async function loginUser(email, password) {
  const response = await fetch('/api/v1/auth/login', {
    method: 'POST', 
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  
  const data = await response.json();
  if (data.access_token) {
    localStorage.setItem('token', data.access_token);
  }
  return data;
}

// Make authenticated request
async function makeAuthenticatedRequest(url) {
  const token = localStorage.getItem('token');
  const response = await fetch(url, {
    headers: { 
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  return response.json();
}
```

### Using with Python
```python
import requests

class AccuNodeAuth:
    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None
    
    def register(self, email, password, full_name):
        response = requests.post(
            f"{self.base_url}/api/v1/auth/register",
            json={
                "email": email,
                "password": password, 
                "full_name": full_name
            }
        )
        return response.json()
    
    def login(self, email, password):
        response = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"email": email, "password": password}
        )
        
        if response.status_code == 200:
            data = response.json()
            self.token = data["access_token"]
            return data
        return response.json()
    
    def get_headers(self):
        return {"Authorization": f"Bearer {self.token}"}

# Usage example
auth = AccuNodeAuth("http://localhost:8000")
result = auth.login("user@example.com", "password123")
headers = auth.get_headers()
```

## Testing

### Test with curl
```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123","full_name":"Test User"}'

# Login  
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123"}'

# Use token (replace YOUR_TOKEN with actual token)
curl -X GET http://localhost:8000/api/v1/users/profile \
  -H "Authorization: Bearer YOUR_TOKEN"
```

This authentication system provides secure, scalable user management for AccuNode with industry-standard security practices.
