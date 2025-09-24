# Permission Analysis & Recommendations

## Current Issues

### 1. Bulk Upload Predictions
**Current Status:** ✅ WORKS
- User who does bulk upload can edit/delete their predictions
- `created_by` field is properly set to the user's ID who initiated the upload

### 2. Organization Predictions  
**Current Status:** ❌ TOO RESTRICTIVE
- Organization members CANNOT edit/delete organization predictions
- Only the exact creator or super_admin can modify predictions
- This breaks typical organization workflows

## Recommended Permission Logic

### Option A: Creator + Organization Model
```python
# Allow editing if:
# 1. User is super_admin (can edit anything)
# 2. User created the prediction (current logic)  
# 3. User is in same organization AND prediction is organization-level

if current_user.role == "super_admin":
    can_edit = True
elif prediction.created_by == str(current_user.id):
    can_edit = True  # Creator can always edit
elif (prediction.access_level == "organization" and 
      current_user.organization_id and 
      prediction.organization_id == current_user.organization_id and
      current_user.role in ["org_admin", "org_member"]):
    can_edit = True  # Organization members can edit org predictions
else:
    can_edit = False
```

### Option B: Strict Creator-Only Model (Current)
```python
# Allow editing if:
# 1. User is super_admin
# 2. User created the prediction
# This is most secure but may be too restrictive for teams
```

### Option C: Role-Based Organization Model
```python
# Allow editing if:
# 1. User is super_admin
# 2. User created the prediction  
# 3. User is org_admin and prediction is in their organization

if current_user.role == "super_admin":
    can_edit = True
elif prediction.created_by == str(current_user.id):
    can_edit = True
elif (current_user.role == "org_admin" and 
      current_user.organization_id and
      prediction.organization_id == current_user.organization_id):
    can_edit = True  # Org admins can edit org predictions
else:
    can_edit = False
```

## Questions for You:

1. **Organization Predictions**: Should organization members be able to edit/delete predictions within their organization?
   - Current: ❌ NO - Only creator can edit
   - Proposed: ✅ YES - Org members can edit org predictions

2. **Role Hierarchy**: What roles should have edit permissions?
   - `org_admin` only? 
   - Both `org_admin` AND `org_member`?
   - Different permissions for different roles?

3. **Access Level Scope**: Should this apply to all access levels or only "organization" level?
   - Only "organization" predictions?
   - "personal" predictions remain creator-only?
   - "system" predictions remain super_admin only?

## Current Behavior Summary:

| Prediction Type | Creator | Org Admin | Org Member | Super Admin | Other Users |
|----------------|---------|-----------|------------|-------------|-------------|
| Personal | ✅ Edit | ❌ No | ❌ No | ✅ Edit | ❌ No |
| Organization | ✅ Edit | ❌ No | ❌ No | ✅ Edit | ❌ No |
| System | ❌ No | ❌ No | ❌ No | ✅ Edit | ❌ No |

## Recommended Behavior:

| Prediction Type | Creator | Org Admin | Org Member | Super Admin | Other Users |
|----------------|---------|-----------|------------|-------------|-------------|
| Personal | ✅ Edit | ❌ No | ❌ No | ✅ Edit | ❌ No |
| Organization | ✅ Edit | ✅ Edit | 🤔 Edit? | ✅ Edit | ❌ No |
| System | ❌ No | ❌ No | ❌ No | ✅ Edit | ❌ No |
