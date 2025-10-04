# Tenants API

Base path: /api/v1/tenants
Authentication: required

Create tenant
POST /
Body: { name, domain?, description?, logo_url? }
Roles: super_admin
Rate limit: 20/hour, 100/day

List tenants
GET /
Query: skip, limit (1-100), search, is_active
Roles: super_admin, tenant_admin (restricted to own tenant)
Rate limit: 100/hour, 500/day

Get tenant
GET /{tenant_id}
Roles: super_admin, tenant_admin (own tenant)
Rate limit: 100/hour, 500/day

Update tenant
PUT /{tenant_id}
Roles: super_admin, tenant_admin (own tenant)
Rate limit: 50/hour, 200/day

Delete tenant
DELETE /{tenant_id}?force=false
Roles: super_admin
Rate limit: 10/hour, 50/day

Tenant stats
GET /{tenant_id}/stats
Roles: super_admin, tenant_admin (own tenant)
Rate limit: 100/hour, 500/day

Validation and errors
- 400: duplicate domain, invalid domain, delete blocked without force
- 403: access to other tenants (for tenant_admin)
- 404: not found
- 422: validation errors (see error-handling.md)

Minimal create example
POST /api/v1/tenants
{ "name": "Enterprise Alpha", "domain": "alpha.example" }
