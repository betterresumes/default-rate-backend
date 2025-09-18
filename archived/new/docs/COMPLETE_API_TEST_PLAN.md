# Complete API Testing Plan

## 🎯 API Endpoints Overview

### 1. 🔐 Authentication APIs (`/api/v1/auth`)
- [x] `GET /api/v1/auth/status` - Check auth system status
- [x] `POST /api/v1/auth/register-simple` - Register new user  
- [x] `POST /api/v1/auth/login` - User login
- [x] `GET /api/v1/auth/me` - Get current user info

### 2. 🏢 Organization APIs (`/api/v1/organizations`)

#### 📋 Core Organization Management
- [x] `POST /api/v1/organizations/` - Create New Organization
- [x] `GET /api/v1/organizations/` - List Organizations  
- [x] `GET /api/v1/organizations/{id}` - Get Organization Details
- [ ] `PUT /api/v1/organizations/{id}` - Update Organization
- [ ] `DELETE /api/v1/organizations/{id}` - Delete Organization

#### 👥 Organization User Management
- [x] `GET /api/v1/organizations/{id}/users` - List Organization Users
- [ ] `PUT /api/v1/organizations/{id}/users/{user_id}/role` - Update User Organization Role
- [ ] `DELETE /api/v1/organizations/{id}/users/{user_id}` - Remove User from Organization

#### 📧 Organization Invitation System
- [ ] `POST /api/v1/organizations/{id}/invitations` - Invite User to Organization
- [ ] `GET /api/v1/organizations/{id}/invitations` - List Organization Invitations
- [ ] `POST /api/v1/organizations/invitations/{token}/accept` - Accept Organization Invitation
- [ ] `DELETE /api/v1/organizations/invitations/{invitation_id}` - Cancel Organization Invitation

### 3. 🏢 Company APIs (`/api/v1/companies`)
- [ ] `POST /api/v1/companies/` - Create company
- [ ] `GET /api/v1/companies/` - List companies
- [ ] `GET /api/v1/companies/{id}` - Get company details
- [ ] `PUT /api/v1/companies/{id}` - Update company
- [ ] `DELETE /api/v1/companies/{id}` - Delete company

### 4. 📊 Prediction APIs (`/api/v1/predictions`)
- [ ] `POST /api/v1/predictions/` - Create prediction
- [ ] `GET /api/v1/predictions/` - List predictions
- [ ] `GET /api/v1/predictions/{id}` - Get prediction details
- [ ] `POST /api/v1/predictions/bulk` - Bulk prediction upload
- [ ] `GET /api/v1/predictions/bulk/{id}/status` - Check bulk upload status

### 5. ⚡ System APIs
- [x] `GET /` - Root endpoint
- [ ] `GET /health` - Health check
- [ ] `GET /health/workers` - Worker diagnostics

## 🧪 Testing Progress
- ✅ **Authentication**: 4/4 endpoints tested and working
- 🔄 **Organizations**: 4/12 endpoints tested (core CRUD + users working)
  - ✅ Core Management: 3/5 (create, list, detail working)
  - ✅ User Management: 1/3 (list users working)  
  - ❌ Invitation System: 0/4 (not tested yet)
- ❌ **Companies**: 0/5 endpoints tested
- ❌ **Predictions**: 0/5 endpoints tested  
- ❌ **System**: 1/3 endpoints tested

## 🔑 Test Credentials
- **User**: testuser@example.com / testpass123
- **Token**: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiZDgxMDRhYjktODhlNS00NDE1LWExZmYtZjU1ODA3MWUyOGRmIiwiZW1haWwiOiJ0ZXN0dXNlckBleGFtcGxlLmNvbSIsImV4cCI6MTc1ODIzMTE5MH0.3HhlkN99zk4nhpXM80GZcgEIYhVl1HX1KjFI-8ooscE
- **Organization**: Test Company 2024 (ID: 016a4fbd-8993-4350-b709-e9a0c1e1af43)

## 📋 Testing Order
1. ✅ Authentication system (complete)
2. 🔄 Organization management (in progress)
3. 📋 Company management
4. 📊 Prediction system
5. ⚡ System health endpoints
