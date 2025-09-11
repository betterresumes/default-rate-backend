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
        self.model_path = os.path.join(os.path.dirname(__file__), "models", "annual_logistic_model.pkl")
        self.scoring_info_path = os.path.join(os.path.dirname(__file__), "models", "scoring_info.pkl")
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
        # Replace 'NM' with NaN and convert to numeric
        df[value_col] = pd.to_numeric(df[value_col].replace('NM', np.nan), errors='coerce')

        intervals = scoring_info[value_col]['intervals']
        rates = scoring_info[value_col]['rates']

        # Apply mapping function to column
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

            # The model now expects exactly these 5 features (matching your updated model)
            single_variables = [
                'long-term debt / total capital (%)',
                'total debt / ebitda',
                'net income margin',
                'ebit / interest expense',
                'return on assets'
            ]

            # Map API input fields to model variables (direct 1:1 mapping)
            required_fields = {
                'long_term_debt_to_total_capital': 'long-term debt / total capital (%)',
                'total_debt_to_ebitda': 'total debt / ebitda',
                'net_income_margin': 'net income margin',
                'ebit_to_interest_expense': 'ebit / interest expense',
                'return_on_assets': 'return on assets'
            }

            # Check for missing fields
            missing_fields = []
            for field in required_fields.keys():
                if field not in financial_ratios or financial_ratios[field] is None:
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

            # Extract values using ONLY the 5 user inputs - NO defaults needed!
            values = [
                financial_ratios['long_term_debt_to_total_capital'],     # User input only
                financial_ratios['total_debt_to_ebitda'],                # User input only
                financial_ratios['net_income_margin'],                   # User input only
                financial_ratios['ebit_to_interest_expense'],            # User input only
                financial_ratios['return_on_assets']                     # User input only
            ]

            # Create DataFrame with only the 5 user values
            df = pd.DataFrame([values], columns=single_variables)
            
            # Apply binned scoring to each variable
            for value_col in single_variables:
                df = self.binned_runscoring(df, value_col, self.scoring_info)

            # Define the features that the model expects (the exact 5 features from your updated model)
            features = [
                'bin_long-term debt / total capital (%)',
                'bin_total debt / ebitda',
                'bin_net income margin',
                'bin_ebit / interest expense',
                'bin_return on assets'
            ]

            # Prepare the feature matrix
            X = df[features]

            # Make prediction
            probability = self.model.predict_proba(X)[:, 1][0]

            # Convert probability to percentage for risk level determination
            probability_percentage = probability * 100

            # Determine risk level based on probability percentage
            if probability_percentage > 15:
                risk_level = "CRITICAL"
            elif probability_percentage >= 5:
                risk_level = "HIGH"
            elif probability_percentage >= 2:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"

            # Calculate confidence (distance from 0.5, scaled to 0-1)
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

# Create a global instance
ml_model = MLModelService()
