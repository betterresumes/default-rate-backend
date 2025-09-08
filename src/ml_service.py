import pandas as pd
import numpy as np
import pickle
import joblib
import os
from typing import Dict, List, Optional
from datetime import datetime

class MLModelService:
    def __init__(self):
        self.model = None
        self.scoring_info = None
        self.model_path = os.path.join(os.path.dirname(__file__), "model", "annual_logistic_model.pkl")
        self.scoring_info_path = os.path.join(os.path.dirname(__file__), "model", "scoring_info.pkl")
        self.load_model()

    def load_model(self):
        """Load the trained model and scoring information"""
        try:
            # Load the logistic regression model
            self.model = joblib.load(self.model_path)
            
            # Load scoring information for binning
            with open(self.scoring_info_path, "rb") as f:
                self.scoring_info = pickle.load(f)
                
            print("✅ ML Model and scoring info loaded successfully")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            raise e

    def binned_runscoring(self, df: pd.DataFrame, value_col: str) -> pd.DataFrame:
        """Apply binning to a specific column using scoring info"""
        # Replace 'NM' with NaN and convert to numeric
        df[value_col] = pd.to_numeric(df[value_col].replace('NM', np.nan), errors='coerce')
        
        intervals = self.scoring_info[value_col]['intervals']
        rates = self.scoring_info[value_col]['rates']

        def assign_rate(x):
            if pd.isna(x):
                return rates[intervals.index("Missing")]
            for idx, iv in enumerate(intervals):
                if iv == "Missing":
                    continue
                low, high = iv
                if low < x <= high:
                    return rates[idx]
            return None  # in case it doesn't fall in any bin

        prefix = 'bin_'
        new_column_name = f"{prefix}{value_col}"
        df[new_column_name] = df[value_col].apply(assign_rate)
        
        return df

    def predict_default_probability(self, financial_ratios: Dict[str, float]) -> Dict:
        """
        Predict default probability for a company based on financial ratios
        
        Args:
            financial_ratios: Dictionary containing financial ratio values
            
        Returns:
            Dictionary with prediction results
        """
        try:
            # Quick validation - if model not loaded, return fallback
            if self.model is None or self.scoring_info is None:
                return {
                    "probability": 0.5,
                    "risk_level": "UNKNOWN",
                    "confidence": 0.5,
                    "error": "Model not loaded",
                    "predicted_at": datetime.utcnow().isoformat()
                }

            # Map the input ratios to the model's expected variable names with defaults
            ratio_mapping = {
                'return on assets': financial_ratios.get('return_on_assets', 0.05),
                'net income margin': financial_ratios.get('profit_margin', 0.1),
                'fixed asset turnover': financial_ratios.get('fixed_asset_turnover', 1.0),
                'total debt / total capital (%)': financial_ratios.get('debt_to_equity_ratio', 0.3),
                'ebitda / interest expense': financial_ratios.get('interest_coverage', 5.0),
                'total debt / ebitda': financial_ratios.get('total_debt_ebitda', 2.0)
            }

            # Optimize: Skip pandas DataFrame creation for simple binning
            binned_values = {}
            for var_name, value in ratio_mapping.items():
                if var_name in self.scoring_info:
                    intervals = self.scoring_info[var_name]['intervals']
                    rates = self.scoring_info[var_name]['rates']
                    
                    # Fast binning without pandas
                    if pd.isna(value) or value is None:
                        binned_values[f"bin_{var_name}"] = rates[intervals.index("Missing")] if "Missing" in intervals else 0.5
                    else:
                        assigned_rate = None
                        for idx, iv in enumerate(intervals):
                            if iv == "Missing":
                                continue
                            if isinstance(iv, tuple) and len(iv) == 2:
                                low, high = iv
                                if low < value <= high:
                                    assigned_rate = rates[idx]
                                    break
                        binned_values[f"bin_{var_name}"] = assigned_rate if assigned_rate is not None else 0.5

            # Features that the model expects (binned versions)
            features = [
                'bin_return on assets', 
                'bin_net income margin', 
                'bin_fixed asset turnover',  
                'bin_total debt / total capital (%)',  
                'bin_ebitda / interest expense', 
                'bin_total debt / ebitda'
            ]

            # Prepare the feature array directly (faster than DataFrame)
            X = np.array([[binned_values.get(feature, 0.5) for feature in features]])

            # Make prediction
            probability = self.model.predict_proba(X)[:, 1][0]

            # Determine risk level based on probability
            if probability >= 0.7:
                risk_level = "HIGH_RISK"
            elif probability >= 0.4:
                risk_level = "MEDIUM_RISK"
            else:
                risk_level = "LOW_RISK"

            # Calculate confidence (inverse of how close to decision boundary)
            confidence = max(abs(probability - 0.5) * 2, 0.5)

            return {
                "probability": float(probability),
                "risk_level": risk_level,
                "confidence": float(confidence),
                "model_features": {feature: binned_values.get(feature, 0.5) for feature in features}
            }

        except Exception as e:
            print(f"❌ Prediction error: {e}")
            # Return a fallback prediction
            return {
                "probability": 0.5,
                "risk_level": "UNKNOWN",
                "confidence": 0.5,
                "error": str(e)
            }

ml_service = MLModelService()
