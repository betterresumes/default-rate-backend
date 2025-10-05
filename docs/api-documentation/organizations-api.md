# Organizations API

Complete API reference for organization management in AccuNode's multi-tenant architecture.

## Base Information
- **Base Path**: `/api/v1/organizations`
- **Authentication**: Required (JWT token)
- **Rate Limiting**: Applied per endpoint (see individual endpoints)

## Access Control

### Role-Based Permissions
| Role | Access Level | Can Do |
|------|-------------|---------|
| **super_admin** | Full system access | All operations across all tenants |
| **tenant_admin** | Tenant-scoped | Operations within their tenant only |
| **org_admin** | Organization-scoped | Manage their organization + members |
| **org_member** | Read-only org access | View their organization details |

## API Endpoints

### List Organizations
```
GET /api/v1/organizations/
```

**Parameters:**
- `page` (int, default: 1) - Page number for pagination
- `limit` (int, 1-100, default: 10) - Items per page
- `search` (string, optional) - Search in name, domain, description
- `is_active` (boolean, optional) - Filter by active status
- `tenant_id` (string, optional) - Filter by tenant (super_admin only)

**Access:**
- **super_admin**: All organizations across all tenants
- **tenant_admin**: Organizations in their tenant only
- **org_admin/org_member**: Their organization only

**Rate Limit:** 100/hour, 500/day

**Response:**
```json
{
  "organizations": [...],
  "total": 25,
  "skip": 0,
  "limit": 10
}
```

### Get Organization Details
```
GET /api/v1/organizations/{org_id}
```

**Access:** super_admin, tenant_admin (own tenant), org users (own org)
**Rate Limit:** 100/hour, 500/day

**Response:** Enhanced organization details with tenant info, admin, and member lists.

### Create Organization
```
POST /api/v1/organizations/
```

**Body:**
```json
{
  "name": "Organization Name",
  "domain": "example.com",
  "description": "Optional description",
  "logo_url": "https://example.com/logo.png",
  "tenant_id": "optional-tenant-id"
}
```

**Access:**
- **super_admin**: Can create for any tenant (tenant_id optional)
- **tenant_admin**: Can create only within their tenant

**Rate Limit:** 20/hour, 100/day

**Validation:**
- `name` is required and becomes the organization slug
- `domain` must be unique and valid format
- Duplicate domains return 400 error

### Update Organization
```
PUT /api/v1/organizations/{org_id}
```

**Body:** Partial organization data (same fields as create)

**Access:**
- **super_admin**: Any organization
- **tenant_admin**: Organizations in their tenant
- **org_admin**: Their own organization only

**Rate Limit:** 50/hour, 200/day

### Delete Organization
```
DELETE /api/v1/organizations/{org_id}?force=false
```

**Parameters:**
- `force` (boolean, default: false) - Force delete even with users

**Access:** super_admin, tenant_admin (own tenant only)
**Rate Limit:** 10/hour, 50/day

**Behavior:**
- Without `force=true`: Fails if organization has users
- With `force=true`: Removes all users from org before deletion

### Join Token Management
```
POST /api/v1/organizations/{org_id}/regenerate-token
```

**Access:** super_admin, tenant_admin (own tenant), org_admin (own org)
**Rate Limit:** 5/hour, 20/day

**Response:**
```json
{
  "message": "Join token regenerated successfully",
  "new_token": "abc123...",
  "join_url": "/join/abc123..."
}
```

### Member Whitelist
```
GET /api/v1/organizations/{org_id}/whitelist
POST /api/v1/organizations/{org_id}/whitelist
DELETE /api/v1/organizations/{org_id}/whitelist/{email}
```

**Parameters (GET):**
- `skip` (int, default: 0)
- `limit` (int, 1-100, default: 50)

**Body (POST):**
```json
{
  "email": "user@example.com"
}
```

**Access:** org_admin or above (scoped to org/tenant)
**Rate Limits:**
- GET: 100/hour, 500/day
- POST/DELETE: 50/hour, 200/day

### Organization Users
```
GET /api/v1/organizations/{org_id}/users
```

**Parameters:**
- `skip`, `limit` (pagination)
- `role` (string, optional) - Filter by user role

**Access:** super_admin, tenant_admin (own tenant), org users (own org)
**Rate Limit:** 100/hour, 500/day

### Organization Details & Admins
```
GET /api/v1/organizations/{org_id}/details
GET /api/v1/organizations/{org_id}/admins
```

**Access:** super_admin, tenant_admin (own tenant), org users (own org)
**Rate Limit:** 100/hour, 500/day

**Returns:** Detailed org information including admin list and user statistics.

### Global Data Access Control
```
GET /api/v1/organizations/{org_id}/global-data-access
PATCH /api/v1/organizations/{org_id}/global-data-access?allow_access=true
```

**Purpose:** Control whether organization users can view system-wide/global data created by super_admin.

**Access:**
- **GET**: super_admin, tenant_admin (own tenant), org users (own org)
- **PATCH**: super_admin, tenant_admin (own tenant) only

**Effect:** When enabled, org users can view global predictions and companies. Does not grant modification rights.

## Error Responses

| Code | Description | Example |
|------|-------------|---------|
| 400 | Invalid/duplicate domain | Domain already registered |
| 403 | Insufficient permissions | Cannot access different tenant |
| 404 | Organization not found | Organization with ID not found |
| 422 | Validation errors | See [error-handling.md](./error-handling.md) |

## Default Values

When creating organizations:
- `slug`: Auto-generated from name (with numeric suffix for uniqueness)
- `join_enabled`: true
- `default_role`: "org_member"
- `max_users`: 500
- `join_token`: Auto-generated unique token

## Example Usage

### Create Organization
```bash
curl -X POST "http://localhost:8000/api/v1/organizations/" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corporation",
    "domain": "acme.com",
    "description": "Leading manufacturing company"
  }'
```

### List Organizations with Search
```bash
curl "http://localhost:8000/api/v1/organizations/?search=acme&limit=20" \
  -H "Authorization: Bearer <token>"
```
