# Access Model and Ownership

Roles
- user, org_member, org_admin, tenant_admin, super_admin

Access levels (per record)
- personal: visible to creator only (and privileged admins where endpoints allow)
- organization: visible to users in the same organization
- system: global objects created by super_admin; visibility can be toggled per-organization

Ownership
- created_by is stored on Companies, AnnualPrediction, QuarterlyPrediction.
- Updates for predictions are owner-only; only the creator can edit their prediction.
- Deletes and updates for other entities follow their endpoint-specific role rules.

Organization global data access
- Organization.allow_global_data_access controls whether org users can view system/global data.
- PATCH /api/v1/organizations/{org_id}/global-data-access?allow_access=true|false
- When enabled, org members can read:
  - Predictions created by super_admin users
  - Companies marked for global/system access

Scoping examples
- personal prediction: only creator can read/update; others get 403/404 depending on filters.
- organization prediction: org members can read; only creator can update.
- system prediction/company: visible to orgs only if allow_global_data_access is true.

Notes
- Access filters are applied in list/read endpoints; update/put checks also verify ownership or role as implemented in each router.
