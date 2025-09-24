import pandas as pd
import numpy as np
import pickle
import os
import joblib
import warnings
from typing import Dict, Optional
from datetime import datetime

warnings.filterwarnings("ignore")

class MLModelService:
    def __init__(self):
        self.model = None
        self.scoring_info = None
        base_dir = os.path.dirname(os.path.dirname(__file__))  
        self.model_path = os.path.join(base_dir, "models", "annual_logistic_model.pkl")
        self.scoring_info_path = os.path.join(base_dir, "models", "scoring_info.pkl")
        self.load_model()

    def load_model(self):
        """Load the trained model and scoring information"""
        try:
            self.model = joblib.load(self.model_path)
            
            with open(self.scoring_info_path, "rb") as f:
                self.scoring_info = pickle.load(f)
                
            print("✅ ML Model and scoring info loaded successfully")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            raise e

    def binned_runscoring(self, df: pd.DataFrame, value_col: str, scoring_info: Dict) -> pd.DataFrame:
        """Apply binned scoring to a column based on scoring information"""
        df[value_col] = df[value_col].replace([None, 'NM', 'N/A', ''], np.nan)
        df[value_col] = pd.to_numeric(df[value_col], errors='coerce')

        intervals = scoring_info[value_col]['intervals']
        rates = scoring_info[value_col]['rates']

        def assign_rate(x):
            if pd.isna(x) or x is None:
                if "Missing" in intervals:
                    return rates[intervals.index("Missing")]
                else:
                    return rates[0] if rates else 0.0
            for idx, iv in enumerate(intervals):
                if iv == "Missing":
                    continue
                low, high = iv
                if low < x <= high:
                    return rates[idx]
            if rates:
                return rates[0] 
            return 0.0  

        prefix = 'bin_'
        new_column_name = f"{prefix}{value_col}"
        df[new_column_name] = df[value_col].apply(assign_rate)
        
        return df

    def predict_default_probability(self, financial_ratios: Dict[str, float]) -> Dict:
        """
        Predict default probability for a company based on financial ratios
        
        Args:
            financial_ratios: Dictionary containing exactly these 5 ratios:
                - long_term_debt_to_total_capital: Long-term debt / total capital (%)
                - total_debt_to_ebitda: Total debt / EBITDA
                - net_income_margin: Net income margin (%)
                - ebit_to_interest_expense: EBIT / interest expense  
                - return_on_assets: Return on assets (%)
                
        Returns:
            Dictionary with prediction results
        """
        try:
            if self.model is None or self.scoring_info is None:
                return {
                    "probability": 0.5,
                    "risk_level": "UNKNOWN",
                    "confidence": 0.5,
                    "error": "Model or scoring info not loaded",
                    "predicted_at": datetime.utcnow().isoformat()
                }

            single_variables = [
                'long-term debt / total capital (%)',
                'total debt / ebitda',
                'net income margin',
                'ebit / interest expense',
                'return on assets'
            ]

            required_fields = {
                'long_term_debt_to_total_capital': 'long-term debt / total capital (%)',
                'total_debt_to_ebitda': 'total debt / ebitda',
                'net_income_margin': 'net income margin',
                'ebit_to_interest_expense': 'ebit / interest expense',
                'return_on_assets': 'return on assets'
            }

            missing_fields = []
            for field in required_fields.keys():
                if field not in financial_ratios:
                    missing_fields.append(field)
            
            if missing_fields:
                return {
                    "probability": None,
                    "risk_level": "UNKNOWN",
                    "confidence": 0.0,
                    "error": f"Missing required financial ratios: {missing_fields}",
                    "required_fields": list(required_fields.keys()),
                    "predicted_at": datetime.utcnow().isoformat()
                }

            values = [
                financial_ratios['long_term_debt_to_total_capital'],     
                financial_ratios['total_debt_to_ebitda'],                
                financial_ratios['net_income_margin'],                   
                financial_ratios['ebit_to_interest_expense'],            
                financial_ratios['return_on_assets']                     
            ]

            df = pd.DataFrame([values], columns=single_variables)
            
            for value_col in single_variables:
                df = self.binned_runscoring(df, value_col, self.scoring_info)

            features = [
                'bin_long-term debt / total capital (%)',
                'bin_total debt / ebitda',
                'bin_net income margin',
                'bin_ebit / interest expense',
                'bin_return on assets'
            ]

            X = df[features]
            
            if X.isnull().any().any():
                print(f"❌ Warning: NaN values found in features: {X.isnull().sum()}")
                for feature in features:
                    if X[feature].isnull().any():
                        original_col = feature.replace('bin_', '')
                        if original_col in self.scoring_info and 'rates' in self.scoring_info[original_col]:
                            rates = self.scoring_info[original_col]['rates']
                            default_value = rates[0] if rates else 0.0
                            X[feature] = X[feature].fillna(default_value)
                            print(f"Filled NaN in {feature} with default value: {default_value}")

            probability = self.model.predict_proba(X)[:, 1][0]

            probability_percentage = probability * 100

            if probability_percentage > 15:
                risk_level = "CRITICAL"
            elif probability_percentage >= 5:
                risk_level = "HIGH"
            elif probability_percentage >= 2:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"

            confidence = max(abs(probability - 0.5) * 2, 0.5)

            return {
                "probability": float(probability),
                "risk_level": risk_level,
                "confidence": float(confidence),
                "model_features": {feature: float(df[feature].iloc[0]) for feature in features},
                "predicted_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"❌ Prediction error: {e}")
            return {
                "probability": 0.0,
                "risk_level": "ERROR",
                "confidence": 0.0,
                "error": str(e),
                "predicted_at": datetime.utcnow().isoformat()
            }

    async def predict_annual(self, financial_ratios: Dict[str, float]) -> Dict:
        """
        Async wrapper for annual prediction - calls predict_default_probability
        
        Args:
            financial_ratios: Dictionary containing the 5 required financial ratios
            
        Returns:
            Dictionary with prediction results
        """
        return self.predict_default_probability(financial_ratios)

ml_model = MLModelService()
