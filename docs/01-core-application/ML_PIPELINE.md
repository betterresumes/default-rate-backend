# 🤖 Machine Learning Pipeline Architecture

## 📋 **Table of Contents**
1. [ML Pipeline Overview](#ml-pipeline-overview)
2. [Model Architecture](#model-architecture)
3. [Annual Prediction Pipeline](#annual-prediction-pipeline)
4. [Quarterly Prediction Pipeline](#quarterly-prediction-pipeline)
5. [Feature Engineering](#feature-engineering)
6. [Model Ensemble Strategy](#model-ensemble-strategy)
7. [Risk Categorization System](#risk-categorization-system)
8. [Performance Monitoring](#performance-monitoring)

---

## 🎯 **ML Pipeline Overview**

AccuNode implements a sophisticated **dual-pipeline ML system** for corporate default prediction, with separate optimized models for annual and quarterly financial data analysis.

### **ML Architecture Diagram**
```
┌─────────────────────────────────────────────────────────────────┐
│                    INPUT DATA SOURCES                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Annual    │  │ Quarterly   │  │   Market    │            │
│  │ Financials  │  │ Financials  │  │    Data     │            │
│  │(5 Ratios)   │  │(6 Ratios)   │  │(External)   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                DATA PREPROCESSING                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ Validation  │  │   Scaling   │  │  Feature    │            │
│  │ & Cleaning  │  │ & Normali.  │  │Engineering  │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                 ML INFERENCE ENGINE                            │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐│
│  │      ANNUAL PIPELINE        │  │    QUARTERLY PIPELINE       ││
│  │  ┌─────────┐ ┌─────────┐    │  │ ┌─────────┐ ┌─────────┐   ││
│  │  │Logistic │ │  Step   │    │  │ │Logistic │ │LightGBM │   ││
│  │  │Regres.  │ │Function │    │  │ │Regres.  │ │ Model   │   ││
│  │  └─────────┘ └─────────┘    │  │ └─────────┘ └─────────┘   ││
│  │       │         │           │  │      │          │        ││
│  │       └─────────┼───────────┤  │      │     ┌─────────┐   ││
│  │              Ensemble       │  │      │     │  Step   │   ││
│  │             (Weighted)      │  │      │     │Function │   ││
│  └─────────────────────────────┘  │      │     └─────────┘   ││
│                                   │      └─────────┼─────────┤│
│                                   │             Ensemble     ││
│                                   │            (Advanced)    ││
│                                   └─────────────────────────────┘│
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                 OUTPUT PROCESSING                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │    Risk     │  │ Confidence  │  │  Result     │            │
│  │Categoriza.  │  │ Calculation │  │ Validation  │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                 PREDICTION OUTPUT                              │
│    Default Probability + Risk Level + Confidence Score        │
└─────────────────────────────────────────────────────────────────┘
```

### **ML Technology Stack**
| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Core ML Framework** | Scikit-learn | 1.3+ | Logistic Regression, preprocessing |
| **Gradient Boosting** | LightGBM | 4.0+ | Advanced ensemble model |
| **Data Processing** | Pandas | 2.0+ | Data manipulation and analysis |
| **Numerical Computing** | NumPy | 1.24+ | Mathematical operations |
| **Model Serialization** | Pickle/Joblib | Built-in | Model persistence |
| **Feature Scaling** | StandardScaler | Scikit-learn | Feature normalization |

---

## 🏗️ **Model Architecture**

### **Model Storage Structure**
```
/app/models/
├── annual_logistic_model.pkl       # Annual Logistic Regression
├── annual_step.pkl                 # Annual Step Function Model
├── scoring_info.pkl                # Annual Feature Scaler
├── quarterly_lgb_model.pkl         # Quarterly LightGBM Model
├── quarterly_logistic_model.pkl    # Quarterly Logistic Regression
├── quarterly_step.pkl              # Quarterly Step Function
├── quarterly_scoring_info.pkl      # Quarterly Feature Scaler
└── model_metadata.json             # Model version and info
```

### **Model Loading and Management**
```python
class MLModelManager:
    """Centralized ML model management system"""
    
    def __init__(self, model_path: str = "/app/models"):
        self.model_path = Path(model_path)
        self.models = {}
        self.scalers = {}
        self.metadata = {}
        self._load_all_models()
    
    def _load_all_models(self):
        """Load all ML models and scalers at startup"""
        try:
            # Annual Models
            self.models['annual_logistic'] = joblib.load(
                self.model_path / 'annual_logistic_model.pkl'
            )
            self.models['annual_step'] = joblib.load(
                self.model_path / 'annual_step.pkl'
            )
            self.scalers['annual'] = joblib.load(
                self.model_path / 'scoring_info.pkl'
            )
            
            # Quarterly Models
            self.models['quarterly_lgb'] = joblib.load(
                self.model_path / 'quarterly_lgb_model.pkl'
            )
            self.models['quarterly_logistic'] = joblib.load(
                self.model_path / 'quarterly_logistic_model.pkl'
            )
            self.models['quarterly_step'] = joblib.load(
                self.model_path / 'quarterly_step.pkl'
            )
            self.scalers['quarterly'] = joblib.load(
                self.model_path / 'quarterly_scoring_info.pkl'
            )
            
            # Load metadata
            with open(self.model_path / 'model_metadata.json', 'r') as f:
                self.metadata = json.load(f)
                
            logger.info("All ML models loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load ML models: {e}")
            raise MLModelLoadError(f"Model loading failed: {e}")
    
    def get_model_info(self) -> dict:
        """Get information about loaded models"""
        return {
            "models_loaded": list(self.models.keys()),
            "scalers_loaded": list(self.scalers.keys()),
            "metadata": self.metadata,
            "model_path": str(self.model_path)
        }
```

### **Model Validation and Health Checks**
```python
class ModelValidator:
    """Validate model integrity and performance"""
    
    @staticmethod
    def validate_model_predictions(model, test_data: np.ndarray) -> bool:
        """Validate that model produces reasonable outputs"""
        try:
            predictions = model.predict_proba(test_data)[:, 1]
            
            # Check predictions are in valid range [0, 1]
            if not all(0 <= p <= 1 for p in predictions):
                return False
            
            # Check for NaN or infinite values
            if np.any(np.isnan(predictions)) or np.any(np.isinf(predictions)):
                return False
            
            return True
        except Exception:
            return False
    
    @staticmethod
    def validate_scaler(scaler, test_data: np.ndarray) -> bool:
        """Validate that scaler transforms data correctly"""
        try:
            scaled_data = scaler.transform(test_data)
            
            # Check for NaN or infinite values
            if np.any(np.isnan(scaled_data)) or np.any(np.isinf(scaled_data)):
                return False
            
            return True
        except Exception:
            return False
```

---

## 📊 **Annual Prediction Pipeline**

### **Annual Financial Ratios (5 Features)**
```python
class AnnualFinancialRatios(BaseModel):
    """Annual prediction input schema with validation"""
    
    long_term_debt_to_total_capital: float = Field(
        ..., 
        ge=0, 
        le=2.0,
        description="Long-term debt divided by total capital (0-200%)"
    )
    total_debt_to_ebitda: float = Field(
        ..., 
        ge=0, 
        le=50.0,
        description="Total debt divided by EBITDA (0-50x)"
    )
    net_income_margin: float = Field(
        ..., 
        ge=-1.0, 
        le=1.0,
        description="Net income divided by revenue (-100% to 100%)"
    )
    ebit_to_interest_expense: float = Field(
        ..., 
        ge=0, 
        le=100.0,
        description="EBIT divided by interest expense (0-100x coverage)"
    )
    return_on_assets: float = Field(
        ..., 
        ge=-1.0, 
        le=1.0,
        description="Net income divided by total assets (-100% to 100%)"
    )
    
    @validator('*')
    def validate_finite_values(cls, v):
        """Ensure all values are finite"""
        if not np.isfinite(v):
            raise ValueError(f"Value must be finite, got {v}")
        return v
```

### **Annual Prediction Implementation**
```python
class AnnualPredictionService:
    """Annual default prediction service"""
    
    def __init__(self, model_manager: MLModelManager):
        self.model_manager = model_manager
        self.logistic_model = model_manager.models['annual_logistic']
        self.step_model = model_manager.models['annual_step']
        self.scaler = model_manager.scalers['annual']
        
        # Model weights for ensemble
        self.logistic_weight = 0.7
        self.step_weight = 0.3
    
    async def predict(self, financial_data: AnnualFinancialRatios) -> dict:
        """Generate annual default prediction"""
        
        # 1. Feature Preparation
        features = self._prepare_features(financial_data)
        
        # 2. Feature Scaling
        scaled_features = self._scale_features(features)
        
        # 3. Model Inference
        logistic_prob = self._predict_logistic(scaled_features)
        step_prob = self._predict_step(scaled_features)
        
        # 4. Ensemble Combination
        ensemble_prob = self._combine_predictions(logistic_prob, step_prob)
        
        # 5. Risk Assessment
        risk_level = self._categorize_risk(ensemble_prob)
        confidence = self._calculate_confidence(logistic_prob, step_prob)
        
        return {
            "probability": float(ensemble_prob),
            "risk_level": risk_level,
            "confidence": float(confidence),
            "model_details": {
                "logistic_probability": float(logistic_prob),
                "step_probability": float(step_prob),
                "ensemble_method": "weighted_average",
                "weights": {
                    "logistic": self.logistic_weight,
                    "step": self.step_weight
                }
            },
            "predicted_at": datetime.utcnow().isoformat()
        }
    
    def _prepare_features(self, financial_data: AnnualFinancialRatios) -> np.ndarray:
        """Convert financial ratios to numpy array for ML processing"""
        features = np.array([[
            financial_data.long_term_debt_to_total_capital,
            financial_data.total_debt_to_ebitda,
            financial_data.net_income_margin,
            financial_data.ebit_to_interest_expense,
            financial_data.return_on_assets
        ]])
        
        # Validate feature array
        if np.any(np.isnan(features)) or np.any(np.isinf(features)):
            raise ValueError("Invalid feature values detected")
        
        return features
    
    def _scale_features(self, features: np.ndarray) -> np.ndarray:
        """Apply StandardScaler transformation"""
        try:
            scaled_features = self.scaler.transform(features)
            
            # Validate scaled features
            if np.any(np.isnan(scaled_features)) or np.any(np.isinf(scaled_features)):
                raise ValueError("Invalid scaled feature values")
            
            return scaled_features
        except Exception as e:
            logger.error(f"Feature scaling failed: {e}")
            raise MLPredictionError(f"Feature scaling error: {e}")
    
    def _predict_logistic(self, scaled_features: np.ndarray) -> float:
        """Get prediction from logistic regression model"""
        try:
            # Get probability of default (class 1)
            prob = self.logistic_model.predict_proba(scaled_features)[0][1]
            return float(prob)
        except Exception as e:
            logger.error(f"Logistic model prediction failed: {e}")
            raise MLPredictionError(f"Logistic model error: {e}")
    
    def _predict_step(self, scaled_features: np.ndarray) -> float:
        """Get prediction from step function model"""
        try:
            # Get probability of default (class 1)
            prob = self.step_model.predict_proba(scaled_features)[0][1]
            return float(prob)
        except Exception as e:
            logger.error(f"Step model prediction failed: {e}")
            raise MLPredictionError(f"Step model error: {e}")
    
    def _combine_predictions(self, logistic_prob: float, step_prob: float) -> float:
        """Combine model predictions using weighted average"""
        ensemble_prob = (
            logistic_prob * self.logistic_weight + 
            step_prob * self.step_weight
        )
        
        # Ensure output is in valid range
        return max(0.0, min(1.0, ensemble_prob))
    
    def _calculate_confidence(self, prob1: float, prob2: float) -> float:
        """Calculate prediction confidence based on model agreement"""
        # Higher agreement between models = higher confidence
        agreement = 1.0 - abs(prob1 - prob2)
        
        # Apply confidence curve (sigmoid-like transformation)
        confidence = 1.0 / (1.0 + np.exp(-5 * (agreement - 0.5)))
        
        return max(0.0, min(1.0, confidence))
```

---

## 📈 **Quarterly Prediction Pipeline**

### **Quarterly Financial Ratios (6 Features)**
```python
class QuarterlyFinancialRatios(BaseModel):
    """Quarterly prediction input schema with validation"""
    
    current_ratio: float = Field(
        ..., 
        ge=0, 
        le=10.0,
        description="Current assets divided by current liabilities (0-10x)"
    )
    quick_ratio: float = Field(
        ..., 
        ge=0, 
        le=10.0,
        description="Quick assets divided by current liabilities (0-10x)"
    )
    debt_to_equity: float = Field(
        ..., 
        ge=0, 
        le=5.0,
        description="Total debt divided by total equity (0-5x)"
    )
    inventory_turnover: float = Field(
        ..., 
        ge=0, 
        le=50.0,
        description="Cost of goods sold divided by average inventory (0-50x)"
    )
    receivables_turnover: float = Field(
        ..., 
        ge=0, 
        le=50.0,
        description="Revenue divided by average receivables (0-50x)"
    )
    working_capital_to_total_assets: float = Field(
        ..., 
        ge=-1.0, 
        le=1.0,
        description="Working capital divided by total assets (-100% to 100%)"
    )
```

### **Quarterly Prediction Implementation**
```python
class QuarterlyPredictionService:
    """Advanced quarterly default prediction with triple ensemble"""
    
    def __init__(self, model_manager: MLModelManager):
        self.model_manager = model_manager
        self.lgb_model = model_manager.models['quarterly_lgb']
        self.logistic_model = model_manager.models['quarterly_logistic']
        self.step_model = model_manager.models['quarterly_step']
        self.scaler = model_manager.scalers['quarterly']
        
        # Model weights for advanced ensemble
        self.lgb_weight = 0.5      # LightGBM gets highest weight
        self.logistic_weight = 0.3  # Logistic second
        self.step_weight = 0.2     # Step function lowest
    
    async def predict(self, financial_data: QuarterlyFinancialRatios) -> dict:
        """Generate quarterly default prediction with advanced ensemble"""
        
        # 1. Feature Preparation
        features = self._prepare_features(financial_data)
        
        # 2. Feature Scaling
        scaled_features = self._scale_features(features)
        
        # 3. Multi-Model Inference
        lgb_prob = self._predict_lightgbm(scaled_features)
        logistic_prob = self._predict_logistic(scaled_features)
        step_prob = self._predict_step(scaled_features)
        
        # 4. Advanced Ensemble
        ensemble_prob = self._advanced_ensemble(lgb_prob, logistic_prob, step_prob)
        
        # 5. Enhanced Risk Assessment
        risk_level = self._categorize_risk_quarterly(ensemble_prob)
        confidence = self._calculate_ensemble_confidence(lgb_prob, logistic_prob, step_prob)
        
        return {
            "logistic_probability": float(logistic_prob),
            "gbm_probability": float(lgb_prob),
            "ensemble_probability": float(ensemble_prob),
            "risk_level": risk_level,
            "confidence": float(confidence),
            "model_details": {
                "step_probability": float(step_prob),
                "ensemble_method": "weighted_triple_ensemble",
                "weights": {
                    "lightgbm": self.lgb_weight,
                    "logistic": self.logistic_weight,
                    "step": self.step_weight
                },
                "model_agreement": self._calculate_model_agreement(lgb_prob, logistic_prob, step_prob)
            },
            "predicted_at": datetime.utcnow().isoformat()
        }
    
    def _prepare_features(self, financial_data: QuarterlyFinancialRatios) -> np.ndarray:
        """Convert quarterly ratios to numpy array"""
        features = np.array([[
            financial_data.current_ratio,
            financial_data.quick_ratio,
            financial_data.debt_to_equity,
            financial_data.inventory_turnover,
            financial_data.receivables_turnover,
            financial_data.working_capital_to_total_assets
        ]])
        
        # Validate feature array
        if np.any(np.isnan(features)) or np.any(np.isinf(features)):
            raise ValueError("Invalid quarterly feature values detected")
        
        return features
    
    def _predict_lightgbm(self, scaled_features: np.ndarray) -> float:
        """Get prediction from LightGBM model"""
        try:
            # LightGBM may output direct probability or need probability extraction
            if hasattr(self.lgb_model, 'predict_proba'):
                prob = self.lgb_model.predict_proba(scaled_features)[0][1]
            else:
                # Direct probability output
                prob = self.lgb_model.predict(scaled_features)[0]
            
            return float(prob)
        except Exception as e:
            logger.error(f"LightGBM model prediction failed: {e}")
            raise MLPredictionError(f"LightGBM model error: {e}")
    
    def _advanced_ensemble(self, lgb_prob: float, logistic_prob: float, step_prob: float) -> float:
        """Advanced ensemble with dynamic weighting"""
        
        # Calculate base weighted average
        base_ensemble = (
            lgb_prob * self.lgb_weight +
            logistic_prob * self.logistic_weight +
            step_prob * self.step_weight
        )
        
        # Apply confidence-based adjustment
        model_variance = np.var([lgb_prob, logistic_prob, step_prob])
        
        # If models agree (low variance), increase confidence in ensemble
        # If models disagree (high variance), be more conservative
        if model_variance < 0.01:  # Models strongly agree
            adjustment_factor = 1.0
        elif model_variance < 0.05:  # Moderate agreement
            adjustment_factor = 0.95
        else:  # High disagreement
            adjustment_factor = 0.9
        
        adjusted_ensemble = base_ensemble * adjustment_factor
        
        # Ensure valid probability range
        return max(0.0, min(1.0, adjusted_ensemble))
    
    def _calculate_ensemble_confidence(self, lgb_prob: float, logistic_prob: float, step_prob: float) -> float:
        """Calculate confidence for triple model ensemble"""
        
        # Calculate pairwise agreements
        lgb_logistic_agreement = 1.0 - abs(lgb_prob - logistic_prob)
        lgb_step_agreement = 1.0 - abs(lgb_prob - step_prob)
        logistic_step_agreement = 1.0 - abs(logistic_prob - step_prob)
        
        # Average agreement across all model pairs
        avg_agreement = (lgb_logistic_agreement + lgb_step_agreement + logistic_step_agreement) / 3.0
        
        # Apply sigmoid transformation for smooth confidence curve
        confidence = 1.0 / (1.0 + np.exp(-8 * (avg_agreement - 0.4)))
        
        return max(0.0, min(1.0, confidence))
    
    def _calculate_model_agreement(self, lgb_prob: float, logistic_prob: float, step_prob: float) -> dict:
        """Calculate detailed model agreement statistics"""
        return {
            "lgb_logistic_agreement": 1.0 - abs(lgb_prob - logistic_prob),
            "lgb_step_agreement": 1.0 - abs(lgb_prob - step_prob),
            "logistic_step_agreement": 1.0 - abs(logistic_prob - step_prob),
            "overall_variance": float(np.var([lgb_prob, logistic_prob, step_prob])),
            "prediction_range": {
                "min": min(lgb_prob, logistic_prob, step_prob),
                "max": max(lgb_prob, logistic_prob, step_prob),
                "spread": max(lgb_prob, logistic_prob, step_prob) - min(lgb_prob, logistic_prob, step_prob)
            }
        }
```

---

## 🔧 **Feature Engineering**

### **Feature Preprocessing Pipeline**
```python
class FeatureEngineer:
    """Advanced feature engineering for financial ratios"""
    
    @staticmethod
    def engineer_annual_features(raw_ratios: dict) -> dict:
        """Create additional features for annual predictions"""
        
        # Base ratios
        features = raw_ratios.copy()
        
        # Derived features
        features['leverage_score'] = (
            raw_ratios['long_term_debt_to_total_capital'] * 0.6 +
            raw_ratios['total_debt_to_ebitda'] * 0.4
        )
        
        features['profitability_score'] = (
            raw_ratios['net_income_margin'] * 0.7 +
            raw_ratios['return_on_assets'] * 0.3
        )
        
        features['coverage_ratio'] = raw_ratios['ebit_to_interest_expense']
        
        # Risk interaction terms
        if raw_ratios['net_income_margin'] < 0:
            features['negative_margin_flag'] = 1.0
            features['leverage_risk'] = features['leverage_score'] * 1.5
        else:
            features['negative_margin_flag'] = 0.0
            features['leverage_risk'] = features['leverage_score']
        
        return features
    
    @staticmethod
    def engineer_quarterly_features(raw_ratios: dict) -> dict:
        """Create additional features for quarterly predictions"""
        
        # Base ratios
        features = raw_ratios.copy()
        
        # Liquidity composite score
        features['liquidity_score'] = (
            raw_ratios['current_ratio'] * 0.6 +
            raw_ratios['quick_ratio'] * 0.4
        )
        
        # Efficiency composite score
        features['efficiency_score'] = (
            np.log1p(raw_ratios['inventory_turnover']) * 0.5 +
            np.log1p(raw_ratios['receivables_turnover']) * 0.5
        )
        
        # Financial health indicator
        if raw_ratios['working_capital_to_total_assets'] < 0:
            features['negative_wc_flag'] = 1.0
            features['distress_indicator'] = (
                raw_ratios['debt_to_equity'] * features['negative_wc_flag']
            )
        else:
            features['negative_wc_flag'] = 0.0
            features['distress_indicator'] = 0.0
        
        # Ratio interactions
        features['liquidity_leverage_interaction'] = (
            features['liquidity_score'] / (1.0 + raw_ratios['debt_to_equity'])
        )
        
        return features
    
    @staticmethod
    def detect_outliers(features: np.ndarray, method: str = 'iqr') -> np.ndarray:
        """Detect outliers in feature data"""
        
        if method == 'iqr':
            Q1 = np.percentile(features, 25, axis=0)
            Q3 = np.percentile(features, 75, axis=0)
            IQR = Q3 - Q1
            
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers = (features < lower_bound) | (features > upper_bound)
            
        elif method == 'zscore':
            z_scores = np.abs((features - np.mean(features, axis=0)) / np.std(features, axis=0))
            outliers = z_scores > 3
            
        return outliers
```

---

## 🎯 **Risk Categorization System**

### **Risk Level Classification**
```python
class RiskCategorizer:
    """Advanced risk categorization with dynamic thresholds"""
    
    # Base thresholds for risk categorization
    LOW_RISK_THRESHOLD = 0.3
    HIGH_RISK_THRESHOLD = 0.7
    
    @classmethod
    def categorize_annual_risk(cls, probability: float, confidence: float) -> str:
        """Categorize annual prediction risk with confidence adjustment"""
        
        # Adjust thresholds based on confidence
        confidence_factor = max(0.8, confidence)  # Minimum confidence factor
        
        adjusted_low = cls.LOW_RISK_THRESHOLD * confidence_factor
        adjusted_high = cls.HIGH_RISK_THRESHOLD * confidence_factor
        
        if probability < adjusted_low:
            return "Low"
        elif probability < adjusted_high:
            return "Medium"
        else:
            return "High"
    
    @classmethod
    def categorize_quarterly_risk(cls, probability: float, confidence: float, model_agreement: dict) -> str:
        """Enhanced quarterly risk categorization"""
        
        # Base categorization
        base_risk = cls.categorize_annual_risk(probability, confidence)
        
        # Adjust based on model agreement
        if model_agreement['overall_variance'] > 0.1:
            # High model disagreement - be more conservative
            if base_risk == "Low" and probability > 0.2:
                return "Medium"
            elif base_risk == "Medium" and probability > 0.5:
                return "High"
        
        return base_risk
    
    @staticmethod
    def get_risk_explanation(risk_level: str, probability: float, confidence: float) -> dict:
        """Provide detailed risk explanation"""
        
        explanations = {
            "Low": {
                "description": "Low default risk based on strong financial indicators",
                "recommendation": "Monitor periodically, suitable for standard credit terms",
                "key_factors": ["Strong liquidity position", "Healthy profitability ratios", "Low leverage"]
            },
            "Medium": {
                "description": "Moderate default risk requiring closer monitoring",
                "recommendation": "Enhanced monitoring, consider risk mitigation measures",
                "key_factors": ["Mixed financial indicators", "Industry-specific risks", "Market volatility"]
            },
            "High": {
                "description": "High default risk requiring immediate attention",
                "recommendation": "Detailed review required, implement risk controls",
                "key_factors": ["Weak financial position", "High leverage", "Declining profitability"]
            }
        }
        
        return {
            "risk_level": risk_level,
            "probability": probability,
            "confidence": confidence,
            "interpretation": explanations.get(risk_level, {}),
            "confidence_interpretation": cls._interpret_confidence(confidence)
        }
    
    @staticmethod
    def _interpret_confidence(confidence: float) -> str:
        """Interpret confidence score"""
        if confidence >= 0.9:
            return "Very High - Models strongly agree"
        elif confidence >= 0.8:
            return "High - Good model agreement"
        elif confidence >= 0.7:
            return "Medium - Moderate model agreement"
        elif confidence >= 0.6:
            return "Low - Models show some disagreement"
        else:
            return "Very Low - Significant model disagreement"
```

---

## 📊 **Performance Monitoring**

### **Model Performance Metrics**
```python
class MLPerformanceMonitor:
    """Monitor ML model performance and drift"""
    
    def __init__(self):
        self.metrics_store = {}
        self.performance_thresholds = {
            'prediction_latency_ms': 100,
            'confidence_threshold': 0.6,
            'model_agreement_threshold': 0.8
        }
    
    async def log_prediction_metrics(self, prediction_result: dict, processing_time_ms: float):
        """Log metrics for each prediction"""
        
        metrics = {
            'timestamp': datetime.utcnow(),
            'processing_time_ms': processing_time_ms,
            'probability': prediction_result.get('probability', 0),
            'confidence': prediction_result.get('confidence', 0),
            'risk_level': prediction_result.get('risk_level', 'Unknown'),
            'model_type': 'annual' if 'logistic_probability' not in prediction_result else 'quarterly'
        }
        
        # Store metrics for analysis
        await self._store_metrics(metrics)
        
        # Check for performance issues
        await self._check_performance_alerts(metrics)
    
    async def calculate_model_drift(self, recent_predictions: List[dict], baseline_stats: dict) -> dict:
        """Calculate statistical drift in model predictions"""
        
        if not recent_predictions:
            return {"status": "insufficient_data"}
        
        # Extract probabilities
        probabilities = [p.get('probability', 0) for p in recent_predictions]
        confidences = [p.get('confidence', 0) for p in recent_predictions]
        
        # Calculate current statistics
        current_stats = {
            'mean_probability': np.mean(probabilities),
            'std_probability': np.std(probabilities),
            'mean_confidence': np.mean(confidences),
            'std_confidence': np.std(confidences),
            'risk_distribution': {
                'Low': sum(1 for p in recent_predictions if p.get('risk_level') == 'Low'),
                'Medium': sum(1 for p in recent_predictions if p.get('risk_level') == 'Medium'),
                'High': sum(1 for p in recent_predictions if p.get('risk_level') == 'High')
            }
        }
        
        # Calculate drift scores
        drift_scores = {
            'probability_drift': abs(current_stats['mean_probability'] - baseline_stats.get('mean_probability', 0.5)),
            'confidence_drift': abs(current_stats['mean_confidence'] - baseline_stats.get('mean_confidence', 0.8)),
            'variance_drift': abs(current_stats['std_probability'] - baseline_stats.get('std_probability', 0.2))
        }
        
        # Determine drift severity
        max_drift = max(drift_scores.values())
        if max_drift > 0.2:
            drift_status = "high_drift"
        elif max_drift > 0.1:
            drift_status = "moderate_drift"
        else:
            drift_status = "normal"
        
        return {
            "status": drift_status,
            "drift_scores": drift_scores,
            "current_stats": current_stats,
            "baseline_stats": baseline_stats,
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
    
    async def generate_performance_report(self, time_period_hours: int = 24) -> dict:
        """Generate comprehensive performance report"""
        
        # Get recent metrics
        since_time = datetime.utcnow() - timedelta(hours=time_period_hours)
        recent_metrics = await self._get_metrics_since(since_time)
        
        if not recent_metrics:
            return {"status": "no_data", "message": "No predictions in specified time period"}
        
        # Calculate aggregated statistics
        processing_times = [m['processing_time_ms'] for m in recent_metrics]
        probabilities = [m['probability'] for m in recent_metrics]
        confidences = [m['confidence'] for m in recent_metrics]
        
        report = {
            "time_period": f"{time_period_hours} hours",
            "total_predictions": len(recent_metrics),
            "performance_metrics": {
                "avg_processing_time_ms": np.mean(processing_times),
                "p95_processing_time_ms": np.percentile(processing_times, 95),
                "p99_processing_time_ms": np.percentile(processing_times, 99),
                "avg_confidence": np.mean(confidences),
                "min_confidence": np.min(confidences),
                "low_confidence_predictions": sum(1 for c in confidences if c < self.performance_thresholds['confidence_threshold'])
            },
            "prediction_distribution": {
                "mean_probability": np.mean(probabilities),
                "std_probability": np.std(probabilities),
                "risk_breakdown": {
                    "Low": sum(1 for m in recent_metrics if m['risk_level'] == 'Low'),
                    "Medium": sum(1 for m in recent_metrics if m['risk_level'] == 'Medium'),
                    "High": sum(1 for m in recent_metrics if m['risk_level'] == 'High')
                }
            },
            "model_type_breakdown": {
                "annual": sum(1 for m in recent_metrics if m['model_type'] == 'annual'),
                "quarterly": sum(1 for m in recent_metrics if m['model_type'] == 'quarterly')
            },
            "quality_indicators": {
                "performance_issues": sum(1 for t in processing_times if t > self.performance_thresholds['prediction_latency_ms']),
                "low_confidence_rate": sum(1 for c in confidences if c < self.performance_thresholds['confidence_threshold']) / len(confidences)
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
        return report
```

---

**Last Updated**: October 5, 2025  
**ML Pipeline Version**: 2.0.0
