# Dashboard API Documentation

## Overview
The Dashboard API provides comprehensive statistics and analytics based on the user's role and access level. This endpoint returns different data scopes depending on who is making the request.

---

## Endpoint Details

**URL:** `GET /api/v1/predictions/dashboard`  
**Authentication:** Required (Bearer Token)  
**Content-Type:** `application/json`

---

## Role-Based Response Structure

The API returns different data based on the authenticated user's role:

1. **Personal User** - Only their own data
2. **Organization Admin/Member** - All data within their organization  
3. **Tenant Admin** - All data across organizations in their tenant + breakdown
4. **Super Admin** - System-wide data + tenant breakdown

---

## Response Examples

### 1. Personal User Response

**User Role:** Personal user (not in any organization)  
**Data Scope:** Only companies and predictions they created

```json
{
  "scope": "personal",
  "user_name": "Sarah Williams",
  "total_companies": 4305,
  "total_predictions": 8610,
  "average_default_rate": 0.1234,
  "high_risk_companies": 430,
  "sectors_covered": 15,
  "data_scope": "Only companies and predictions you created"
}
```

### 2. Organization User Response

**User Role:** `org_admin` or `org_member`  
**Data Scope:** All data within their organization

```json
{
  "scope": "organization",
  "user_name": "Robert Chen",
  "organization_name": "Morgan Stanley Credit Risk Division",
  "total_companies": 12500,
  "total_predictions": 25000,
  "average_default_rate": 0.0875,
  "high_risk_companies": 1250,
  "sectors_covered": 25,
  "data_scope": "All data within Morgan Stanley Credit Risk Division"
}
```

### 3. Tenant Admin Response

**User Role:** `tenant_admin`  
**Data Scope:** All organizations within their tenant + detailed breakdown

```json
{
  "scope": "tenant",
  "user_name": "Jennifer Thompson",
  "tenant_name": "Default Rate Analytics Inc",
  "total_companies": 45000,
  "total_predictions": 90000,
  "average_default_rate": 0.1050,
  "high_risk_companies": 4500,
  "sectors_covered": 35,
  "organizations_breakdown": [
    {
      "org_name": "Morgan Stanley Credit Risk Division",
      "companies": 25000,
      "predictions": 50000,
      "avg_default_rate": 0.0875,
      "high_risk_companies": 2500,
      "sectors_covered": 20
    },
    {
      "org_name": "JPMorgan Chase Risk Analytics",
      "companies": 20000,
      "predictions": 40000,
      "avg_default_rate": 0.1280,
      "high_risk_companies": 2000,
      "sectors_covered": 18
    }
  ],
  "data_scope": "All organizations within Default Rate Analytics Inc"
}
```

### 4. Super Admin Response

**User Role:** `super_admin`  
**Data Scope:** Entire system across all tenants and access levels

```json
{
  "scope": "system",
  "total_companies": 150000,
  "total_predictions": 300000,
  "average_default_rate": 0.1125,
  "high_risk_companies": 15000,
  "sectors_covered": 50,
  "tenants_breakdown": [
    {
      "tenant_name": "Default Rate Analytics Inc",
      "companies": 45000,
      "predictions": 90000,
      "organizations_count": 2
    },
    {
      "tenant_name": "Global Risk Partners",
      "companies": 35000,
      "predictions": 70000,
      "organizations_count": 3
    },
    {
      "tenant_name": "Enterprise Credit Solutions",
      "companies": 70000,
      "predictions": 140000,
      "organizations_count": 5
    }
  ],
  "data_scope": "Entire system across all tenants and access levels"
}
```

---

## Field Definitions

### Common Fields (All Responses)

| Field | Type | Description |
|-------|------|-------------|
| `scope` | string | User's access scope: `"personal"`, `"organization"`, `"tenant"`, or `"system"` |
| `total_companies` | integer | Total number of companies visible to the user |
| `total_predictions` | integer | Total number of predictions (annual + quarterly) |
| `average_default_rate` | float | Mean default probability across all predictions (0.0 to 1.0) |
| `high_risk_companies` | integer | Number of companies with latest prediction > 0.15 (15%) |
| `sectors_covered` | integer | Number of unique industry sectors represented |
| `data_scope` | string | Human-readable description of what data the user can see |

