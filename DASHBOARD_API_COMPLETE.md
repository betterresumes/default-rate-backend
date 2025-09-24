# Dashboard API - Complete Reference

## Overview
The `/predictions/dashboard` endpoint provides comprehensive dashboard analytics with user-scoped data and optional platform statistics. Recently updated with prediction breakdowns and cleaner platform metrics.

---

## Endpoint Details

### **POST** `/api/v1/predictions/dashboard`

**Authentication:** Required (JWT Bearer Token)

**Content-Type:** `application/json`

---

## Request Structure

### Request Body
```json
{
    "include_platform_stats": true,  // Optional: include platform statistics
    "organization_filter": null,     // Optional: organization filter 
    "custom_scope": null            // Optional: custom scope (reserved for future use)
}
```

### Request Parameters
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `include_platform_stats` | boolean | No | false | Whether to include platform-wide statistics |
| `organization_filter` | string | No | null | Organization filter (reserved) |
| `custom_scope` | string | No | null | Custom scope (reserved) |

---

## Response Structure

The response contains two main objects:
- `user_dashboard`: User's scoped dashboard data
- `platform_statistics`: Platform-wide statistics (if requested)
- `scope`: The determined scope for the user

---

## Response Examples

### 1. Personal User Dashboard (like Pranit)

**Request:**
```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"include_platform_stats": true}' \
  "http://localhost:8000/api/v1/predictions/dashboard"
```

**Response:**
```json
{
    "user_dashboard": {
        "scope": "personal",
        "user_name": "Pranit",
        "organization_name": "Personal Data",
        "total_companies": 18,
        "total_predictions": 400,
        "annual_predictions": 350,          // NEW: Count of annual predictions
        "quarterly_predictions": 50,        // NEW: Count of quarterly predictions  
        "average_default_rate": 0.0202,
        "high_risk_companies": 0,
        "sectors_covered": 8,
        "data_scope": "Personal data only"
    },
    "scope": "personal",
    "platform_statistics": {
        "total_companies": 112,
        "total_predictions": 2882,
        "annual_predictions": 2728,         // Platform annual predictions
        "quarterly_predictions": 154,       // Platform quarterly predictions
        "average_default_rate": 0.0172,
        "high_risk_companies": 0,
        "sectors_covered": 15
        // REMOVED: total_users, total_organizations, total_tenants
    }
}
```

---

### 2. Organization User Dashboard

**Response:**
```json
{
    "user_dashboard": {
        "scope": "organization",
        "user_name": "John Doe",
        "organization_name": "Tech Innovations Inc",
        "total_companies": 45,
        "total_predictions": 1200,
        "annual_predictions": 980,          // NEW: Organization annual predictions
        "quarterly_predictions": 220,       // NEW: Organization quarterly predictions
        "average_default_rate": 0.0189,
        "high_risk_companies": 2,
        "sectors_covered": 12,
        "data_scope": "Data within Tech Innovations Inc (Organization data only)"
    },
    "scope": "organization",
    "platform_statistics": {
        "total_companies": 112,
        "total_predictions": 2882,
        "annual_predictions": 2728,
        "quarterly_predictions": 154,
        "average_default_rate": 0.0172,
        "high_risk_companies": 0,
        "sectors_covered": 15
    }
}
```

---

### 3. Tenant Admin Dashboard (Cross-Organization Access)

**Response:**
```json
{
    "user_dashboard": {
        "scope": "organization",
        "user_name": "Sarah Johnson",
        "organization_name": "Enterprise Solutions Ltd",
        "total_companies": 87,              // All organizations' companies
        "total_predictions": 2100,
        "annual_predictions": 1800,         // NEW: All organizations' annual predictions
        "quarterly_predictions": 300,       // NEW: All organizations' quarterly predictions
        "average_default_rate": 0.0165,
        "high_risk_companies": 3,
        "sectors_covered": 14,
        "data_scope": "Data within Enterprise Solutions Ltd (Cross-organization access - all orgs)"
    },
    "scope": "organization",
    "platform_statistics": {
        "total_companies": 112,
        "total_predictions": 2882,
        "annual_predictions": 2728,
        "quarterly_predictions": 154,
        "average_default_rate": 0.0172,
        "high_risk_companies": 0,
        "sectors_covered": 15
    }
}
```

---

### 4. Super Admin Dashboard

**Response:**
```json
{
    "user_dashboard": {
        "scope": "system",
        "user_name": "Admin User",
        "organization_name": "System Administrator",
        "total_companies": 112,
        "total_predictions": 2882,
        "annual_predictions": 2728,        // NEW: System-wide annual predictions
        "quarterly_predictions": 154,      // NEW: System-wide quarterly predictions
        "average_default_rate": 0.0172,
        "high_risk_companies": 0,
        "sectors_covered": 15,
        "data_scope": "All system data"
    },
    "scope": "system",
    "platform_statistics": {
        "total_companies": 112,
        "total_predictions": 2882,
        "annual_predictions": 2728,
        "quarterly_predictions": 154,
        "average_default_rate": 0.0172,
        "high_risk_companies": 0,
        "sectors_covered": 15
    }
}
```

