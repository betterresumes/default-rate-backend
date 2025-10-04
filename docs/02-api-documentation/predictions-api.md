# ML Predictions API

This document explains how to generate financial risk predictions using AccuNode's machine learning models. AccuNode provides two types of predictions: **Annual** and **Quarterly**.

## Predictions Overview

AccuNode uses machine learning models to predict financial risk based on company ratios:

### Annual Predictions 📅
- **Purpose**: Long-term risk assessment (yearly trends)
- **Ratios Used**: 5 key financial ratios
- **Model**: Logistic Regression with binned scoring
- **Score Range**: 1-10 (1 = lowest risk, 10 = highest risk)

### Quarterly Predictions 📊  
- **Purpose**: Short-term risk assessment (quarterly trends)
- **Ratios Used**: 4 key financial ratios
- **Model**: Ensemble (Logistic Regression + LightGBM)
- **Score Range**: 1-10 (1 = lowest risk, 10 = highest risk)

## Base Information

- **Base URL**: `/api/v1/predictions`
- **Authentication**: Bearer token required
- **Access Control**: Organization-based (predict for your companies only)

| Endpoint | Purpose | Model Type |
|----------|---------|------------|
| POST /predictions/annual | Generate annual prediction | Logistic Regression |
| POST /predictions/quarterly | Generate quarterly prediction | Ensemble Model |

## Annual Predictions

### Required Financial Ratios

| Ratio Name | Description | Formula | Example |
|------------|-------------|---------|---------|
| **Current Ratio** | Liquidity measure | Current Assets ÷ Current Liabilities | 2.1 |
| **Quick Ratio** | Immediate liquidity | (Current Assets - Inventory) ÷ Current Liabilities | 1.8 |
| **Debt to Equity** | Leverage measure | Total Debt ÷ Total Equity | 0.45 |
| **Return on Assets** | Asset efficiency | Net Income ÷ Total Assets | 0.12 |
| **Profit Margin** | Profitability | Net Income ÷ Revenue | 0.08 |

### 1. Generate Annual Prediction 🎯

**Endpoint**: `POST /api/v1/predictions/annual`

**What it does**: Creates a risk prediction using annual financial ratios

**Authentication**: Required (Bearer token)

**Request Example**:
```json
{
  "company_id": "comp-abc123...",
  "current_ratio": 2.1,
  "quick_ratio": 1.8,
  "debt_to_equity": 0.45,
  "return_on_assets": 0.12,
  "profit_margin": 0.08
}
```

**Response Example**:
```json
{
  "id": "pred-annual-xyz789...",
  "company_id": "comp-abc123...",
  "prediction_type": "annual",
  "risk_score": 3.2,
  "risk_category": "low_risk",
  "prediction_date": "2024-10-05T16:30:00Z",
  "model_version": "v2.1.0",
  "input_ratios": {
    "current_ratio": 2.1,
    "quick_ratio": 1.8, 
    "debt_to_equity": 0.45,
    "return_on_assets": 0.12,
    "profit_margin": 0.08
  },
  "risk_factors": {
    "positive_indicators": [
      "Strong current ratio indicates good liquidity",
      "Healthy profit margin shows profitability"
    ],
    "risk_indicators": [
      "Debt to equity ratio could be improved"
    ]
  },
  "confidence_score": 0.87,
  "created_at": "2024-10-05T16:30:00Z"
}
```

## Quarterly Predictions

### Required Financial Ratios

| Ratio Name | Description | Formula | Example |
|------------|-------------|---------|---------|
| **Debt to Equity** | Leverage measure | Total Debt ÷ Total Equity | 0.52 |
| **Current Ratio** | Liquidity measure | Current Assets ÷ Current Liabilities | 1.9 |
| **Return on Equity** | Equity efficiency | Net Income ÷ Shareholders' Equity | 0.15 |
| **Asset Turnover** | Asset utilization | Revenue ÷ Total Assets | 1.2 |

