# 🔒 FINAL DATA ACCESS RULES - Personal Predictions Privacy

## **📊 Complete Data Access Matrix**

### **Prediction Types & Visibility:**

| Prediction Type | organization_id | created_by | Visible To |
|-----------------|-----------------|------------|------------|
| **Global Predictions** | `null` | `super_admin_id` | **ALL users** (public data) |
| **Organization Predictions** | `org_id` | `org_member_id` | **Organization members only** |
| **Personal Predictions** | `null` | `regular_user_id` | **Creator + Super admin only** |

---

## **🔍 Data Access Examples:**

### **1. Super Admin (global_role = "super_admin")**
```python
# CAN SEE: Everything
predictions = db.query(AnnualPrediction).all()  # No filters needed

# ✅ Global predictions (by super admin)
# ✅ All organization predictions  
# ✅ All personal predictions (all users)
# ✅ Platform oversight capability
```

### **2. Organization Admin/User (organization_id = org1)**
```python
# CAN SEE: Global + Own org predictions only
predictions = db.query(AnnualPrediction).filter(
    or_(
        # Global predictions (by super admin)
        and_(
            AnnualPrediction.organization_id.is_(None),
            AnnualPrediction.created_by.in_(super_admin_ids)
        ),
        # Own organization predictions
        AnnualPrediction.organization_id == current_user.organization_id
    )
).all()

# ✅ Global predictions (by super admin)
# ✅ Own organization predictions
# ❌ Other organizations' predictions
# ❌ Personal predictions (by other users)
```

### **3. Personal User (organization_id = null)**
```python
# CAN SEE: Global + Own personal predictions only
predictions = db.query(AnnualPrediction).filter(
    or_(
        # Global predictions (by super admin)  
        and_(
            AnnualPrediction.organization_id.is_(None),
            AnnualPrediction.created_by.in_(super_admin_ids)
        ),
        # Own personal predictions
        and_(
            AnnualPrediction.organization_id.is_(None),
            AnnualPrediction.created_by == current_user.id
        )
    )
).all()

# ✅ Global predictions (by super admin)
# ✅ Own personal predictions
# ❌ Organization predictions  
# ❌ Other users' personal predictions
```

---

## **🛡️ Privacy Guarantees:**

### **Personal Predictions are 100% Private:**
```python
# John's personal prediction
prediction = {
    "id": "pred-123",
    "company_id": "AAPL", 
    "organization_id": None,      # No organization
    "created_by": "john-user-id", # John created it
    "probability": 0.0234,
    "risk_level": "Low"
}

# Who can see this prediction?
# ✅ John (creator)
# ✅ Super admin (platform oversight)
# ❌ HDFC Bank users (different org)
# ❌ ICICI Bank users (different org)  
# ❌ Other personal users (not the creator)
```

### **Organization Predictions are Org-Private:**
```python
# HDFC's organization prediction
prediction = {
    "id": "pred-456", 
    "company_id": "HDFCBANK",
    "organization_id": "hdfc-org-id",  # HDFC organization
    "created_by": "hdfc-user-id",      # HDFC employee
    "probability": 0.0456,
    "risk_level": "Medium"
}

# Who can see this prediction?
# ✅ All HDFC Bank users (same org)
# ✅ Super admin (platform oversight)
# ❌ ICICI Bank users (different org)
# ❌ Personal users (no org access)
```

### **Global Predictions are Public:**
```python
# Super admin's global prediction
prediction = {
    "id": "pred-789",
    "company_id": "RELIANCE", 
    "organization_id": None,           # Global
    "created_by": "super-admin-id",    # Super admin created
    "probability": 0.0123,
    "risk_level": "Low"
}

# Who can see this prediction?
# ✅ ALL users (global data)
# ✅ HDFC Bank users
# ✅ ICICI Bank users  
# ✅ Personal users
# ✅ Super admin
```

---

## **🔐 Implementation in Code:**

### **Data Access Helper Function:**
```python
def get_accessible_predictions(db: Session, current_user: User, prediction_model):
    """Get predictions accessible to current user"""
    
    # Super admin sees everything
    if current_user.global_role == "super_admin":
        return db.query(prediction_model).all()
    
    # Build access filter
    access_filters = []
    
    # 1. Global predictions (by super admin)
    super_admin_ids = db.query(User.id).filter(
        User.global_role == "super_admin"
    ).subquery()
    
    access_filters.append(
        and_(
            prediction_model.organization_id.is_(None),
            prediction_model.created_by.in_(super_admin_ids)
        )
    )
    
    # 2. Organization predictions (if user has org)
    if current_user.organization_id:
        access_filters.append(
            prediction_model.organization_id == current_user.organization_id
        )
    
    # 3. Personal predictions (own only)
    access_filters.append(
        and_(
            prediction_model.organization_id.is_(None),
            prediction_model.created_by == current_user.id
        )
    )
    
    return db.query(prediction_model).filter(or_(*access_filters)).all()
```

---

## **✅ Perfect Privacy Model:**

1. **Personal = Private** (Creator + Super admin only)
2. **Organization = Team-shared** (Organization members + Super admin)  
3. **Global = Public** (Everyone can see)
4. **Super Admin = Full oversight** (Platform management)

**This ensures maximum privacy while enabling collaboration!** 

**Ready to implement this complete multi-tenant system with perfect data isolation? 🚀**
