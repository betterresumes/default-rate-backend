# 🎯 **Financial Risk API - Role-Based Access Implementation**

## 📋 **Data Access Strategy**

### **Global Role Hierarchy:**
1. **`super_admin`** → Access ALL data across ALL tenants/organizations  
2. **`tenant_admin`** → Access data within their tenant only
3. **`user` (with organization)** → Access data within their organization only

### **Organization Role (within organization):**
- **`admin`** → Full access within organization
- **`member`** → Standard access within organization

### **Data Isolation Rules:**
- **Companies**: Tied to organization_id + created_by (user_id)
- **Predictions**: Tied to organization_id + created_by (user_id) + company_id
- **Super Admins**: See everything globally
- **Tenant Admins**: See all data within their tenant
- **Regular Users**: See only their organization's data

---

## 🔧 **Implementation Approach**

### **Company Creation:**
1. **Can create company first** → Then add predictions to that company
2. **Can create prediction with new company** → System auto-creates company if needed
3. **Organization Assignment**: Automatically assigns to user's organization
4. **Access Control**: Only members+ can create companies

### **Prediction Creation:**
1. **Requires Valid Company**: Must reference existing company in user's scope
2. **Auto-tracking**: Saves user_id, organization_id, company_id
3. **Scope Validation**: Users can only predict for companies in their scope
4. **Duplicate Prevention**: Prevents duplicate predictions for same company/year/quarter

---

## 🚀 **API Endpoints Implemented**

### 1. **`POST /api/v1/companies`** - Create Company
- **Access**: Members+ with organization
- **Tracks**: organization_id, created_by (user_id)
- **Validation**: Symbol uniqueness within scope

### 2. **`GET /api/v1/companies`** - List Companies  
- **Access**: Members+ with organization
- **Filtering**: By user's organization scope
- **Pagination**: page, limit, search, sector filters

### 3. **`POST /api/v1/predictions/annual`** - Annual Prediction
- **Access**: Members+ with organization  
- **Tracks**: organization_id, created_by (user_id), company_id
- **Validation**: Company exists in user's scope

### 4. **`POST /api/v1/predictions/quarterly`** - Quarterly Prediction
- **Access**: Members+ with organization
- **Tracks**: organization_id, created_by (user_id), company_id  
- **Validation**: Company exists in user's scope, valid quarter

---

## 📊 **Sample Data Flow**

### **User: Regular Member**
```
Organization: HDFC Bank (org_id: 123)
User: john@hdfc.com (user_id: 456)
Access: Can only see/create data for HDFC Bank organization
```

### **User: Super Admin**  
```
Organization: N/A
User: admin@system.com (user_id: 789)
Access: Can see/create data for ALL organizations
```

### **User: Tenant Admin**
```
Tenant: Banking Corp (tenant_id: 111)  
Organizations: HDFC, ICICI, SBI (all under Banking Corp)
User: admin@banking.com (user_id: 321)
Access: Can see/create data for all orgs in Banking Corp tenant
```

---

## 🔒 **Security Features**

1. **Organization Isolation**: Users can't access other organizations' data
2. **Role Validation**: Permission checks before every operation
3. **Data Tracking**: All records track creator and organization
4. **Scope Enforcement**: API responses filtered by user scope
5. **Duplicate Prevention**: Prevents data conflicts within scope