### 2. Generate Quarterly Prediction 📈

**Endpoint**: `POST /api/v1/predictions/quarterly`

**What it does**: Creates a risk prediction using quarterly financial ratios

**Authentication**: Required (Bearer token)

**Request Example**:
```json
{
  "company_id": "comp-abc123...",
  "debt_to_equity": 0.52,
  "current_ratio": 1.9,
  "return_on_equity": 0.15,
  "asset_turnover": 1.2
}
```

**Response Example**:
```json
{
  "id": "pred-quarterly-xyz456...",
  "company_id": "comp-abc123...",
  "prediction_type": "quarterly", 
  "risk_score": 4.1,
  "risk_category": "moderate_risk",
  "prediction_date": "2024-10-05T16:35:00Z",
  "model_version": "v1.8.0",
  "input_ratios": {
    "debt_to_equity": 0.52,
    "current_ratio": 1.9,
    "return_on_equity": 0.15,
    "asset_turnover": 1.2
  },
  "model_breakdown": {
    "logistic_regression_score": 4.3,
    "lightgbm_score": 3.9,
    "ensemble_weight": 0.6,
    "final_score": 4.1
  },
  "risk_factors": {
    "positive_indicators": [
      "Good return on equity shows efficient use of capital",
      "Reasonable asset turnover indicates operational efficiency"
    ],
    "risk_indicators": [
      "Debt to equity ratio is moderately high",
      "Current ratio below optimal range"
    ]
  },
  "confidence_score": 0.82,
  "created_at": "2024-10-05T16:35:00Z"
}
```

## Risk Categories

### Risk Score Interpretation

| Score Range | Category | Color | Meaning |
|-------------|----------|-------|---------|
| **1.0 - 3.0** | Low Risk | 🟢 Green | Company shows strong financial health |
| **3.1 - 6.0** | Moderate Risk | 🟡 Yellow | Some financial concerns, monitor closely |
| **6.1 - 10.0** | High Risk | 🔴 Red | Significant financial stress indicators |

### What Each Category Means

**Low Risk (1-3)**:
- Strong liquidity position
- Manageable debt levels
- Good profitability metrics
- Low probability of financial distress

**Moderate Risk (4-6)**:
- Some liquidity concerns
- Elevated debt levels
- Mixed profitability signals
- Requires monitoring and attention

**High Risk (7-10)**:
- Liquidity problems
- High debt burden
- Poor profitability
- High probability of financial difficulties

## Access Control & Validation

### Organization Access
- Can only create predictions for companies in your organization
- Cannot predict for companies from other organizations
- System automatically validates company ownership

### Role Requirements
| Role | Can Create Annual | Can Create Quarterly |
|------|-------------------|---------------------|
| **user** | ❌ No | ❌ No |
| **org_member** | ✅ Yes | ✅ Yes |
| **org_admin** | ✅ Yes | ✅ Yes |
| **tenant_admin** | ✅ Yes | ✅ Yes |
| **super_admin** | ✅ Yes | ✅ Yes |

### Ratio Validation Rules

**All ratios must be**:
- ✅ Numeric values (decimals allowed)
- ✅ Non-null (required fields)
- ✅ Within reasonable business ranges

**Specific validations**:
- **Current Ratio**: Must be > 0 (typically 0.5 - 10.0)
- **Quick Ratio**: Must be > 0 (typically 0.3 - 8.0)  
- **Debt to Equity**: Must be ≥ 0 (typically 0.0 - 5.0)
- **Return on Assets**: Can be negative (typically -1.0 to 1.0)
- **Profit Margin**: Can be negative (typically -1.0 to 1.0)
- **Return on Equity**: Can be negative (typically -2.0 to 2.0)
- **Asset Turnover**: Must be > 0 (typically 0.1 - 5.0)

## Common Error Messages

