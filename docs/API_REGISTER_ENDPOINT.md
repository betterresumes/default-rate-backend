# 🔐 User Registration API Endpoint

## Overview
The user registration endpoint allows new users to create accounts with automatic role assignment and enhanced security features.

## Endpoint Details

### **POST** `/api/v1/auth/register`

**Description:** Register a new user account with automatic security role enforcement.

---

## 📋 Request Specification

### **Headers**
```http
Content-Type: application/json
```

### **Request Body Schema**
```json
{
  "email": "string (required)",
  "password": "string (required, min 8 chars)",
  "full_name": "string (optional)",
  "username": "string (optional)",
  "first_name": "string (optional)",
  "last_name": "string (optional)"
}
```

### **Field Descriptions**

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `email` | string | ✅ Yes | Valid email address | Must be valid email format |
| `password` | string | ✅ Yes | User password | Min 8 chars, must contain letter & digit |
| `full_name` | string | ❌ No | Complete user name | Auto-generated from first/last name if provided |
| `username` | string | ❌ No | Unique username | Auto-generated from email if not provided |
| `first_name` | string | ❌ No | User's first name | Used to build full_name if provided |
| `last_name` | string | ❌ No | User's last name | Used to build full_name if provided |

### **Password Requirements**
- Minimum 8 characters
- Must contain at least one letter
- Must contain at least one digit

---

## 📤 Response Specification

### **Success Response (201 Created)**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "username": "user_123",
  "full_name": "John Doe",
  "role": "user",
  "organization_id": null,
  "tenant_id": null,
  "is_active": true,
  "created_at": "2025-10-03T10:30:00Z",
  "last_login": null
}
```

### **Response Field Descriptions**

| Field | Type | Description |
|-------|------|-------------|
| `id` | string (UUID) | Unique user identifier |
| `email` | string | Registered email address |
| `username` | string | Generated or provided username |
| `full_name` | string | User's display name |
| `role` | string | Always "user" for public registrations |
| `organization_id` | string/null | Organization membership (null for personal accounts) |
| `tenant_id` | string/null | Tenant association (null for personal accounts) |
| `is_active` | boolean | Account activation status (always true) |
| `created_at` | string (ISO) | Account creation timestamp |
| `last_login` | string/null | Last login timestamp (null for new accounts) |

---

## 🚨 Error Responses

### **400 Bad Request - Email Already Exists**
```json
{
  "detail": "Email already registered"
}
```

### **400 Bad Request - Username Taken**
```json
{
  "detail": "Username 'johndoe' is already taken. Please choose a different username."
}
```

### **400 Bad Request - Username Generation Failed**
```json
{
  "detail": "Unable to generate a unique username from email 'user@example.com'. Please provide a custom username."
}
```

### **400 Bad Request - Invalid Data**
```json
{
  "detail": "Invalid data provided. Please check your input and try again."
}
```

### **422 Validation Error**
```json
{
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "Password must be at least 8 characters long",
      "type": "value_error"
    }
  ]
}
```

### **429 Too Many Requests (Rate Limited)**
```json
{
  "detail": "Rate limit exceeded. Please try again later."
}
```

### **500 Internal Server Error**
```json
{
  "detail": "Database error: [error details]..."
}
```

---

## 🔧 Business Logic

### **Username Generation**
1. If `username` provided → validate uniqueness
2. If `username` not provided → auto-generate from email local part
3. If conflict → append incremental numbers (`username_1`, `username_2`, etc.)
4. Sanitize usernames (remove special characters, replace with underscores)
5. Minimum username length: 2 characters

### **Name Handling**
1. If `full_name` provided → use as-is
2. If `first_name`/`last_name` provided → combine as `"first last"`
3. Trim whitespace automatically

### **Security Features**
- 🔒 **Role Enforcement**: All public registrations get `"user"` role only
- 🚫 **No Privilege Escalation**: Cannot register with admin roles
- 🔐 **Password Hashing**: BCrypt with 5 rounds
- ⚡ **Rate Limiting**: Auth-level rate limiting applied

---

## 📝 Example Requests

### **Minimal Registration**
```bash
curl -X POST "https://api.example.com/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "securepass123"
  }'
