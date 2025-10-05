# Tenants API

Complete API reference for tenant management in AccuNode's multi-tenant architecture.

## Base Information
- **Base Path**: `/api/v1/tenants`
- **Authentication**: Required (JWT token)
- **Rate Limiting**: Applied per endpoint (see individual endpoints)

## Access Control

### Role-Based Permissions
| Role | Access Level | Can Do |
|------|-------------|---------|
| **super_admin** | Full system access | All tenant operations across the system |
| **tenant_admin** | Tenant-scoped | Operations within their own tenant only |
| **Other roles** | No access | Cannot access tenant management endpoints |

## API Endpoints

### Create Tenant
```
POST /api/v1/tenants/
```

**Body:**
```json
{
  "name": "Enterprise Tenant Name",
  "domain": "enterprise.com",
  "description": "Optional tenant description",
  "logo_url": "https://enterprise.com/logo.png"
}
```

**Access:** super_admin only
**Rate Limit:** 20/hour, 100/day

**Validation:**
- `name` is required and becomes the tenant slug
- `domain` must be unique and valid format if provided
- Duplicate domains return 400 error

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Enterprise Tenant Name",
  "slug": "enterprise-tenant-name",
  "domain": "enterprise.com",
  "description": "Optional tenant description",
  "logo_url": "https://enterprise.com/logo.png",
  "is_active": true,
  "created_by": "admin-user-id",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

### List Tenants
```
GET /api/v1/tenants/
```

**Parameters:**
- `skip` (int, default: 0) - Number of records to skip
- `limit` (int, 1-100, default: 50) - Maximum records to return
- `search` (string, optional) - Search in name, domain, description
- `is_active` (boolean, optional) - Filter by active status

**Access:**
- **super_admin**: All tenants with comprehensive details
- **tenant_admin**: Only their own tenant

**Rate Limit:** 100/hour, 500/day

**Response:**
```json
{
  "tenants": [
    {
      "id": "tenant-id",
      "name": "Tenant Name",
      "slug": "tenant-slug",
      "domain": "tenant.com",
      "is_active": true,
      "tenant_admins": [...],
      "organizations": [...],
      "total_organizations": 5,
      "active_organizations": 4,
      "total_users_in_tenant": 25,
      "total_active_users": 23
    }
  ],
  "total": 10,
  "skip": 0,
  "limit": 50,
  "total_tenant_admins": 8,
  "total_organizations": 45,
  "total_users": 250
}
```

### Get Tenant Details
```
GET /api/v1/tenants/{tenant_id}
```

**Access:**
- **super_admin**: Any tenant
- **tenant_admin**: Their own tenant only

**Rate Limit:** 100/hour, 500/day

**Response:** Comprehensive tenant information including:
- Tenant details
- List of tenant admins with their information
- All organizations under the tenant with admin/member details
- User count summaries

### Update Tenant
```
PUT /api/v1/tenants/{tenant_id}
```

**Body:** Partial tenant data (same fields as create)

**Access:**
- **super_admin**: Any tenant
- **tenant_admin**: Their own tenant only

**Rate Limit:** 50/hour, 200/day

**Validation:**
- Domain must be unique if changed
- Cannot change tenant to inactive if it has active organizations

### Delete Tenant
```
DELETE /api/v1/tenants/{tenant_id}?force=false
```

**Parameters:**
- `force` (boolean, default: false) - Force delete even with organizations

**Access:** super_admin only
**Rate Limit:** 10/hour, 50/day

**Behavior:**
- Without `force=true`: Fails if tenant has organizations
- With `force=true`: Deletes all organizations under tenant first

**Response:**
```json
{
  "message": "Tenant 'Enterprise Alpha' deleted successfully"
}
```

### Get Tenant Statistics
```
GET /api/v1/tenants/{tenant_id}/stats
```

**Access:**
- **super_admin**: Any tenant
- **tenant_admin**: Their own tenant only

**Rate Limit:** 100/hour, 500/day

**Response:**
```json
{
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_name": "Enterprise Alpha",
  "total_organizations": 12,
  "active_organizations": 10,
  "total_users": 145,
  "created_at": "2025-01-01T00:00:00Z"
}
```

## Error Responses

| Code | Description | Example |
|------|-------------|---------|
| 400 | Invalid/duplicate domain or deletion blocked | Domain already registered |
| 403 | Insufficient permissions | Cannot access different tenant |
| 404 | Tenant not found | Tenant with ID not found |
| 422 | Validation errors | See [error-handling.md](./error-handling.md) |

## Default Values

When creating tenants:
- `slug`: Auto-generated from name (with numeric suffix for uniqueness)
- `is_active`: true
- `created_at`/`updated_at`: Current timestamp

## Business Logic Notes

### Tenant Hierarchy
- Tenants are the top-level entity in the multi-tenant architecture
- Each tenant can have multiple organizations
- Tenant admins can manage organizations within their tenant
- Users belong to organizations, which belong to tenants

### Data Isolation
- Tenant admins can only see/manage their tenant's data
- Super admins have full access across all tenants
- Organization data is scoped to the parent tenant

## Example Usage

### Create Enterprise Tenant
```bash
curl -X POST "http://localhost:8000/api/v1/tenants/" \
  -H "Authorization: Bearer <super_admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Enterprise Alpha",
    "domain": "alpha.enterprise.com",
    "description": "Main enterprise tenant for Alpha Corp"
  }'
```

### List Tenants with Search
```bash
curl "http://localhost:8000/api/v1/tenants/?search=alpha&is_active=true" \
  -H "Authorization: Bearer <token>"
```

### Get Tenant Statistics
```bash
curl "http://localhost:8000/api/v1/tenants/550e8400-e29b-41d4-a716-446655440000/stats" \
  -H "Authorization: Bearer <token>"
```
