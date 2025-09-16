import pandas as pd
import numpy as np
import pickle
import os
import joblib
import warnings
from typing import Dict, Optional
from datetime import datetime

warnings.filterwarnings("ignore")

class QuarterlyMLModelService:
    def __init__(self):
        self.logistic_model = None
        self.gbm_model = None
        self.scoring_info = None
        
        self.logistic_model_path = os.path.join(os.path.dirname(__file__), "models", "quarterly_logistic_model.pkl")
        self.gbm_model_path = os.path.join(os.path.dirname(__file__), "models", "quarterly_lgb_model.pkl")
        self.scoring_info_path = os.path.join(os.path.dirname(__file__), "models", "quarterly_scoring_info.pkl")
        
        self.load_models()

    def load_models(self):
        """Load the trained models and scoring information"""
        try:
            self.logistic_model = joblib.load(self.logistic_model_path)
            
            self.gbm_model = joblib.load(self.gbm_model_path)
            
            with open(self.scoring_info_path, "rb") as f:
                self.scoring_info = pickle.load(f)
                
            print("✅ Quarterly ML Models and scoring info loaded successfully")
        except Exception as e:
            print(f"❌ Error loading quarterly models: {e}")
            raise e

    def binned_runscoring(self, df: pd.DataFrame, value_col: str, scoring_info: Dict) -> pd.DataFrame:
        """Apply binned scoring to a column based on scoring information"""
        df[value_col] = pd.to_numeric(df[value_col].replace('NM', np.nan), errors='coerce')

        intervals = scoring_info[value_col]['intervals']
        rates = scoring_info[value_col]['rates']

        def assign_rate(x):
            if pd.isna(x):
                return rates[intervals.index("Missing")]
            for idx, iv in enumerate(intervals):
                if iv == "Missing":
                    continue
                low, high = iv
                if low < x <= high:
                    return rates[idx]
            return None  

        prefix = 'bin_'
        new_column_name = f"{prefix}{value_col}"
        df[new_column_name] = df[value_col].apply(assign_rate)
        
        return df

    def predict_quarterly_default_probability(self, financial_ratios: Dict[str, float]) -> Dict:
        """
        Predict quarterly default probability for a company based on financial ratios
        
        Args:
            financial_ratios: Dictionary containing exactly these 4 ratios:
                - total_debt_to_ebitda: Total debt / EBITDA
                - sga_margin: SG&A margin (%)
                - long_term_debt_to_total_capital: Long-term debt / total capital (%)
                - return_on_capital: Return on capital (%)
                
        Returns:
            Dictionary with prediction results from both models
        """
        try:
            if self.logistic_model is None or self.gbm_model is None or self.scoring_info is None:
                return {
                    "logistic_probability": 0.5,
                    "gbm_probability": 0.5,
                    "ensemble_probability": 0.5,
                    "risk_level": "UNKNOWN",
                    "confidence": 0.5,
                    "error": "Models or scoring info not loaded",
                    "predicted_at": datetime.utcnow().isoformat()
                }

            single_variables = [
                'total debt / ebitda',
                'sg&a margin',
                'long-term debt / total capital (%)',
                'return on capital'
            ]

            required_fields = {
                'total_debt_to_ebitda': 'total debt / ebitda',
                'sga_margin': 'sg&a margin',
                'long_term_debt_to_total_capital': 'long-term debt / total capital (%)',
                'return_on_capital': 'return on capital'
            }

            missing_fields = []
            for field in required_fields.keys():
                if field not in financial_ratios or financial_ratios[field] is None:
                    missing_fields.append(field)
            
            if missing_fields:
                return {
                    "logistic_probability": None,
                    "gbm_probability": None,
                    "ensemble_probability": None,
                    "risk_level": "UNKNOWN",
                    "confidence": 0.0,
                    "error": f"Missing required financial ratios: {missing_fields}",
                    "required_fields": list(required_fields.keys()),
                    "predicted_at": datetime.utcnow().isoformat()
                }

            values = [
                financial_ratios['total_debt_to_ebitda'],
                financial_ratios['sga_margin'],
                financial_ratios['long_term_debt_to_total_capital'],
                financial_ratios['return_on_capital']
            ]

            df = pd.DataFrame([values], columns=single_variables)
            
            df_binned = df.copy()
            for value_col in single_variables:
                df_binned = self.binned_runscoring(df_binned, value_col, self.scoring_info)

            binned_features = [
                'bin_total debt / ebitda',
                'bin_sg&a margin',
                'bin_long-term debt / total capital (%)',
                'bin_return on capital'
            ]

            X_logistic = df_binned[binned_features]
            logistic_probability = self.logistic_model.predict_proba(X_logistic)[:, 1][0]

            X_gbm = df[single_variables]
            gbm_probability = self.gbm_model.predict(X_gbm)[0]

            ensemble_probability = (logistic_probability + gbm_probability) / 2

            probability_percentage = ensemble_probability * 100

            if probability_percentage > 15:
                risk_level = "CRITICAL"
            elif probability_percentage >= 5:
                risk_level = "HIGH"
            elif probability_percentage >= 2:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"

            confidence = max(abs(ensemble_probability - 0.5) * 2, 0.5)

            return {
                "logistic_probability": float(logistic_probability),
                "gbm_probability": float(gbm_probability),
                "ensemble_probability": float(ensemble_probability),
                "risk_level": risk_level,
                "confidence": float(confidence),
                "model_features": {
                    "binned_features": {feature: float(df_binned[feature].iloc[0]) for feature in binned_features},
                    "raw_features": {feature: float(df[feature].iloc[0]) for feature in single_variables}
                },
                "predicted_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"❌ Quarterly prediction error: {e}")
            return {
                "logistic_probability": 0.0,
                "gbm_probability": 0.0,
                "ensemble_probability": 0.0,
                "risk_level": "ERROR",
                "confidence": 0.0,
                "error": str(e),
                "predicted_at": datetime.utcnow().isoformat()
            }

    def predict_default_probability(self, financial_ratios: Dict[str, float]) -> Dict:
        """Alias for predict_quarterly_default_probability for compatibility"""
        return self.predict_quarterly_default_probability(financial_ratios)

quarterly_ml_model = QuarterlyMLModelService()