```

### **Complete Registration**
```bash
curl -X POST "https://api.example.com/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "securepass123",
    "username": "johndoe",
    "full_name": "John Doe",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

---

## 🔄 Frontend Integration

### **JavaScript Example**
```javascript
async function registerUser(userData) {
  try {
    const response = await fetch('/api/v1/auth/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email: userData.email,
        password: userData.password,
        full_name: userData.fullName,
        username: userData.username || null,
        first_name: userData.firstName || null,
        last_name: userData.lastName || null
      })
    });

    // Handle rate limiting
    if (response.status === 429) {
      throw new Error("Too many attempts. Please wait and try again.");
    }

    if (!response.ok) {
      const error = await response.json();
      
      // Handle specific errors
      if (error.detail?.includes("Email already registered")) {
        throw new Error("Email already registered. Please try logging in.");
      }
      if (error.detail?.includes("Username") && error.detail?.includes("taken")) {
        throw new Error("Username taken. Please choose another.");
      }
      
      throw new Error(error.detail || "Registration failed");
    }

    const newUser = await response.json();
    console.log("Registration successful:", newUser);
    return newUser;
    
  } catch (error) {
    console.error("Registration error:", error);
    throw error;
  }
}
```

### **React Hook Example**
```javascript
import { useState } from 'react';

export function useRegister() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const register = async (userData) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/v1/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userData)
      });

      if (response.status === 429) {
        throw new Error("Too many attempts. Please wait and try again.");
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Registration failed");
      }

      const user = await response.json();
      return user;
      
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { register, loading, error };
}
```

---

## ⚡ Rate Limiting

### **Limits Applied**
- **Auth Rate Limit**: Applied to this endpoint
- **Specific Limits**: Configured in rate limiting middleware
- **Headers**: Rate limit info returned in response headers

### **Rate Limit Headers**
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1696339200
```

---

## 🔍 Testing

### **Valid Test Cases**
```bash
# Test 1: Minimal valid registration
{
  "email": "test@example.com",
  "password": "password123"
}

# Test 2: Complete registration
{
  "email": "john@example.com", 
  "password": "securepass123",
  "username": "johndoe",
  "full_name": "John Doe"
}

# Test 3: Auto-username generation
{
  "email": "jane.smith@company.com",
  "password": "mypassword123"
}
# Expected username: "jane_smith" or "jane_smith_1" if conflicts
```

### **Invalid Test Cases**
```bash
# Test 1: Duplicate email
{
  "email": "existing@example.com",
  "password": "password123"
}
# Expected: 400 "Email already registered"

# Test 2: Weak password
{
  "email": "test@example.com",
  "password": "weak"
}
# Expected: 422 Validation error

# Test 3: Invalid email
{
  "email": "not-an-email",
  "password": "password123"
}
# Expected: 422 Validation error
```

---

## 📚 Related Endpoints

- **POST** `/api/v1/auth/login` - User authentication
- **POST** `/api/v1/auth/refresh` - Token refresh
- **POST** `/api/v1/auth/change-password` - Password update
- **POST** `/api/v1/auth/join` - Organization joining

---

## 🔒 Security Notes

1. **Role Security**: Public registrations are restricted to `"user"` role only
2. **Password Security**: BCrypt hashing with configurable rounds
3. **Input Validation**: Comprehensive validation on all fields  
4. **Rate Limiting**: Protection against abuse
5. **SQL Injection**: Protected via ORM and parameterized queries
6. **Duplicate Prevention**: Email and username uniqueness enforced

---

## 📊 Status Codes Summary

| Code | Description | Scenario |
|------|-------------|----------|
| 201 | Created | Successful registration |
| 400 | Bad Request | Duplicate email/username, invalid data |
| 422 | Validation Error | Invalid input format |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Error | Database or server error |

---

*Last Updated: October 3, 2025*
*API Version: v1*