---

## Field Descriptions

### User Dashboard Fields

| Field | Type | Description |
|-------|------|-------------|
| `scope` | string | Data scope: "personal", "organization", or "system" |
| `user_name` | string | Full name of the current user |
| `organization_name` | string | Organization name or "Personal Data"/"System Administrator" |
| `total_companies` | integer | Total number of companies in user's scope |
| `total_predictions` | integer | Total predictions (annual + quarterly) |
| `annual_predictions` | integer | **NEW**: Count of annual predictions |
| `quarterly_predictions` | integer | **NEW**: Count of quarterly predictions |
| `average_default_rate` | float | Average default probability (0.0 - 1.0) |
| `high_risk_companies` | integer | Companies with >70% default probability |
| `sectors_covered` | integer | Number of unique sectors |
| `data_scope` | string | Description of data accessibility |

### Platform Statistics Fields

| Field | Type | Description |
|-------|------|-------------|
| `total_companies` | integer | Platform-wide total companies |
| `total_predictions` | integer | Platform-wide total predictions |
| `annual_predictions` | integer | Platform-wide annual predictions count |
| `quarterly_predictions` | integer | Platform-wide quarterly predictions count |
| `average_default_rate` | float | Platform-wide average default rate |
| `high_risk_companies` | integer | Platform-wide high risk companies |
| `sectors_covered` | integer | Platform-wide sectors count |

### **REMOVED Fields (No Longer Returned)**
- ❌ `total_users` - Removed from platform_statistics
- ❌ `total_organizations` - Removed from platform_statistics  
- ❌ `total_tenants` - Removed from platform_statistics

---

## Scope Determination Logic

The dashboard automatically determines user scope based on role:

| User Role | Scope | Data Access |
|-----------|-------|-------------|
| `user` | personal | Only user's own predictions |
| `org_member` | organization | User's + organization's predictions |
| `org_admin` | organization | User's + organization's predictions |
| `tenant_admin` | organization | Cross-organization access |
| `super_admin` | system | All system predictions |

---

## Recent Updates

### ✅ Added to User Dashboard
- `annual_predictions`: Count of annual predictions in user's scope
- `quarterly_predictions`: Count of quarterly predictions in user's scope
- Better prediction type breakdown for analytics

### ❌ Removed from Platform Statistics  
- `total_users`: No longer returned (privacy/security)
- `total_organizations`: No longer returned (internal metric)
- `total_tenants`: No longer returned (internal metric)

### 🔄 Enhanced Data Structure
- Consistent prediction fields across user_dashboard and platform_statistics
- Mathematical validation: `annual_predictions + quarterly_predictions = total_predictions`
- Cleaner platform metrics focused on business data

---

## Error Responses

### Authentication Error (401)
```json
{
    "detail": "Not authenticated"
}
```

### Permission Error (403)
```json
{
    "detail": "Authentication required to view predictions"
}
```

### Organization Not Found (404)
```json
{
    "detail": "Organization not found"
}
```

### Server Error (500)
```json
{
    "detail": "Dashboard error: Database connection failed"
}
```

---

## Usage Examples

### Basic Dashboard Request
```bash
curl -X POST \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{}' \
  "http://localhost:8000/api/v1/predictions/dashboard"
```

### Dashboard with Platform Statistics
```bash
curl -X POST \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{"include_platform_stats": true}' \
  "http://localhost:8000/api/v1/predictions/dashboard"
```

### JavaScript/TypeScript Example
```typescript
const response = await fetch('/api/v1/predictions/dashboard', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        include_platform_stats: true
    })
});

const dashboardData = await response.json();

// Access prediction breakdown
const userAnnual = dashboardData.user_dashboard.annual_predictions;
const userQuarterly = dashboardData.user_dashboard.quarterly_predictions;
const userTotal = dashboardData.user_dashboard.total_predictions;

// Verify: userAnnual + userQuarterly should equal userTotal
console.assert(userAnnual + userQuarterly === userTotal);
```

---

## Integration Notes

### Frontend Integration
- Use `annual_predictions` and `quarterly_predictions` for charts and analytics
- `platform_statistics` provides system-wide context when needed
- `scope` field helps UI determine what data visualization to show

### Data Validation
- Always verify: `annual_predictions + quarterly_predictions = total_predictions`
- Check `scope` field to understand data context
- Handle cases where `platform_statistics` might be null (when not requested)

### Performance Considerations
- Set `include_platform_stats: false` if platform data isn't needed
- Dashboard data is computed in real-time, consider caching on frontend
- Scope determination happens automatically, no need for additional API calls

---

## Business Use Cases

1. **Personal Analytics**: Users see their prediction portfolio breakdown
2. **Organization Insights**: Teams analyze their collective prediction data  
3. **Platform Overview**: Admins get system-wide metrics for reporting
4. **Prediction Type Analysis**: Understanding annual vs quarterly prediction trends
5. **Risk Assessment**: High-risk company identification across different scopes
