# Organizations API

Base path: /api/v1/organizations
Authentication: required

List organizations
GET /
Query: page (int, default 1), limit (1-100), search, is_active, tenant_id (super_admin only)
Rate limit: 100/hour, 500/day

Get organization
GET /{org_id}
Rate limit: 100/hour, 500/day

Create organization
POST /
Body: { name, domain?, description?, logo_url?, tenant_id? }
Roles: super_admin or tenant_admin (tenant_admin only within own tenant)
Rate limit: 20/hour, 100/day

Update organization
PUT /{org_id}
Body: OrganizationUpdate (partial)
Roles: super_admin, tenant_admin (own tenant), org_admin (own organization)
Rate limit: 50/hour, 200/day

Delete organization
DELETE /{org_id}?force=false
Roles: super_admin, tenant_admin (own tenant)
Rate limit: 10/hour, 50/day

Regenerate join token
POST /{org_id}/regenerate-token
Roles: super_admin, tenant_admin (own tenant), org_admin (own org)
Rate limit: 5/hour, 20/day
Response: { message, new_token, join_url }

Whitelist management
GET /{org_id}/whitelist?skip=0&limit=50
POST /{org_id}/whitelist { email }
DELETE /{org_id}/whitelist/{email}
Roles: org_admin or above (and scoped to org/tenant where applicable)

Organization users
GET /{org_id}/users?skip=0&limit=50&role=
Roles: super_admin, tenant_admin (own tenant), org members of that org

Details and admins
GET /{org_id}/details
GET /{org_id}/admins
Roles: super_admin, tenant_admin (own tenant), org members of that org

Global data access setting
PATCH /{org_id}/global-data-access?allow_access=true|false
GET   /{org_id}/global-data-access
Roles (PATCH): super_admin or tenant_admin (own tenant)
Roles (GET): super_admin, tenant_admin (own tenant), org users of that org

Validation and errors
- 400: duplicate domain, invalid domain
- 403: cross-tenant access, insufficient role
- 404: organization not found
- 422: validation errors (see error-handling.md)

Minimal create example
POST /api/v1/organizations
{ "name": "Acme Inc", "domain": "acme.com" }
