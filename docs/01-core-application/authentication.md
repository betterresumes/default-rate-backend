# Authentication System

This document explains how AccuNode handles user login, permissions, and data access in simple terms with visual diagrams.

## What is Authentication?

Authentication is how AccuNode knows who you are and what you're allowed to do. It's like having an ID card that shows:
- Your identity (who you are)
- Your role (what you can access)
- Your organization (which data you can see)

## How AccuNode Authentication Works

### Step-by-Step Login Process

```
1. User Registration
   ↓
2. User Login (Email + Password)
   ↓
3. System Creates Security Token
   ↓
4. User Uses Token for All Requests
   ↓
5. System Checks Permissions
```

### Authentication Flow Diagram

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Register  │───▶│    Login    │───▶│ Get Token   │
│             │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
                                              │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Make Request│◀───│Check Permissions│◀─│ Use Token   │
│             │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
```

## User Roles and Permissions

AccuNode has **5 levels of users**, each with different permissions:

### User Role Hierarchy (5 Levels)

```
┌─────────────────┐
│   Super Admin   │ ◀── Can manage everything in the system
└─────────────────┘
          │
┌─────────────────┐
│  Tenant Admin   │ ◀── Can manage organizations within their tenant
└─────────────────┘
          │
┌─────────────────┐
│  Org Admin      │ ◀── Can manage their organization
└─────────────────┘
          │
┌─────────────────┐
│  Org Member     │ ◀── Can view organization data
└─────────────────┘
          │
┌─────────────────┐
│     User        │ ◀── Can only see their own data
└─────────────────┘
```

### What Each Role Can Do

| Role | What They Can Do | Data Access |
|------|------------------|-------------|
| **User** | • View their own predictions<br/>• Create personal companies<br/>• Change their profile | Only their own data |
| **Org Member** | • Everything a User can do<br/>• View organization predictions<br/>• See company data shared in org | Personal + Organization data |
| **Org Admin** | • Everything an Org Member can do<br/>• Invite new members<br/>• Manage organization settings<br/>• Remove members | Personal + Organization management |
| **Tenant Admin** | • Everything an Org Admin can do<br/>• Create new organizations<br/>• Manage multiple organizations<br/>• User management across tenant | Personal + Multiple organizations |
| **Super Admin** | • Everything a Tenant Admin can do<br/>• System-wide administration<br/>• Manage all tenants<br/>• Global system settings | All system data |

### Permission Inheritance

```
Super Admin ──┐
              │ (inherits all permissions from lower roles)
Tenant Admin ─┤
              │
Org Admin ────┤
              │
Org Member ───┤
              │
User ─────────┘
```

## How Organizations Work

### Organization Structure

```
┌─────────────────────────────────────┐
│            TENANT                   │
│  ┌─────────────┐  ┌─────────────┐  │
│  │Organization │  │Organization │  │
│  │     A       │  │     B       │  │
│  │             │  │             │  │
│  │ • Users     │  │ • Users     │  │
│  │ • Companies │  │ • Companies │  │
│  │ • Data      │  │ • Data      │  │
│  └─────────────┘  └─────────────┘  │
└─────────────────────────────────────┘
```

### Joining an Organization

**Method 1: Invitation Token**
```
1. Org Admin creates invitation token
   ↓
2. They share the token with new user
   ↓
3. User enters token in AccuNode
   ↓
4. System adds user to organization
```

**Method 2: Email Whitelist**
```
1. Org Admin adds email to whitelist
   ↓
2. User with that email can join automatically
   ↓
3. System checks email against whitelist
   ↓
4. Approved users get organization access
```

## Security Tokens

### How Security Tokens Work

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  User Login │───▶│AccuNode API │───▶│Security Token│
│             │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────┐
│           Token Contains:                       │
│  • User ID                                      │
│  • Expiration Time (60 minutes)                │
│  • Digital Signature (for security)            │
└─────────────────────────────────────────────────┘
```

### Token Security Features