### Role-Specific Fields

#### Personal Users
| Field | Type | Description |
|-------|------|-------------|
| `user_name` | string | Full name of the authenticated user |

#### Organization Users  
| Field | Type | Description |
|-------|------|-------------|
| `user_name` | string | Full name of the authenticated user |
| `organization_name` | string | Name of the user's organization |

#### Tenant Admins
| Field | Type | Description |
|-------|------|-------------|
| `user_name` | string | Full name of the authenticated user |
| `tenant_name` | string | Name of the user's tenant |
| `organizations_breakdown` | array | Detailed statistics for each organization in the tenant |

**Organization Breakdown Object:**
```json
{
  "org_name": "string",
  "companies": "integer",
  "predictions": "integer", 
  "avg_default_rate": "float",
  "high_risk_companies": "integer",
  "sectors_covered": "integer"
}
```

#### Super Admins
| Field | Type | Description |
|-------|------|-------------|
| `tenants_breakdown` | array | High-level statistics for each tenant |

**Tenant Breakdown Object:**
```json
{
  "tenant_name": "string",
  "companies": "integer",
  "predictions": "integer",
  "organizations_count": "integer"
}
```

---

## Business Logic

### High Risk Threshold
- **Definition:** Companies with default probability > 0.15 (15%)
- **Calculation:** Based on the **latest prediction** per company (no double counting)
- **Models:** Considers both annual and quarterly predictions, uses most recent

### Average Default Rate
- **Calculation:** Mean of all prediction probabilities
- **Scope:** Includes **all predictions** (historical data for trend analysis)
- **Models:** 
  - Annual: Uses `probability` field
  - Quarterly: Uses `logistic_probability` field

### Predictions Count
- **Method:** Raw count of all predictions (not unique per company)
- **Rationale:** Shows total prediction workload and historical activity
- **Types:** Annual + Quarterly predictions combined

### Sectors Covered
- **Source:** `sector` field from Companies table
- **Logic:** Count of unique sectors across all visible companies

---

## Error Responses

### Authentication Error
```json
{
  "detail": "Could not validate credentials"
}
```
**Status Code:** `401 Unauthorized`

### Authorization Error  
```json
{
  "detail": "User not associated with an organization"
}
```
**Status Code:** `400 Bad Request`

### Server Error
```json
{
  "detail": "Error generating dashboard: [specific error message]"
}
```
**Status Code:** `500 Internal Server Error`

---

## Frontend Implementation Guide

### 1. Request Setup
```javascript
const response = await fetch('/api/v1/predictions/dashboard', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${userToken}`,
    'Content-Type': 'application/json'
  }
});

