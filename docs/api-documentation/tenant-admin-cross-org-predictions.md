# Tenant Admin Cross-Organization Predictions Access

## Current Limitation

**Issue**: Tenant admins currently cannot filter predictions by specific organization ID through the main prediction APIs. They are restricted to their own organization's data just like org_admin users.

**Evidence from Code Analysis**:
1. In `/app/api/v1/predictions.py`, the `get_data_access_filter()` function treats tenant_admin the same as org_admin
2. The `get_organization_context()` function returns `current_user.organization_id` for tenant_admin
3. No query parameter exists for `organization_id` in the main prediction endpoints

## Current Behavior

### What Tenant Admins Can Currently Access:
- ✅ **Personal predictions** (created by them)
- ✅ **Organization predictions** (from their assigned organization only)
- ❌ **Cross-organization predictions** (from other organizations in their tenant)

### Current API Endpoints:
```
GET /api/v1/predictions/annual
GET /api/v1/predictions/quarterly
```

**Access Control**: Limited to tenant admin's own organization (`user.organization_id`)

## Proposed Solution

### Option 1: Add Organization ID Query Parameter (Recommended)

Modify existing endpoints to accept an optional `organization_id` parameter for tenant admins:

#### **Enhanced Endpoint Signature:**
```python
@router.get("/annual", response_model=Dict)
async def get_annual_predictions(
    request: Request, 
    page: int = 1,
    size: int = 10,
    company_symbol: Optional[str] = None,
    reporting_year: Optional[str] = None,
    organization_id: Optional[str] = None,  # NEW PARAMETER
    db: Session = Depends(get_db),
    current_user: User = Depends(current_verified_user)
):
```

#### **Enhanced Access Control Logic:**
```python
def get_tenant_admin_access_filter(user: User, prediction_model, organization_id: Optional[str] = None):
    """Enhanced access filter for tenant admins with cross-org capability"""
    
    if user.role == "super_admin":
        return None  # Full access
    
    conditions = []
    
    # Personal predictions (always accessible)
    conditions.append(
        and_(
            prediction_model.access_level == "personal",
            prediction_model.created_by == str(user.id)
        )
    )
    
    if user.role == "tenant_admin":
        # Tenant admin can access predictions from any org in their tenant
        if organization_id:
            # Verify the organization belongs to tenant admin's tenant
            org = db.query(Organization).filter(
                Organization.id == organization_id,
                Organization.tenant_id == user.tenant_id
            ).first()
            
            if org:
                conditions.append(
                    and_(
                        prediction_model.access_level == "organization",
                        prediction_model.organization_id == organization_id
                    )
                )
        else:
            # No specific org requested - show all orgs in tenant
            tenant_org_ids = db.query(Organization.id).filter(
                Organization.tenant_id == user.tenant_id
            ).all()
            tenant_org_ids = [str(org_id[0]) for org_id in tenant_org_ids]
            
            conditions.append(
                and_(
                    prediction_model.access_level == "organization",
                    prediction_model.organization_id.in_(tenant_org_ids)
                )
            )
    
    elif user.organization_id:
        # Regular org users - restricted to their organization
        conditions.append(
            and_(
                prediction_model.access_level == "organization", 
                prediction_model.organization_id == user.organization_id
            )
        )
    
    return or_(*conditions)
```

#### **Usage Examples:**

**Get all predictions across tenant:**
```bash
GET /api/v1/predictions/annual
# Returns predictions from all organizations in tenant admin's tenant
```

**Get predictions from specific organization:**
```bash
GET /api/v1/predictions/annual?organization_id=550e8400-e29b-41d4-a716-446655440000
# Returns predictions only from specified organization (if in same tenant)
```

**Get predictions with other filters:**
```bash
GET /api/v1/predictions/annual?organization_id=550e8400-e29b-41d4-a716-446655440000&company_symbol=AAPL&reporting_year=2024
# Returns Apple predictions from specified organization for 2024
```

### Option 2: Create Dedicated Tenant Admin Endpoints

Add new endpoints specifically for tenant admin cross-organization access:

#### **New Endpoints:**
```python
@router.get("/annual/cross-org", response_model=Dict)
async def get_tenant_annual_predictions(
    request: Request,
    organization_id: str,  # REQUIRED for cross-org access
    page: int = 1,
    size: int = 10,
    company_symbol: Optional[str] = None,
    reporting_year: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above)
):
    """Get annual predictions from specific organization (Tenant Admin+ only)"""
    
    # Verify organization belongs to tenant admin's tenant
    organization = db.query(Organization).filter(
        Organization.id == organization_id,
        Organization.tenant_id == current_user.tenant_id
    ).first()
    
    if not organization:
        raise HTTPException(
            status_code=404, 
            detail="Organization not found or not accessible"
        )
    
    # Query predictions from specified organization
    query = db.query(AnnualPrediction).filter(
        AnnualPrediction.organization_id == organization_id
    )
    
    # Apply additional filters...
    # ... rest of implementation
```

#### **Usage Examples:**
```bash
# Get predictions from specific organization
GET /api/v1/predictions/annual/cross-org?organization_id=550e8400-e29b-41d4-a716-446655440000

# Get quarterly predictions from specific organization
GET /api/v1/predictions/quarterly/cross-org?organization_id=550e8400-e29b-41d4-a716-446655440000&company_symbol=MSFT
```

### Option 3: Enhanced Dashboard API

Extend the existing dashboard functionality to provide organization-specific prediction lists:

#### **New Dashboard Endpoint:**
```python
@router.get("/dashboard/organization/{organization_id}/predictions")
async def get_organization_predictions_dashboard(
    organization_id: str,
    prediction_type: str = "annual",  # "annual" or "quarterly"
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above)
):
    """Get predictions dashboard for specific organization (Tenant Admin+ only)"""
```

