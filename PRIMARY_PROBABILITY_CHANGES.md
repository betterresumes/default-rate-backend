# Primary Probability Field - Backend Changes & Frontend Integration Guide

## 🔧 Backend Changes Made

To fix the frontend error `"Cannot read properties of undefined (reading 'primary_probability')"`, I added the `primary_probability` field to **3 key locations** in the backend to ensure consistency across all API endpoints.

### 1. **Update Prediction Endpoint** (`src/routers/predictions.py`)

**Location:** Lines 1106-1107
```python
"probability": safe_float(updated_prediction.probability),
"primary_probability": safe_float(updated_prediction.probability),  # ← ADDED
```

**Full Context:**
```python
response_data["updated_prediction"] = {
    "type": "annual",
    "id": str(updated_prediction.id),
    "reporting_year": updated_prediction.reporting_year,
    "reporting_quarter": updated_prediction.reporting_quarter,
    "probability": safe_float(updated_prediction.probability),
    "primary_probability": safe_float(updated_prediction.probability),  # ← ADDED
    "risk_level": updated_prediction.risk_level,
    "confidence": safe_float(updated_prediction.confidence),
    "action": "replaced" if existing_prediction else "created",
    "financial_ratios": { ... }
}
```

### 2. **Companies List Endpoint** (`src/routers/companies.py`)

**Location:** Annual predictions serialization
```python
# For annual predictions in companies list
"probability": safe_float(pred.probability),
"primary_probability": safe_float(pred.probability),  # ← ADDED
```

**Full Context:**
```python
for pred in company.annual_predictions:
    company_data["annual_predictions"].append({
        "id": str(pred.id),
        "reporting_year": pred.reporting_year,
        "reporting_quarter": pred.reporting_quarter,
        "probability": safe_float(pred.probability),
        "primary_probability": safe_float(pred.probability),  # ← ADDED
        "risk_level": pred.risk_level,
        "confidence": safe_float(pred.confidence),
        "financial_ratios": { ... },
        "created_at": serialize_datetime(pred.created_at)
    })
```

### 3. **Bulk Processing Task** (`src/tasks.py`)

**Location:** Lines 472-473 in `process_bulk_normalized_task`
```python
"probability": safe_float(annual_prediction.probability),
"primary_probability": safe_float(annual_prediction.probability),  # ← ADDED
```

**Full Context:**
```python
result_item = {
    "stock_symbol": stock_symbol,
    "company_name": company_name,
    "sector": sector,
    "market_cap": market_cap,
    "prediction": {
        "id": str(annual_prediction.id),
        "type": "annual",
        "probability": safe_float(annual_prediction.probability),
        "primary_probability": safe_float(annual_prediction.probability),  # ← ADDED
        "risk_level": annual_prediction.risk_level,
        "confidence": safe_float(annual_prediction.confidence),
        "reporting_year": annual_prediction.reporting_year,
        "reporting_quarter": annual_prediction.reporting_quarter,
        "financial_ratios": ratios
    },
    "status": "success",
    "error_message": None
}
```

---

## 📋 API Response Structures

### **Update Prediction Endpoint Response**
```json
{
  "success": true,
  "message": "Company updated successfully",
  "company": {
    "id": "13048426-e209-4f13-8a88-fec050f6c7ef",
    "symbol": "HPE",
    "name": "Hewlett Packard Enterprise Company1",
    "market_cap": 1000.0,
    "sector": "Information Technology",
    "updated_at": "2025-09-16T15:53:16.050220"
  },
  "updated_prediction": {
    "type": "annual",
    "id": "b13b82d2-55b6-4d09-b5f5-d035bf5cd42d",
    "reporting_year": "2024",
    "reporting_quarter": null,
    "probability": 0.0231,
    "primary_probability": 0.0231,  // ← Available here
    "risk_level": "MEDIUM",
    "confidence": 0.9538,
    "action": "replaced",
    "financial_ratios": {
      "long_term_debt_to_total_capital": 0.35,
      "total_debt_to_ebitda": 2.5,
      "net_income_margin": 0.08,
      "ebit_to_interest_expense": 15.0,
      "return_on_assets": 0.06
    }
  }
}
```

### **Companies List Response**
```json
{
  "success": true,
  "companies": [
    {
      "id": "13048426-e209-4f13-8a88-fec050f6c7ef",
      "symbol": "HPE",
      "name": "Hewlett Packard Enterprise Company1",
      "market_cap": 1000.0,
      "sector": "Information Technology",
      "annual_predictions": [
        {
          "id": "a8e21263-8fb7-41d2-bd3b-f7994ec58402",
          "reporting_year": "2013",
          "reporting_quarter": "Q4",
          "probability": 0.0215,
          "primary_probability": 0.0215,  // ← Available here
          "risk_level": "MEDIUM",
          "confidence": 0.957,
          "financial_ratios": { ... },
          "created_at": "2025-09-16T04:58:46.535454"
        }
      ],
      "quarterly_predictions": [
        {
          "id": "...",
          "probabilities": {
            "logistic": 0.0234,
            "gbm": 0.0221,
            "ensemble": 0.0228
          },
          "primary_probability": 0.0228,  // ← Available here (ensemble value)
          "risk_level": "MEDIUM",
          "confidence": 0.9542
        }
      ]
    }
  ]
}
```