| Error Code | Error Message | What It Means | What To Do |
|------------|---------------|---------------|------------|
| **400** | "Current ratio must be greater than 0" | Invalid ratio value | Check ratio calculation |
| **400** | "Profit margin must be between -1 and 1" | Ratio out of range | Verify profit margin is in decimal form |
| **403** | "Company not in your organization" | Access denied | Use company from your organization |
| **404** | "Company not found" | Invalid company ID | Check company ID exists |
| **422** | "Missing required field: current_ratio" | Missing ratio | Provide all required ratios |
| **500** | "ML model prediction failed" | Model error | Try again or contact support |

## Integration Examples

### Using with JavaScript
```javascript
class PredictionsAPI {
  constructor(baseUrl, token) {
    this.baseUrl = baseUrl;
    this.token = token;
  }

  async createAnnualPrediction(companyId, ratios) {
    const response = await fetch(`${this.baseUrl}/api/v1/predictions/annual`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        company_id: companyId,
        current_ratio: ratios.currentRatio,
        quick_ratio: ratios.quickRatio,
        debt_to_equity: ratios.debtToEquity,
        return_on_assets: ratios.returnOnAssets,
        profit_margin: ratios.profitMargin
      })
    });
    return response.json();
  }

  async createQuarterlyPrediction(companyId, ratios) {
    const response = await fetch(`${this.baseUrl}/api/v1/predictions/quarterly`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        company_id: companyId,
        debt_to_equity: ratios.debtToEquity,
        current_ratio: ratios.currentRatio,
        return_on_equity: ratios.returnOnEquity,
        asset_turnover: ratios.assetTurnover
      })
    });
    return response.json();
  }

  getRiskCategory(score) {
    if (score <= 3.0) return { category: 'Low Risk', color: 'green' };
    if (score <= 6.0) return { category: 'Moderate Risk', color: 'yellow' };
    return { category: 'High Risk', color: 'red' };
  }
}

// Usage example
const api = new PredictionsAPI('http://localhost:8000', 'your_jwt_token');

// Create annual prediction
const annualPrediction = await api.createAnnualPrediction('comp-123', {
  currentRatio: 2.1,
  quickRatio: 1.8,
  debtToEquity: 0.45,
  returnOnAssets: 0.12,
  profitMargin: 0.08
});

console.log(`Risk Score: ${annualPrediction.risk_score}`);
console.log(`Category: ${annualPrediction.risk_category}`);

// Create quarterly prediction  
const quarterlyPrediction = await api.createQuarterlyPrediction('comp-123', {
  debtToEquity: 0.52,
  currentRatio: 1.9,
  returnOnEquity: 0.15,
  assetTurnover: 1.2
});

console.log(`Risk Score: ${quarterlyPrediction.risk_score}`);
console.log(`Confidence: ${quarterlyPrediction.confidence_score}`);
```