## **API Documentation Updates Needed**

### **Enhanced Predictions API Documentation:**

#### **Access Control Table:**
| Role | Personal | Own Org | Cross-Org | System |
|------|----------|---------|-----------|---------|
| `user` | ✅ | ❌ | ❌ | ❌ |
| `org_member` | ✅ | ✅ (view) | ❌ | ❌ |
| `org_admin` | ✅ | ✅ (full) | ❌ | ❌ |
| `tenant_admin` | ✅ | ✅ | ✅ (with org_id) | ❌ |
| `super_admin` | ✅ | ✅ | ✅ | ✅ |

#### **New Query Parameters:**
| Parameter | Type | Required | Description | Access Level |
|-----------|------|----------|-------------|--------------|
| `organization_id` | string | No | Filter by specific organization | tenant_admin+ |
| `page` | int | No | Page number (default: 1) | All |
| `size` | int | No | Items per page (default: 10) | All |
| `company_symbol` | string | No | Filter by company symbol | All |
| `reporting_year` | string | No | Filter by reporting year | All |

#### **Example API Responses:**

**Tenant Admin - All Organizations:**
```json
{
  "predictions": [
    {
      "id": "pred-1",
      "company_symbol": "AAPL",
      "organization_id": "org-retail",
      "organization_name": "Retail Banking",
      "probability": 0.15,
      "created_at": "2024-10-05T16:30:00Z"
    },
    {
      "id": "pred-2", 
      "company_symbol": "MSFT",
      "organization_id": "org-corporate",
      "organization_name": "Corporate Banking",
      "probability": 0.08,
      "created_at": "2024-10-05T17:45:00Z"
    }
  ],
  "total": 45,
  "page": 1,
  "size": 10,
  "access_scope": "cross_organization"
}
```

**Tenant Admin - Specific Organization:**
```json
{
  "predictions": [
    {
      "id": "pred-1",
      "company_symbol": "AAPL", 
      "organization_id": "org-retail",
      "organization_name": "Retail Banking",
      "probability": 0.15,
      "created_at": "2024-10-05T16:30:00Z"
    }
  ],
  "total": 12,
  "page": 1,
  "size": 10,
  "access_scope": "single_organization",
  "filtered_organization": {
    "id": "org-retail",
    "name": "Retail Banking"
  }
}
```

## **Implementation Priority**

### **Recommended Approach: Option 1**
- ✅ **Minimal Code Changes**: Extends existing endpoints
- ✅ **Backward Compatible**: Doesn't break existing functionality  
- ✅ **Consistent API**: Uses same endpoints for all users
- ✅ **Flexible**: Supports both single-org and cross-org access

### **Implementation Steps:**
1. **Modify Access Control**: Update `get_data_access_filter()` function
2. **Add Query Parameter**: Add `organization_id` to prediction endpoints
3. **Add Validation**: Verify organization belongs to tenant admin's tenant
4. **Update Documentation**: Document new parameter and access levels
5. **Add Tests**: Test cross-organization access and security
6. **Deploy**: Roll out with feature flag for testing

### **Security Considerations:**
- ✅ **Tenant Isolation**: Ensure tenant admins can only access orgs in their tenant
- ✅ **Organization Validation**: Verify organization ID belongs to correct tenant
- ✅ **Permission Checks**: Maintain existing role-based access control
- ✅ **Audit Logging**: Log cross-organization access attempts

## **Current Workaround**

Until this feature is implemented, tenant admins can:
1. **Use Dashboard API**: Limited cross-org access through dashboard endpoints
2. **Switch Organizations**: If assigned to multiple orgs, switch context
3. **Request Super Admin**: Ask super admin to provide cross-org data

## **Impact Assessment**

### **Benefits:**
- 🎯 **Enhanced Tenant Management**: Tenant admins can properly manage all organizations
- 📊 **Better Analytics**: Cross-organization reporting and comparison
- 🚀 **Improved Workflow**: Reduces need for super admin intervention
- 🔄 **Consistent UX**: Aligns API capability with role hierarchy

### **Risks:**
- 🔒 **Security**: Must ensure proper tenant isolation
- 📈 **Performance**: Cross-org queries may be slower
- 🧪 **Testing**: Requires comprehensive security testing
- 📚 **Documentation**: Needs clear access control documentation

## **Implementation Status**

✅ **IMPLEMENTED** - The tenant admin cross-organization predictions feature has been successfully implemented!

### **What's Now Available:**

1. **Enhanced API Endpoints**: Both annual and quarterly prediction endpoints now accept `organization_id` parameter
2. **Proper Access Control**: Tenant admins can filter by organization_id, other roles cannot
3. **Security Validation**: Organization must belong to tenant admin's tenant
4. **Backward Compatibility**: Existing functionality unchanged for all user types

### **API Usage:**

```bash
# ✅ NOW WORKS - Tenant admin filtering by organization
GET /api/v1/predictions/annual?page=1&size=1000&organization_id=326ae596-2a69-463c-8db1-cfbfe249ff0b

# ✅ Cross-tenant security - Returns empty if org not in tenant
GET /api/v1/predictions/quarterly?organization_id=other-tenant-org-id

# ✅ All organizations in tenant (no org_id parameter)
GET /api/v1/predictions/annual?page=1&size=50
```

### **Testing:**
Run the test script to verify functionality:
```bash
python test_tenant_admin_predictions.py
```

## **Conclusion**

**Current Answer**: **YES** ✅ - Tenant admins can now get predictions filtered by specific organization ID using the `organization_id` query parameter.

**Implementation**: Completed Option 1 (add `organization_id` query parameter) with full security validation and backward compatibility.
