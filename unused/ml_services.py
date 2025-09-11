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
        self.annual_data = None
        self.model_path = os.path.join(os.path.dirname(__file__), "model", "annual_logistic_model.pkl")
        self.scoring_info_path = os.path.join(os.path.dirname(__file__), "model", "scoring_info.pkl")
        self.annual_data_path = os.path.join(os.path.dirname(__file__), "model", "annual_step.pkl")
        self.load_model()

    def load_model(self):
        """Load the trained model, scoring information, and historical data"""
        try:
            self.model = joblib.load(self.model_path)
            
            with open(self.scoring_info_path, "rb") as f:
                self.scoring_info = pickle.load(f)
            
            self.annual_data = pd.read_pickle(self.annual_data_path)
                
            print("✅ ML Model, scoring info, and annual data loaded successfully")
            print(f"📊 Annual data shape: {self.annual_data.shape}")
            print(f"📊 Annual data columns: {list(self.annual_data.columns)}")
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            raise e

    def binned_runscoring(self, df: pd.DataFrame, value_col: str) -> pd.DataFrame:
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
            return None

        prefix = 'bin_'
        new_column_name = f"{prefix}{value_col}"
        df[new_column_name] = df[value_col].apply(assign_rate)
        
        return df

    def get_historical_benchmarks(self, financial_ratios: Dict[str, float]) -> Dict:
        """Get historical benchmarks from annual data for comparison"""
        try:
            if self.annual_data is None:
                return {}
            
            ratio_to_column = {
                'return_on_assets': 'return on assets',
                'profit_margin': 'net income margin', 
                'fixed_asset_turnover': 'fixed asset turnover',
                'debt_to_equity_ratio': 'total debt / total capital (%)',
                'interest_coverage': 'ebitda / interest expense',
                'total_debt_ebitda': 'total debt / ebitda'
            }
            
            benchmarks = {}
            for input_field, column_name in ratio_to_column.items():
                if column_name in self.annual_data.columns and input_field in financial_ratios:
                    col_data = pd.to_numeric(self.annual_data[column_name], errors='coerce')
                    col_data = col_data.dropna()
                    
                    if len(col_data) > 0:
                        user_value = financial_ratios[input_field]
                        
                        if input_field in ['return_on_assets', 'profit_margin']:
                            user_value_scaled = user_value * 100  
                        else:
                            user_value_scaled = user_value  
                        
                        percentile = (col_data < user_value_scaled).mean() * 100
                        
                        benchmarks[input_field] = {
                            'user_value': user_value,  
                            'user_value_scaled': round(user_value_scaled, 4),  
                            'percentile': round(percentile, 1),
                            'median': round(col_data.median(), 4),
                            'mean': round(col_data.mean(), 4),
                            'interpretation': self._interpret_percentile(percentile, input_field)
                        }
            
            return benchmarks
        except Exception as e:
            print(f"❌ Error calculating benchmarks: {e}")
            return {}
    
    def _interpret_percentile(self, percentile: float, metric: str) -> str:
        """Interpret what the percentile means for each metric"""
        if metric in ['return_on_assets', 'profit_margin', 'fixed_asset_turnover', 'interest_coverage']:
            if percentile >= 75:
                return "Excellent - Top 25%"
            elif percentile >= 50:
                return "Above Average"
            elif percentile >= 25:
                return "Below Average"
            else:
                return "Poor - Bottom 25%"
        else:
            if percentile <= 25:
                return "Excellent - Low debt"
            elif percentile <= 50:
                return "Good"
            elif percentile <= 75:
                return "Moderate debt"
            else:
                return "High debt - Top 25%"

    def predict_default_probability(self, financial_ratios: Dict[str, float]) -> Dict:
        """
        Predict default probability for a company based on financial ratios
        
        Args:
            financial_ratios: Dictionary containing financial ratio values
            
        Returns:
            Dictionary with prediction results
        """
        try:
            if self.model is None or self.scoring_info is None or self.annual_data is None:
                return {
                    "probability": 0.5,
                    "risk_level": "UNKNOWN",
                    "confidence": 0.5,
                    "error": "Model or data not loaded",
                    "predicted_at": datetime.utcnow().isoformat()
                }

            single_variables = [
                'return on assets', 
                'net income margin', 
                'fixed asset turnover',  
                'total debt / total capital (%)',  
                'ebitda / interest expense', 
                'total debt / ebitda'
            ]

            required_fields = {
                'return_on_assets': 'return on assets',
                'profit_margin': 'net income margin',
                'fixed_asset_turnover': 'fixed asset turnover',
                'debt_to_equity_ratio': 'total debt / total capital (%)',
                'interest_coverage': 'ebitda / interest expense',
                'total_debt_ebitda': 'total debt / ebitda'
            }

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
                    "required_fields": list(required_fields.keys())
                }

            values = [
                financial_ratios['return_on_assets'],      
                financial_ratios['profit_margin'],        
                financial_ratios['fixed_asset_turnover'],  
                financial_ratios['debt_to_equity_ratio'],  
                financial_ratios['interest_coverage'],     
                financial_ratios['total_debt_ebitda']      
            ]

            df = pd.DataFrame([values], columns=single_variables)
            
            for value_col in single_variables:
                df = self.binned_runscoring(df, value_col)

            features = [
                'bin_return on assets', 
                'bin_net income margin', 
                'bin_fixed asset turnover',  
                'bin_total debt / total capital (%)',  
                'bin_ebitda / interest expense', 
                'bin_total debt / ebitda'
            ]

            X = df[features]

            probability = self.model.predict_proba(X)[:, 1][0]

            if probability >= 0.7:
                risk_level = "HIGH_RISK"
            elif probability >= 0.4:
                risk_level = "MEDIUM_RISK"
            else:
                risk_level = "LOW_RISK"

            confidence = max(abs(probability - 0.5) * 2, 0.5)

            benchmarks = self.get_historical_benchmarks(financial_ratios)

            return {
                "probability": float(probability),
                "risk_level": risk_level,
                "confidence": float(confidence),
                "model_features": {feature: float(df[feature].iloc[0]) for feature in features},
                "raw_inputs": {var: float(df[var].iloc[0]) for var in single_variables},
                "historical_benchmarks": benchmarks,
                "predicted_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"❌ Prediction error: {e}")
            return {
                "probability": 0.0,
                "risk_level": "NULL",
                "confidence": 0.0,
                "error": str(e)
            }

ml_service = MLModelService()
