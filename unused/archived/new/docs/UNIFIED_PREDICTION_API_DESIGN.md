# 🎯 Enhanced Prediction API Design (Unified Approach)

## 📊 **Unified Prediction Endpoints**

### 🔥 **Core Prediction Management**
```python
# Main prediction endpoints
GET  /predictions/                     - List all predictions with filters
POST /predictions/                     - Create prediction (annual/quarterly)
GET  /predictions/{id}                 - Get specific prediction details
PUT  /predictions/{id}                 - Update prediction
DELETE /predictions/{id}               - Delete prediction

# Bulk operations
POST /predictions/bulk                 - Bulk upload predictions
GET  /predictions/jobs/{job_id}        - Check bulk job status
POST /predictions/jobs/{job_id}/cancel - Cancel bulk job
```

### 🎨 **Advanced Filtering (Query Parameters)**
```python
# Filter by prediction type
GET /predictions/?type=annual          - Only annual predictions
GET /predictions/?type=quarterly       - Only quarterly predictions  
GET /predictions/?type=annual,quarterly - Both types

# Filter by data scope
GET /predictions/?scope=personal       - My personal predictions
GET /predictions/?scope=organization   - My organization predictions
GET /predictions/?scope=global         - Global predictions (admin only)

# Filter by company
GET /predictions/?company_id=uuid      - Predictions for specific company
GET /predictions/?company_symbol=AAPL  - Predictions by stock symbol

# Filter by time
GET /predictions/?reporting_year=2024  - Predictions for 2024
GET /predictions/?reporting_quarter=Q4 - Q4 predictions only
GET /predictions/?created_after=2024-01-01 - Recent predictions

# Filter by risk/performance
GET /predictions/?risk_level=HIGH      - High risk predictions
GET /predictions/?confidence_min=0.8   - High confidence predictions
GET /predictions/?probability_max=0.3  - Low default probability

# Filter by creator/organization
GET /predictions/?created_by=user-id   - Predictions by specific user
GET /predictions/?organization_id=org-id - Specific organization

# Pagination & Sorting
GET /predictions/?page=1&limit=20      - Paginated results
GET /predictions/?sort_by=created_at&order=desc - Sort by date
GET /predictions/?sort_by=probability&order=asc  - Sort by risk
```

### 🎯 **Convenience Endpoints (Shortcuts)**
```python
# Quick access endpoints
GET /predictions/mine                  - My predictions (personal + org)
GET /predictions/recent                - Recent predictions (last 30 days)
GET /predictions/high-risk             - High risk predictions (prob > 0.7)
GET /predictions/companies/{company_id} - All predictions for company

# Dashboard endpoints
GET /predictions/dashboard             - Dashboard summary data
GET /predictions/analytics             - Prediction analytics
GET /predictions/export                - Export predictions (CSV/Excel)
```

## 📋 **Request/Response Examples**

### 🔥 **Create Annual Prediction**
```python
POST /predictions/
{
    "type": "annual",
    "company_id": "company-uuid",
    "reporting_year": "2024",
    "scope": "organization",  # or "personal"
    
    # Annual-specific fields
    "long_term_debt_to_total_capital": 0.25,
    "total_debt_to_ebitda": 3.2,
    "net_income_margin": 0.15,
    "ebit_to_interest_expense": 8.5,
    "return_on_assets": 0.12
}
```

### ⚡ **Create Quarterly Prediction**
```python
POST /predictions/
{
    "type": "quarterly", 
    "company_id": "company-uuid",
    "reporting_year": "2024",
    "reporting_quarter": "Q4",
    "scope": "personal",
    
    # Quarterly-specific fields
    "total_debt_to_ebitda": 3.2,
    "sga_margin": 0.18,
    "long_term_debt_to_total_capital": 0.25,
    "return_on_capital": 0.14
}
```

### 📊 **Response Format**
```python
{
    "success": true,
    "data": {
        "id": "prediction-uuid",
        "type": "annual",  # or "quarterly"
        "company": {
            "id": "company-uuid",
            "symbol": "AAPL",
            "name": "Apple Inc."
        },
        "organization_id": "org-uuid",  # null for personal
        "scope": "organization",
        "reporting_year": "2024",
        "reporting_quarter": null,  # for annual
        
        # Prediction results
        "probability": 0.23,
        "risk_level": "LOW",
        "confidence": 0.85,
        
        # Metadata
        "created_by": "user-uuid", 
        "created_at": "2024-01-15T10:30:00Z",
        "predicted_at": "2024-01-15T10:30:00Z"
    }
}
```

### 🎨 **List Predictions with Filters**
```python
GET /predictions/?type=quarterly&scope=organization&reporting_year=2024&limit=10

{
    "success": true,
    "data": [
        {
            "id": "pred-1",
            "type": "quarterly",
            "company": {...},
            "reporting_quarter": "Q4",
            "probability": 0.15,
            "risk_level": "LOW"
        },
        {...}
    ],
    "pagination": {
        "page": 1,
        "limit": 10,
        "total": 45,
        "pages": 5
    },
    "filters_applied": {
        "type": "quarterly",
        "scope": "organization", 
        "reporting_year": "2024"
    }
}
```

## 🔧 **Implementation Benefits**

### ✅ **Advantages of Unified Approach**
1. **🎯 Single Source of Truth**: One endpoint for all predictions
2. **🔍 Powerful Filtering**: Combine multiple filters easily
3. **📊 Dashboard-Friendly**: Perfect for analytics dashboards
4. **🚀 Performance**: Efficient single queries vs multiple endpoints
5. **👥 User Experience**: Intuitive and consistent API design
6. **🔄 Future-Proof**: Easy to add monthly/weekly prediction types

### 📱 **Frontend Benefits**
```javascript
// Single API call for dashboard
const predictions = await fetch('/predictions/?scope=organization&recent=true');

// Easy filtering
const quarterlyRisk = await fetch('/predictions/?type=quarterly&risk_level=HIGH');

// Company analysis
const companyPreds = await fetch('/predictions/?company_symbol=AAPL&type=annual,quarterly');
```

### 📊 **Analytics Benefits**
```python
# Easy analytics queries
GET /predictions/?group_by=risk_level&type=quarterly
GET /predictions/?aggregate=avg_probability&scope=organization
GET /predictions/?trend=monthly&reporting_year=2024
```

## 🎯 **Conclusion**

**This unified approach gives you:**
- 🔥 **Flexibility**: Handle both annual & quarterly seamlessly
- 📊 **Power**: Advanced filtering and analytics
- 🚀 **Performance**: Efficient single endpoint
- 👥 **Usability**: Simple, intuitive API design

**Is this approach better than separate endpoints?** Absolutely! It's more professional, flexible, and future-proof.

Would you like me to implement this unified prediction API design?
