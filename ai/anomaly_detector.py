"""
Anomaly Detection Module
Detects unusual patterns in motor sensor data using machine learning.
This module is designed to be optional. If scikit-learn is not installed,
the anomaly detection features will be disabled.
"""

import numpy as np
import pandas as pd
import joblib
import logging
from typing import Dict, List, Optional, Tuple
from config.settings import config

logger = logging.getLogger(__name__)

# --- Optional scikit-learn import ---
try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    class IsolationForest: pass
    class StandardScaler: pass

class MotorAnomalyDetector:
    """
    Advanced anomaly detection for motor sensor data.
    Gracefully handles the absence of scikit-learn.
    """
    
    def __init__(self):
        self.name = "AnomalyDetector"
        self.isolation_forest = None
        self.scaler = None
        self.is_trained = False

        # This is the fixed, canonical list of features the model was trained on.
        self.canonical_features = [
            'esp_current', 'esp_voltage', 'esp_rpm', 'env_temp_c', 'env_humidity',
            'plc_motor_temp', 'plc_motor_voltage', 'power_calculated', 'temp_differential',
            'esp_current_rolling_mean', 'esp_current_rolling_std',
            'plc_motor_temp_rolling_mean', 'plc_motor_temp_rolling_std'
        ]
        
        if SKLEARN_AVAILABLE:
            self.scaler = StandardScaler()
            self.model_path = f"{config.model_path}/anomaly_detector.joblib"
            self.scaler_path = f"{config.model_path}/anomaly_scaler.joblib"
            self._load_model()
        else:
            logger.warning("scikit-learn is not installed. Anomaly detection features will be disabled.")

    def prepare_features(self, data: pd.DataFrame) -> Optional[np.ndarray]:
        """
        Prepare features for anomaly detection, ensuring a consistent feature set.
        """
        if not SKLEARN_AVAILABLE: return None
        try:
            if data.empty: return None

            # Start with columns that are present in the input data
            feature_data = data.copy()

            # 1. Add derived features
            if 'esp_current' in feature_data and 'esp_voltage' in feature_data:
                feature_data['power_calculated'] = feature_data['esp_current'] * feature_data['esp_voltage']
            if 'plc_motor_temp' in feature_data and 'env_temp_c' in feature_data:
                feature_data['temp_differential'] = feature_data['plc_motor_temp'] - feature_data['env_temp_c']

            # 2. Add rolling statistical features
            if len(feature_data) > 1:
                if 'esp_current' in feature_data:
                    feature_data['esp_current_rolling_mean'] = feature_data['esp_current'].rolling(window=3, min_periods=1).mean()
                    feature_data['esp_current_rolling_std'] = feature_data['esp_current'].rolling(window=3, min_periods=1).std()
                if 'plc_motor_temp' in feature_data:
                    feature_data['plc_motor_temp_rolling_mean'] = feature_data['plc_motor_temp'].rolling(window=3, min_periods=1).mean()
                    feature_data['plc_motor_temp_rolling_std'] = feature_data['plc_motor_temp'].rolling(window=3, min_periods=1).std()

            # 3. Align DataFrame with the canonical feature list
            # This adds any missing columns with NaN
            feature_data = feature_data.reindex(columns=self.canonical_features)

            # 4. Fill any remaining NaN values (from reindexing or rolling std on small windows)
            feature_data = feature_data.fillna(0)
            
            # 5. Convert to numpy array
            features = feature_data.values
            return np.nan_to_num(features, nan=0.0, posinf=1e6, neginf=-1e6)

        except Exception as e:
            logger.error(f"Error preparing features for anomaly detection: {e}", exc_info=True)
            return None

    def train_model(self, training_data: pd.DataFrame, contamination: float = 0.1) -> bool:
        """Train the anomaly detection model."""
        if not SKLEARN_AVAILABLE: return False
        try:
            if len(training_data) < 20: return False
            features = self.prepare_features(training_data)
            if features is None: return False
            
            self.scaler.fit(features)
            scaled_features = self.scaler.transform(features)
            
            self.isolation_forest = IsolationForest(contamination=contamination, random_state=42)
            self.isolation_forest.fit(scaled_features)
            self.is_trained = True
            self._save_model()
            logger.info(f"Anomaly detection model trained with {len(features)} samples.")
            return True
        except Exception as e:
            logger.error(f"Error training anomaly detection model: {e}")
            return False

    def detect_anomalies(self, data: pd.DataFrame) -> Dict:
        """Detect anomalies in sensor data."""
        if not self.is_trained or not SKLEARN_AVAILABLE:
            return {'anomalies_detected': False, 'message': 'Anomaly detector not available or not trained.'}
        
        try:
            features = self.prepare_features(data)
            if features is None:
                return {'anomalies_detected': False, 'message': 'Insufficient data for analysis.'}
            
            # Ensure the number of features matches the scaler's expectations
            if features.shape[1] != self.scaler.n_features_in_:
                logger.error(f"Feature mismatch: Got {features.shape[1]} features, but scaler expects {self.scaler.n_features_in_}.")
                return {'anomalies_detected': False, 'message': 'Feature mismatch during prediction.'}

            scaled_features = self.scaler.transform(features)
            anomaly_labels = self.isolation_forest.predict(scaled_features)
            anomaly_scores = self.isolation_forest.decision_function(scaled_features)
            anomaly_count = np.sum(anomaly_labels == -1)
            total_points = len(anomaly_labels)
            anomaly_percentage = (anomaly_count / total_points) * 100

            if anomaly_percentage > 30: severity = 'HIGH'
            elif anomaly_percentage > 15: severity = 'MEDIUM'
            elif anomaly_percentage > 5: severity = 'LOW'
            else: severity = 'NORMAL'

            return {
                'anomalies_detected': anomaly_count > 0,
                'anomaly_count': int(anomaly_count),
                'anomaly_percentage': round(anomaly_percentage, 1),
                'severity': severity,
                'message': f'{severity} anomaly rate: {anomaly_percentage:.1f}% of recent readings'
            }
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}", exc_info=True)
            return {'anomalies_detected': False, 'message': f'Error in anomaly detection: {e}'}

    def _save_model(self):
        """Save trained model and scaler to disk."""
        if not SKLEARN_AVAILABLE: return
        try:
            if self.is_trained and self.isolation_forest:
                joblib.dump(self.isolation_forest, self.model_path)
                joblib.dump(self.scaler, self.scaler_path)
                logger.info("Anomaly detection model saved successfully.")
        except Exception as e:
            logger.error(f"Error saving anomaly detection model: {e}")

    def _load_model(self):
        """Load existing model and scaler from disk."""
        if not SKLEARN_AVAILABLE: return
        try:
            import os
            if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
                self.isolation_forest = joblib.load(self.model_path)
                self.scaler = joblib.load(self.scaler_path)
                self.is_trained = True
                logger.info("Anomaly detection model loaded successfully.")
        except Exception as e:
            logger.warning(f"Could not load existing anomaly detection model: {e}")
