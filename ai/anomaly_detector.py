"""
Anomaly Detection Module
Detects unusual patterns in motor sensor data using machine learning
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
import logging
from typing import Dict, List, Optional, Tuple
from config.settings import config

logger = logging.getLogger(__name__)

class MotorAnomalyDetector:
    """Advanced anomaly detection for motor sensor data"""
    
    def __init__(self):
        self.name = "AnomalyDetector"
        self.isolation_forest = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_columns = [
            'esp_current', 'esp_voltage', 'esp_rpm', 
            'env_temp_c', 'env_humidity', 
            'plc_motor_temp', 'plc_motor_voltage'
        ]
        self.model_path = f"{config.model_path}/anomaly_detector.joblib"
        self.scaler_path = f"{config.model_path}/anomaly_scaler.joblib"
        
        # Load existing model if available
        self._load_model()
    
    def prepare_features(self, data: pd.DataFrame) -> Optional[np.ndarray]:
        """
        Prepare features for anomaly detection
        
        Args:
            data: DataFrame with sensor readings
            
        Returns:
            Prepared feature array or None if insufficient data
        """
        try:
            if data.empty or len(data) < 1:
                return None
            
            # Select and validate feature columns
            available_columns = [col for col in self.feature_columns if col in data.columns]
            if len(available_columns) < 3:  # Need at least 3 features
                logger.warning("Insufficient feature columns for anomaly detection")
                return None
            
            # Fill missing values with column medians
            feature_data = data[available_columns].copy()
            feature_data = feature_data.fillna(feature_data.median())
            
            # Add derived features for better anomaly detection
            if 'esp_current' in feature_data.columns and 'esp_voltage' in feature_data.columns:
                feature_data['power_calculated'] = feature_data['esp_current'] * feature_data['esp_voltage']
            
            if 'plc_motor_temp' in feature_data.columns and 'env_temp_c' in feature_data.columns:
                feature_data['temp_differential'] = feature_data['plc_motor_temp'] - feature_data['env_temp_c']
            
            # Add statistical features for time series data
            if len(feature_data) > 5:
                for col in available_columns:
                    if col in feature_data.columns:
                        # Rolling statistics (if enough data)
                        feature_data[f'{col}_rolling_mean'] = feature_data[col].rolling(window=3, min_periods=1).mean()
                        feature_data[f'{col}_rolling_std'] = feature_data[col].rolling(window=3, min_periods=1).std().fillna(0)
            
            # Convert to numpy array
            features = feature_data.values
            
            # Handle any remaining NaN values
            features = np.nan_to_num(features, nan=0.0, posinf=1e6, neginf=-1e6)
            
            return features
            
        except Exception as e:
            logger.error(f"Error preparing features for anomaly detection: {e}")
            return None
    
    def train_model(self, training_data: pd.DataFrame, contamination: float = 0.1) -> bool:
        """
        Train the anomaly detection model
        
        Args:
            training_data: Historical sensor data for training
            contamination: Expected proportion of anomalies (0.05-0.2)
            
        Returns:
            True if training successful, False otherwise
        """
        try:
            if len(training_data) < 20:
                logger.warning("Insufficient training data for anomaly detector")
                return False
            
            # Prepare features
            features = self.prepare_features(training_data)
            if features is None:
                logger.error("Failed to prepare features for training")
                return False
            
            # Fit scaler
            self.scaler.fit(features)
            scaled_features = self.scaler.transform(features)
            
            # Train Isolation Forest
            self.isolation_forest = IsolationForest(
                contamination=contamination,
                random_state=42,
                n_estimators=100,
                max_samples='auto',
                bootstrap=False
            )
            
            self.isolation_forest.fit(scaled_features)
            self.is_trained = True
            
            # Save model
            self._save_model()
            
            logger.info(f"Anomaly detection model trained with {len(features)} samples")
            return True
            
        except Exception as e:
            logger.error(f"Error training anomaly detection model: {e}")
            return False
    
    def detect_anomalies(self, data: pd.DataFrame) -> Dict:
        """
        Detect anomalies in sensor data
        
        Args:
            data: Recent sensor data to analyze
            
        Returns:
            Dictionary with anomaly detection results
        """
        try:
            if not self.is_trained:
                logger.warning("Anomaly detector not trained yet")
                return {
                    'anomalies_detected': False,
                    'anomaly_count': 0,
                    'anomaly_score': 0.0,
                    'message': 'Model not trained yet'
                }
            
            # Prepare features
            features = self.prepare_features(data)
            if features is None:
                return {
                    'anomalies_detected': False,
                    'anomaly_count': 0,
                    'anomaly_score': 0.0,
                    'message': 'Insufficient data for analysis'
                }
            
            # Scale features
            scaled_features = self.scaler.transform(features)
            
            # Predict anomalies
            anomaly_labels = self.isolation_forest.predict(scaled_features)
            anomaly_scores = self.isolation_forest.decision_function(scaled_features)
            
            # Count anomalies (-1 indicates anomaly, 1 indicates normal)
            anomaly_count = np.sum(anomaly_labels == -1)
            total_points = len(anomaly_labels)
            anomaly_percentage = (anomaly_count / total_points) * 100
            
            # Calculate average anomaly score (lower is more anomalous)
            avg_anomaly_score = np.mean(anomaly_scores)
            
            # Determine severity
            if anomaly_percentage > 30:
                severity = 'HIGH'
                message = f'High anomaly rate: {anomaly_percentage:.1f}% of recent readings'
            elif anomaly_percentage > 15:
                severity = 'MEDIUM'
                message = f'Moderate anomaly rate: {anomaly_percentage:.1f}% of recent readings'
            elif anomaly_percentage > 5:
                severity = 'LOW'
                message = f'Some anomalies detected: {anomaly_percentage:.1f}% of recent readings'
            else:
                severity = 'NORMAL'
                message = 'No significant anomalies detected'
            
            # Find most anomalous readings
            most_anomalous_indices = np.where(anomaly_labels == -1)[0]
            anomalous_timestamps = []
            
            if len(most_anomalous_indices) > 0 and 'timestamp' in data.columns:
                anomalous_timestamps = data.iloc[most_anomalous_indices]['timestamp'].tolist()
            
            return {
                'anomalies_detected': anomaly_count > 0,
                'anomaly_count': int(anomaly_count),
                'total_readings': int(total_points),
                'anomaly_percentage': round(anomaly_percentage, 1),
                'avg_anomaly_score': round(avg_anomaly_score, 3),
                'severity': severity,
                'message': message,
                'anomalous_timestamps': anomalous_timestamps[:5],  # Top 5 most recent anomalies
                'model_trained': self.is_trained
            }
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return {
                'anomalies_detected': False,
                'anomaly_count': 0,
                'anomaly_score': 0.0,
                'message': f'Error in anomaly detection: {e}'
            }
    
    def analyze_anomaly_patterns(self, anomaly_results: Dict, data: pd.DataFrame) -> List[str]:
        """
        Analyze patterns in detected anomalies
        
        Args:
            anomaly_results: Results from detect_anomalies
            data: Original sensor data
            
        Returns:
            List of pattern descriptions
        """
        patterns = []
        
        try:
            if not anomaly_results.get('anomalies_detected', False):
                return patterns
            
            anomaly_percentage = anomaly_results.get('anomaly_percentage', 0)
            
            # Pattern 1: High frequency anomalies
            if anomaly_percentage > 25:
                patterns.append("High frequency anomaly pattern detected - possible sensor malfunction or system instability")
            
            # Pattern 2: Recent clustering
            anomalous_timestamps = anomaly_results.get('anomalous_timestamps', [])
            if len(anomalous_timestamps) >= 3:
                patterns.append("Recent anomaly clustering detected - monitor for developing issues")
            
            # Pattern 3: Specific parameter anomalies
            if not data.empty and len(data) > 5:
                recent_data = data.tail(10)
                
                # Check for temperature anomalies
                if 'plc_motor_temp' in recent_data.columns:
                    temp_data = recent_data['plc_motor_temp'].dropna()
                    if len(temp_data) > 0:
                        temp_std = temp_data.std()
                        temp_mean = temp_data.mean()
                        if temp_mean > 0 and temp_std / temp_mean > 0.2:
                            patterns.append("Temperature instability pattern - investigate thermal management")
                
                # Check for current anomalies
                if 'esp_current' in recent_data.columns:
                    current_data = recent_data['esp_current'].dropna()
                    if len(current_data) > 0:
                        current_std = current_data.std()
                        current_mean = current_data.mean()
                        if current_mean > 0 and current_std / current_mean > 0.3:
                            patterns.append("Current fluctuation pattern - check electrical connections and load stability")
                
                # Check for RPM anomalies
                if 'esp_rpm' in recent_data.columns:
                    rpm_data = recent_data['esp_rpm'].dropna()
                    if len(rpm_data) > 0:
                        rpm_std = rpm_data.std()
                        rpm_mean = rpm_data.mean()
                        if rpm_mean > 0 and rpm_std / rpm_mean > 0.1:
                            patterns.append("RPM variation pattern - inspect mechanical components and load coupling")
            
        except Exception as e:
            logger.error(f"Error analyzing anomaly patterns: {e}")
            patterns.append("Error analyzing anomaly patterns")
        
        return patterns
    
    def _save_model(self):
        """Save trained model and scaler to disk"""
        try:
            if self.is_trained and self.isolation_forest:
                joblib.dump(self.isolation_forest, self.model_path)
                joblib.dump(self.scaler, self.scaler_path)
                logger.info("Anomaly detection model saved successfully")
        except Exception as e:
            logger.error(f"Error saving anomaly detection model: {e}")
    
    def _load_model(self):
        """Load existing model and scaler from disk"""
        try:
            import os
            if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
                self.isolation_forest = joblib.load(self.model_path)
                self.scaler = joblib.load(self.scaler_path)
                self.is_trained = True
                logger.info("Anomaly detection model loaded successfully")
        except Exception as e:
            logger.warning(f"Could not load existing anomaly detection model: {e}")
    
    def get_model_info(self) -> Dict:
        """Get information about the current model"""
        return {
            'model_trained': self.is_trained,
            'model_type': 'Isolation Forest',
            'feature_columns': self.feature_columns,
            'model_path': self.model_path,
            'scaler_path': self.scaler_path
        }