- **Expiration**: Tokens automatically expire after 60 minutes
- **Digital Signature**: Prevents token tampering
- **User Verification**: System checks if user is still active
- **Secure Algorithm**: Uses industry-standard HS256 encryption

## Password Security

### Password Requirements

Your password must have:
- ✅ **At least 8 characters**
- ✅ **At least 1 letter** (A-Z or a-z)
- ✅ **At least 1 number** (0-9)

**Examples:**
- ❌ `password` (no number)
- ❌ `12345678` (no letter)
- ❌ `pass123` (too short)
- ✅ `password123` (meets all requirements)
- ✅ `MySecure2024` (meets all requirements)

### How Passwords Are Protected

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Your Password│───▶│   Bcrypt    │───▶│ Secure Hash │
│  "pass123"  │    │ Encryption  │    │ (stored)    │
└─────────────┘    └─────────────┘    └─────────────┘
```

**Security Features:**
- Passwords are never stored in plain text
- Uses advanced Bcrypt encryption
- Each password gets a unique "salt" for extra security
- Even AccuNode staff cannot see your actual password

## Anti-Abuse Protection

### Rate Limiting (Speed Limits)

AccuNode prevents system abuse by limiting how many requests you can make:

| Action | Limit | Time Window |
|--------|-------|-------------|
| **Login Attempts** | 20 requests | 5 minutes |
| **User Registration** | 10 requests | 10 minutes |
| **Password Changes** | 5 requests | 15 minutes |
| **General API Use** | 1000 requests | 1 hour |

**What happens if you exceed limits?**
- You'll get a "Too Many Requests" error
- You need to wait before trying again
- This protects against hackers and system overload

### Additional Security Features

**Input Validation:**
- ✅ Email addresses must be valid format
- ✅ Usernames can only contain letters, numbers, underscore, hyphen
- ✅ All data is checked for malicious content
- ✅ System prevents database injection attacks

**Automatic Username Creation:**
- If you don't provide a username, we create one from your email
- Example: `john.doe@company.com` becomes username `john_doe`
- If that username exists, we add a number: `john_doe_1`, `john_doe_2`, etc.

**Security Headers:**
- All web requests include security headers
- Protects against cross-site attacks
- Ensures secure data transmission

## Database Tables

### User Table
| Field | Type | Description |
|-------|------|-------------|
| **id** | UUID | Unique user identifier |
| **email** | String | User's email (unique) |
| **username** | String | Display name (unique) |
| **full_name** | String | User's full name |
| **hashed_password** | String | Encrypted password |
| **role** | String | User role (user, org_member, etc.) |
| **organization_id** | UUID | Which organization they belong to |
| **tenant_id** | UUID | Which tenant they belong to |
| **is_active** | Boolean | Account enabled/disabled |
| **created_at** | DateTime | When account was created |
| **last_login** | DateTime | Last login time |

### Organization Table  
| Field | Type | Description |
|-------|------|-------------|
| **id** | UUID | Unique organization identifier |
| **name** | String | Organization name |
| **join_token** | String | Token for inviting users |
| **join_enabled** | Boolean | Whether new users can join |
| **max_users** | Number | Maximum number of users allowed |
| **is_active** | Boolean | Organization enabled/disabled |

### Organization Whitelist Table
| Field | Type | Description |
|-------|------|-------------|
| **id** | UUID | Unique identifier |
| **organization_id** | UUID | Which organization |
| **email** | String | Approved email address |
| **status** | String | active/inactive |
| **added_by** | UUID | Who added this email |

## Common Error Messages

When something goes wrong, you'll see helpful error messages:

| Error | What It Means | What To Do |
|-------|---------------|------------|
| **"Invalid credentials"** | Wrong email or password | Check your email and password |
| **"Token expired"** | Your login session ended | Log in again |
| **"Account disabled"** | Your account was deactivated | Contact your administrator |
| **"Too many requests"** | You're making requests too fast | Wait a few minutes and try again |
| **"Invalid token"** | Your session token was corrupted | Log out and log in again |

This authentication system keeps your data secure while making it easy to collaborate with your team through organizations and role-based permissions.