### Using with Python
```python
import requests

class AccuNodePredictions:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def create_annual_prediction(self, company_id, **ratios):
        """
        Create annual prediction
        Required ratios: current_ratio, quick_ratio, debt_to_equity, 
                        return_on_assets, profit_margin
        """
        data = {
            'company_id': company_id,
            **ratios
        }
        
        response = requests.post(
            f"{self.base_url}/api/v1/predictions/annual",
            headers=self.headers,
            json=data
        )
        return response.json()
    
    def create_quarterly_prediction(self, company_id, **ratios):
        """
        Create quarterly prediction  
        Required ratios: debt_to_equity, current_ratio, 
                        return_on_equity, asset_turnover
        """
        data = {
            'company_id': company_id,
            **ratios
        }
        
        response = requests.post(
            f"{self.base_url}/api/v1/predictions/quarterly",
            headers=self.headers,
            json=data
        )
        return response.json()
    
    def update_annual_prediction(self, prediction_id, **data):
        """
        Update annual prediction
        Required: company_symbol, company_name, market_cap, sector, 
                  reporting_year, current_ratio, quick_ratio, debt_to_equity,
                  return_on_assets, profit_margin
        """
        response = requests.put(
            f"{self.base_url}/api/v1/predictions/annual/{prediction_id}",
            headers=self.headers,
            json=data
        )
        return response.json()
    
    def update_quarterly_prediction(self, prediction_id, **data):
        """
        Update quarterly prediction  
        Required: company_symbol, company_name, market_cap, sector,
                  reporting_year, reporting_quarter, debt_to_equity, 
                  current_ratio, return_on_equity, asset_turnover
        """
        response = requests.put(
            f"{self.base_url}/api/v1/predictions/quarterly/{prediction_id}",
            headers=self.headers,
            json=data
        )
        return response.json()

    def get_risk_category(self, score):
        if score <= 3.0:
            return {'category': 'Low Risk', 'color': 'green'}
        elif score <= 6.0:
            return {'category': 'Moderate Risk', 'color': 'yellow'}  
        else:
            return {'category': 'High Risk', 'color': 'red'}

# Usage example
predictions_api = AccuNodePredictions('http://localhost:8000', 'your_jwt_token')

# Annual prediction
annual_result = predictions_api.create_annual_prediction(
    company_id='comp-123',
    current_ratio=2.1,
    quick_ratio=1.8,
    debt_to_equity=0.45,
    return_on_assets=0.12,
    profit_margin=0.08
)

print(f"Annual Risk Score: {annual_result['risk_score']}")
print(f"Risk Category: {annual_result['risk_category']}")

# Quarterly prediction
quarterly_result = predictions_api.create_quarterly_prediction(
    company_id='comp-123',
    debt_to_equity=0.52,
    current_ratio=1.9,
    return_on_equity=0.15,
    asset_turnover=1.2
)

print(f"Quarterly Risk Score: {quarterly_result['risk_score']}")
print(f"Model Confidence: {quarterly_result['confidence_score']}")

# Update annual prediction
updated_annual = predictions_api.update_annual_prediction(
    prediction_id='pred-annual-123',
    company_symbol='AAPL',
    company_name='Apple Inc. (Updated)',
    market_cap=3000000,
    sector='Technology',
    reporting_year='2024',
    current_ratio=2.3,
    quick_ratio=2.0,
    debt_to_equity=0.40,
    return_on_assets=0.15,
    profit_margin=0.10
)

print(f"Updated Annual: {updated_annual['prediction']['ml_results']['probability']}")

# Update quarterly prediction  
updated_quarterly = predictions_api.update_quarterly_prediction(
    prediction_id='pred-quarterly-456',
    company_symbol='GOOGL',
    company_name='Alphabet Inc. (Updated)',
    market_cap=1800000,
    sector='Technology', 
    reporting_year='2024',
    reporting_quarter='Q3',
    debt_to_equity=0.48,
    current_ratio=2.1,
    return_on_equity=0.18,
    asset_turnover=1.3
)

print(f"Updated Quarterly: {updated_quarterly['prediction']['ml_results']['ensemble_probability']}")
```

## Model Information

### Annual Model Details
- **Algorithm**: Logistic Regression
- **Training Data**: Historical financial data with known outcomes
- **Features**: 5 financial ratios with interaction terms
- **Scoring**: Binned probability approach for risk categorization
- **Accuracy**: 85%+ on validation data

### Quarterly Model Details  
- **Algorithm**: Ensemble (60% Logistic Regression + 40% LightGBM)
- **Training Data**: Quarterly financial reports with 3-month outcomes
- **Features**: 4 financial ratios with derived features
- **Scoring**: Weighted average of both model predictions  
- **Accuracy**: 82%+ on validation data

### Model Updates
- Models are retrained quarterly with new data
- Version numbers track model updates
- Backward compatibility maintained for API responses

The ML Predictions API provides state-of-the-art financial risk assessment powered by machine learning models trained on real financial data.