### **Bulk Processing Response**
```json
{
  "success": true,
  "message": "Bulk annual prediction completed. 100 successful, 0 failed.",
  "results": [
    {
      "stock_symbol": "AAPL",
      "company_name": "Apple Inc.",
      "prediction": {
        "id": "...",
        "type": "annual",
        "probability": 0.0231,
        "primary_probability": 0.0231,  // ← Available here
        "risk_level": "MEDIUM",
        "confidence": 0.9538,
        "financial_ratios": { ... }
      },
      "status": "success"
    }
  ]
}
```

---

## 🔧 Frontend Integration Guide

### **Common Issues & Solutions**

#### ❌ **Issue 1: Wrong Object Path**
```javascript
// Wrong - This will cause "Cannot read properties of undefined"
const probability = response.prediction.primary_probability;
```

```javascript
// ✅ Correct - Access the right object path
const probability = response.updated_prediction?.primary_probability;
```

#### ❌ **Issue 2: Missing Null Checks**
```javascript
// Wrong - Will fail if response is undefined
const probability = response.updated_prediction.primary_probability;
```

```javascript
// ✅ Correct - Use optional chaining and fallback
const probability = response.updated_prediction?.primary_probability ?? 0;
```

#### ❌ **Issue 3: Async Timing Issues**
```javascript
// Wrong - Accessing before response is received
fetch('/api/predictions/update/123', { ... });
const probability = response.updated_prediction.primary_probability; // undefined
```

```javascript
// ✅ Correct - Wait for response
const response = await fetch('/api/predictions/update/123', { ... });
const data = await response.json();
const probability = data.updated_prediction?.primary_probability ?? 0;
```

### **Endpoint-Specific Access Patterns**

#### **Update Prediction Endpoint**
```javascript
// PUT /api/predictions/update/{company_id}
const updateResponse = await fetch(`/api/predictions/update/${companyId}`, {
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    prediction_type: 'annual',
    reporting_year: '2024',
    long_term_debt_to_total_capital: 0.35,
    // ... other financial ratios
  })
});

const data = await updateResponse.json();

// ✅ Access primary_probability correctly
const primaryProbability = data.updated_prediction?.primary_probability;
const probability = data.updated_prediction?.probability;
const riskLevel = data.updated_prediction?.risk_level;
```

#### **Companies List Endpoint**
```javascript
// GET /api/predictions/companies
const companiesResponse = await fetch('/api/predictions/companies', {
  headers: { 'Authorization': `Bearer ${token}` }
});

const data = await companiesResponse.json();

// ✅ Access annual predictions
data.companies?.forEach(company => {
  company.annual_predictions?.forEach(prediction => {
    const primaryProbability = prediction.primary_probability;
    const probability = prediction.probability;
  });
  
  // ✅ Access quarterly predictions
  company.quarterly_predictions?.forEach(prediction => {
    const primaryProbability = prediction.primary_probability; // ensemble value
    const logisticProb = prediction.probabilities?.logistic;
    const gbmProb = prediction.probabilities?.gbm;
    const ensembleProb = prediction.probabilities?.ensemble;
  });
});
```

#### **Bulk Processing Results**
```javascript
// From bulk upload task results
const bulkResults = taskResult.results;

bulkResults?.forEach(result => {
  if (result.status === 'success') {
    const primaryProbability = result.prediction?.primary_probability;
    const probability = result.prediction?.probability;
    const type = result.prediction?.type; // 'annual' or 'quarterly'
  }
});
```

---

## 🧪 Testing Verification

### **Test Commands Used**
```bash
# Test update endpoint with proper parameters
curl -X PUT "http://localhost:8000/api/predictions/update/13048426-e209-4f13-8a88-fec050f6c7ef" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prediction_type": "annual",
    "reporting_year": "2024",
    "long_term_debt_to_total_capital": 0.35,
    "total_debt_to_ebitda": 2.5,
    "net_income_margin": 0.08,
    "ebit_to_interest_expense": 15.0,
    "return_on_assets": 0.06
  }'

# Verified response includes:
# ✅ "probability": 0.0231
# ✅ "primary_probability": 0.0231
```

### **Test Results**
- ✅ Update endpoint returns `primary_probability` when `prediction_type` and `reporting_year` are provided
- ✅ Companies list includes `primary_probability` for both annual and quarterly predictions
- ✅ Bulk processing tasks include `primary_probability` in results
- ✅ All values are properly handled with `safe_float()` function for null safety

---

## 📝 Key Differences by Prediction Type

### **Annual Predictions**
- `probability` = `primary_probability` (same value)
- Single probability value from logistic regression model

### **Quarterly Predictions**
- `primary_probability` = `ensemble_probability` (combined model result)
- Also includes separate `probabilities.logistic`, `probabilities.gbm`, `probabilities.ensemble`

---

## 🚀 Summary

The backend now consistently provides the `primary_probability` field across all prediction endpoints. The frontend error should be resolved by:

1. **Using correct object paths** (`response.updated_prediction.primary_probability`)
2. **Adding null safety** with optional chaining (`?.`)
3. **Handling async operations** properly with `await`

All API endpoints have been tested and confirmed to include the `primary_probability` field as expected.
