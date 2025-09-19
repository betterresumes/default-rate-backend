# 🔐 Permission Matrix

## Global Roles vs Organization Roles

### 🌍 **Global Roles** (System-wide)
- **super_admin**: Full system access, can create/delete orgs, manage all users
- **admin**: Can create organizations, manage global settings
- **user**: Regular user, can join organizations

### 🏢 **Organization Roles** (Within each organization)
- **admin**: Manages the organization, invites users, assigns roles
- **member**: Creates predictions, views org data
- **viewer**: Read-only access to org data

---

## 📊 **Permission Matrix**

| Action | Super Admin | Global Admin | Org Admin | Org Member | Org Viewer |
|--------|-------------|--------------|-----------|------------|------------|
| **System Management** |
| Create Organizations | ✅ | ✅ | ❌ | ❌ | ❌ |
| Delete Organizations | ✅ | ❌ | ❌ | ❌ | ❌ |
| View All Organizations | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Organization Management** |
| Edit Org Settings | ✅ | ❌ | ✅ | ❌ | ❌ |
| Invite Users to Org | ✅ | ❌ | ✅ | ❌ | ❌ |
| Remove Users from Org | ✅ | ❌ | ✅ | ❌ | ❌ |
| **Role Management** |
| Make User Org Admin | ✅ | ❌ | ✅ | ❌ | ❌ |
| Make User Global Admin | ✅ | ❌ | ❌ | ❌ | ❌ |
| Make User Super Admin | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Data Access** |
| View Global Data | ✅ | ✅ | ✅ | ✅ | ✅ |
| View Own Org Data | ✅ | ✅ | ✅ | ✅ | ✅ |
| View Other Org Data | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Company Management** |
| Create Global Companies | ✅ | ✅ | ❌ | ❌ | ❌ |
| Create Org Companies | ✅ | ❌ | ✅ | ✅ | ❌ |
| Edit Org Companies | ✅ | ❌ | ✅ | ✅ | ❌ |
| **Prediction Management** |
| Create Predictions | ✅ | ✅ | ✅ | ✅ | ❌ |
| View Own Predictions | ✅ | ✅ | ✅ | ✅ | ✅ |
| View Org Predictions | ✅ | ❌ | ✅ | ✅ | ✅ |
| View All Predictions | ✅ | ❌ | ❌ | ❌ | ❌ |

---

## 🎯 **Key Examples**

### Scenario 1: HDFC Bank Organization
```
Organization: HDFC Bank
├── Alice (org admin) 
├── Bob (org member)
└── Carol (org viewer)

✅ Alice can:
- Invite new HDFC Bank employees
- Make Bob an org admin  
- Create HDFC-specific companies
- View all HDFC predictions

❌ Alice cannot:
- Make Bob a global admin
- Access Reliance Industries data
- Delete HDFC Bank organization
```

### Scenario 2: Creating Multiple Admins
```python
# Org admin Alice invites Bob and makes him admin too
POST /organizations/hdfc-bank-id/invite
{
    "email": "bob@hdfcbank.com",
    "organization_role": "admin"  # Alice can assign admin role
}

# But Alice cannot do this:
POST /users/bob-id/global-role
{
    "global_role": "admin"  # ❌ Only super_admin can do this
}
```

---

## 🔧 **Implementation in Code**

The permission checks are handled automatically by the auth dependencies:

```python
# Organization admin can invite users
@router.post("/organizations/{org_id}/invite")
async def invite_user(
    user: User = Depends(require_organization_admin)  # ✅ Checks org admin
):
    # Can assign organization roles only
    pass

# Only super admin can change global roles  
@router.put("/users/{user_id}/global-role")
async def update_global_role(
    user: User = Depends(require_super_admin)  # ✅ Requires super admin
):
    # Can change global_role: admin, super_admin
    pass
```

This ensures **secure role management** with clear boundaries! 🔒