const dashboardData = await response.json();
```

### 2. Role-Based UI Rendering

```javascript
function renderDashboard(data) {
  const { scope } = data;
  
  switch(scope) {
    case 'personal':
      return renderPersonalDashboard(data);
    case 'organization':
      return renderOrganizationDashboard(data);
    case 'tenant':
      return renderTenantDashboard(data);
    case 'system':
      return renderSystemDashboard(data);
    default:
      return renderErrorState();
  }
}
```

### 3. Display Components

#### Main Metrics Cards
```javascript
const MetricsCards = ({ data }) => (
  <div className="metrics-grid">
    <MetricCard 
      title="Total Companies" 
      value={data.total_companies.toLocaleString()} 
      icon="building"
    />
    <MetricCard 
      title="Total Predictions" 
      value={data.total_predictions.toLocaleString()} 
      icon="chart-line"
    />
    <MetricCard 
      title="Average Default Rate" 
      value={`${(data.average_default_rate * 100).toFixed(2)}%`} 
      icon="percentage"
    />
    <MetricCard 
      title="High Risk Companies" 
      value={data.high_risk_companies.toLocaleString()} 
      icon="exclamation-triangle"
      alert={data.high_risk_companies > 0}
    />
    <MetricCard 
      title="Sectors Covered" 
      value={data.sectors_covered} 
      icon="industry"
    />
  </div>
);
```

#### Tenant Admin Breakdown Table
```javascript
const OrganizationBreakdown = ({ organizations }) => (
  <table className="breakdown-table">
    <thead>
      <tr>
        <th>Organization</th>
        <th>Companies</th>
        <th>Predictions</th>
        <th>Avg Default Rate</th>
        <th>High Risk</th>
        <th>Sectors</th>
      </tr>
    </thead>
    <tbody>
      {organizations.map(org => (
        <tr key={org.org_name}>
          <td>{org.org_name}</td>
          <td>{org.companies.toLocaleString()}</td>
          <td>{org.predictions.toLocaleString()}</td>
          <td>{(org.avg_default_rate * 100).toFixed(2)}%</td>
          <td className={org.high_risk_companies > 0 ? 'high-risk' : ''}>
            {org.high_risk_companies.toLocaleString()}
          </td>
          <td>{org.sectors_covered}</td>
        </tr>
      ))}
    </tbody>
  </table>
);
```

#### Super Admin Tenant Overview
```javascript
const TenantOverview = ({ tenants }) => (
  <div className="tenant-overview">
    {tenants.map(tenant => (
      <div key={tenant.tenant_name} className="tenant-card">
        <h3>{tenant.tenant_name}</h3>
        <div className="tenant-stats">
          <span>{tenant.companies.toLocaleString()} companies</span>
          <span>{tenant.predictions.toLocaleString()} predictions</span>
          <span>{tenant.organizations_count} organizations</span>
        </div>
      </div>
    ))}
  </div>
);
```

### 4. Data Scope Indicator
```javascript
const ScopeIndicator = ({ scope, dataScope }) => (
  <div className={`scope-indicator scope-${scope}`}>
    <span className="scope-badge">{scope.toUpperCase()}</span>
    <span className="scope-description">{dataScope}</span>
  </div>
);
```

### 5. Refresh and Real-time Updates
```javascript
// Auto-refresh every 5 minutes
useEffect(() => {
  const interval = setInterval(fetchDashboardData, 5 * 60 * 1000);
  return () => clearInterval(interval);
}, []);

// Manual refresh button
const handleRefresh = async () => {
  setLoading(true);
  try {
    const data = await fetchDashboardData();
    setDashboardData(data);
    setLastUpdated(new Date());
  } catch (error) {
    setError(error.message);
  } finally {
    setLoading(false);
  }
};
```

---

## Sample CSS Styling

```css
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.metric-card {
  padding: 1.5rem;
  border-radius: 8px;
  background: white;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  border-left: 4px solid var(--primary-color);
}

.metric-card.alert {
  border-left-color: var(--danger-color);
}

.scope-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.scope-badge {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: bold;
  text-transform: uppercase;
}

.scope-personal { background: #e3f2fd; color: #1976d2; }
.scope-organization { background: #f3e5f5; color: #7b1fa2; }  
.scope-tenant { background: #e8f5e8; color: #388e3c; }
.scope-system { background: #fff3e0; color: #f57c00; }

.breakdown-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 1rem;
}

.breakdown-table th,
.breakdown-table td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

.breakdown-table .high-risk {
  color: #d32f2f;
  font-weight: bold;
}
```

---

## Testing

### Test Users (from setup script)

```bash
# Super Admin
Email: admin@defaultrate.com
Password: Admin123!

# Tenant Admin  
Email: ceo@defaultrate.com
Password: CEO123!

# Org Admin (Morgan Stanley)
Email: risk.director@morganstanley.com  
Password: Director123!

# Org Member (JPMorgan)
Email: emily.davis@jpmorgan.com
Password: Analyst123!
```

### Test Scenarios

1. **No Data State:** Test with fresh user accounts (empty dashboard)
2. **Role Switching:** Login with different roles to see scope changes
3. **Organization Breakdown:** Use tenant admin to see multi-org view
4. **System Overview:** Use super admin for complete system visibility
5. **Error Handling:** Test with invalid tokens, missing permissions

---

## Performance Considerations

- **Caching:** Consider caching dashboard data for 1-5 minutes
- **Pagination:** Large tenant/super admin views may need pagination for breakdowns
- **Loading States:** Implement skeleton screens for better UX
- **Error Boundaries:** Wrap dashboard components in error boundaries
- **Progressive Loading:** Load main metrics first, then detailed breakdowns

This API provides a powerful foundation for building role-based dashboards with comprehensive business intelligence! 📊
