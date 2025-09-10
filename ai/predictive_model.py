"""
AI Motor Monitoring - Predictive Model Module

This module implements machine learning models for motor fault prediction and 
maintenance scheduling based on sensor data and historical patterns.

Features:
- Random Forest Classifier for fault prediction
- Model training with historical data
- Real-time prediction capabilities
- Model persistence and versioning
- Performance metrics and validation
"""

import os
import logging
import pickle
import joblib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.impute import SimpleImputer
from config.settings import config

logger = logging.getLogger(__name__)

class MotorPredictiveModel:
    """
    Advanced predictive model for motor fault detection and maintenance scheduling
    """
    
    def __init__(self):
        self.name = "MotorPredictiveModel"
        
        # Model components
        self.fault_classifier = None
        self.anomaly_detector = None
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.imputer = SimpleImputer(strategy='median')
        
        # Model metadata
        self.model_version = "1.0"
        self.last_trained = None
        self.feature_names = []
        self.target_classes = []
        
        # Model paths
        self.model_dir = os.path.join(config.model_path, 'predictive')
        self.ensure_model_directory()
        
        # Performance metrics
        self.training_accuracy = 0.0
        self.validation_accuracy = 0.0
        self.feature_importance = {}
        
        # Load existing model if available
        self.load_model()
    
    def ensure_model_directory(self):
        """Ensure model directory exists"""
        os.makedirs(self.model_dir, exist_ok=True)
    
    def prepare_training_data(self, sensor_data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare sensor data for training
        
        Args:
            sensor_data: Raw sensor data from database
            
        Returns:
            Tuple of (features, target)
        """
        try:
            # Define feature columns based on your sensor data
            feature_columns = [
                'esp_current', 'esp_voltage', 'esp_rpm',
                'plc_motor_temp', 'env_temp_c', 'env_humidity',
                'overall_health_score', 'electrical_health', 
                'thermal_health', 'mechanical_health',
                'power_consumption'
            ]
            
            # Filter available columns
            available_features = [col for col in feature_columns if col in sensor_data.columns]
            
            if not available_features:
                raise ValueError("No valid feature columns found in sensor data")
            
            # Extract features
            X = sensor_data[available_features].copy()
            
            # Create target variable (fault prediction)
            # Define fault conditions based on health scores and thresholds
            y = self.create_fault_labels(sensor_data)
            
            # Handle missing values
            X = pd.DataFrame(
                self.imputer.fit_transform(X),
                columns=available_features,
                index=X.index
            )
            
            self.feature_names = available_features
            logger.info(f"Training data prepared: {len(X)} samples, {len(available_features)} features")
            
            return X, y
            
        except Exception as e:
            logger.error(f"Error preparing training data: {e}")
            raise
    
    def create_fault_labels(self, sensor_data: pd.DataFrame) -> pd.Series:
        """
        Create fault labels based on sensor readings and health scores
        
        Args:
            sensor_data: Sensor data with health scores
            
        Returns:
            Series with fault labels
        """
        try:
            conditions = []
            
            # Critical temperature fault
            if 'plc_motor_temp' in sensor_data.columns:
                conditions.append(sensor_data['plc_motor_temp'] > config.thresholds.motor_temp_critical)
            
            # Voltage fault
            if 'esp_voltage' in sensor_data.columns:
                voltage_fault = (
                    (sensor_data['esp_voltage'] < config.thresholds.voltage_min_critical) |
                    (sensor_data['esp_voltage'] > config.thresholds.voltage_max_critical)
                )
                conditions.append(voltage_fault)
            
            # Current fault
            if 'esp_current' in sensor_data.columns:
                current_fault = sensor_data['esp_current'] > config.thresholds.current_max_critical
                conditions.append(current_fault)
            
            # RPM fault
            if 'esp_rpm' in sensor_data.columns:
                rpm_fault = (
                    (sensor_data['esp_rpm'] < config.thresholds.rpm_min_critical) |
                    (sensor_data['esp_rpm'] > config.thresholds.rpm_max_critical)
                )
                conditions.append(rpm_fault)
            
            # Overall health fault
            if 'overall_health_score' in sensor_data.columns:
                health_fault = sensor_data['overall_health_score'] < 60.0
                conditions.append(health_fault)
            
            # Combine all fault conditions
            if conditions:
                fault_labels = pd.Series(False, index=sensor_data.index)
                for condition in conditions:
                    fault_labels = fault_labels | condition
            else:
                # If no conditions available, create synthetic labels for demonstration
                fault_labels = pd.Series(np.random.choice([0, 1], size=len(sensor_data), p=[0.8, 0.2]), 
                                       index=sensor_data.index)
            
            # Convert to categorical labels
            fault_categories = []
            for is_fault in fault_labels:
                if is_fault:
                    fault_categories.append('FAULT')
                else:
                    fault_categories.append('NORMAL')
            
            return pd.Series(fault_categories, index=sensor_data.index)
            
        except Exception as e:
            logger.error(f"Error creating fault labels: {e}")
            # Return default labels
            return pd.Series(['NORMAL'] * len(sensor_data), index=sensor_data.index)
    
    def train_model(self, sensor_data: pd.DataFrame, validation_split: float = 0.2) -> Dict:
        """
        Train the predictive model
        
        Args:
            sensor_data: Historical sensor data
            validation_split: Fraction of data for validation
            
        Returns:
            Training results dictionary
        """
        try:
            logger.info("Starting model training...")
            
            # Prepare training data
            X, y = self.prepare_training_data(sensor_data)
            
            if len(X) < 10:
                raise ValueError(f"Insufficient training data: {len(X)} samples")
            
            # Encode target labels
            y_encoded = self.label_encoder.fit_transform(y)
            self.target_classes = self.label_encoder.classes_
            
            # Split data
            X_train, X_val, y_train, y_val = train_test_split(
                X, y_encoded, 
                test_size=validation_split, 
                random_state=42, 
                stratify=y_encoded if len(np.unique(y_encoded)) > 1 else None
            )
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_val_scaled = self.scaler.transform(X_val)
            
            # Train fault classifier
            self.fault_classifier = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                class_weight='balanced'
            )
            
            self.fault_classifier.fit(X_train_scaled, y_train)
            
            # Train anomaly detector
            self.anomaly_detector = IsolationForest(
                contamination=0.1,
                random_state=42
            )
            self.anomaly_detector.fit(X_train_scaled)
            
            # Calculate performance metrics
            y_train_pred = self.fault_classifier.predict(X_train_scaled)
            y_val_pred = self.fault_classifier.predict(X_val_scaled)
            
            self.training_accuracy = accuracy_score(y_train, y_train_pred)
            self.validation_accuracy = accuracy_score(y_val, y_val_pred)
            
            # Feature importance
            if hasattr(self.fault_classifier, 'feature_importances_'):
                self.feature_importance = dict(zip(
                    self.feature_names,
                    self.fault_classifier.feature_importances_
                ))
            
            # Cross-validation score
            cv_scores = cross_val_score(
                self.fault_classifier, X_train_scaled, y_train, cv=3
            )
            
            # Update metadata
            self.last_trained = datetime.now()
            
            # Save model
            self.save_model()
            
            # Generate classification report
            classification_rep = classification_report(
                y_val, y_val_pred, 
                target_names=self.target_classes,
                output_dict=True
            )
            
            training_results = {
                'training_accuracy': self.training_accuracy,
                'validation_accuracy': self.validation_accuracy,
                'cross_validation_mean': cv_scores.mean(),
                'cross_validation_std': cv_scores.std(),
                'feature_importance': self.feature_importance,
                'classification_report': classification_rep,
                'training_samples': len(X_train),
                'validation_samples': len(X_val),
                'features_used': self.feature_names,
                'target_classes': list(self.target_classes),
                'last_trained': self.last_trained.isoformat()
            }
            
            logger.info(f"Model training completed successfully")
            logger.info(f"Training accuracy: {self.training_accuracy:.3f}")
            logger.info(f"Validation accuracy: {self.validation_accuracy:.3f}")
            logger.info(f"Cross-validation score: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
            
            return training_results
            
        except Exception as e:
            logger.error(f"Error during model training: {e}")
            raise
    
    def predict_fault(self, sensor_reading: Dict) -> Dict:
        """
        Predict fault probability for a single sensor reading
        
        Args:
            sensor_reading: Dictionary with current sensor values
            
        Returns:
            Prediction results dictionary
        """
        try:
            if self.fault_classifier is None:
                raise ValueError("Model not trained. Please train the model first.")
            
            # Prepare input data
            input_data = self.prepare_prediction_input(sensor_reading)
            
            if input_data is None:
                return {
                    'status': 'error',
                    'message': 'Insufficient sensor data for prediction'
                }
            
            # Scale input
            input_scaled = self.scaler.transform(input_data)
            
            # Fault prediction
            fault_prob = self.fault_classifier.predict_proba(input_scaled)[0]
            fault_pred = self.fault_classifier.predict(input_scaled)[0]
            fault_class = self.label_encoder.inverse_transform([fault_pred])[0]
            
            # Anomaly detection
            anomaly_score = self.anomaly_detector.decision_function(input_scaled)[0]
            is_anomaly = self.anomaly_detector.predict(input_scaled)[0] == -1
            
            # Risk assessment
            risk_level = self.assess_risk_level(fault_prob, anomaly_score)
            
            prediction_result = {
                'status': 'success',
                'fault_prediction': fault_class,
                'fault_probability': {
                    class_name: float(prob) 
                    for class_name, prob in zip(self.target_classes, fault_prob)
                },
                'anomaly_detected': bool(is_anomaly),
                'anomaly_score': float(anomaly_score),
                'risk_level': risk_level,
                'confidence': float(max(fault_prob)),
                'prediction_time': datetime.now().isoformat(),
                'model_version': self.model_version
            }
            
            logger.debug(f"Fault prediction completed: {fault_class} (confidence: {max(fault_prob):.3f})")
            
            return prediction_result
            
        except Exception as e:
            logger.error(f"Error during fault prediction: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'prediction_time': datetime.now().isoformat()
            }
    
    def prepare_prediction_input(self, sensor_reading: Dict) -> Optional[np.ndarray]:
        """
        Prepare sensor reading for prediction
        
        Args:
            sensor_reading: Dictionary with sensor values
            
        Returns:
            Prepared input array or None if insufficient data
        """
        try:
            if not self.feature_names:
                return None
            
            # Extract feature values
            input_values = []
            for feature_name in self.feature_names:
                value = sensor_reading.get(feature_name)
                if value is not None:
                    input_values.append(float(value))
                else:
                    # Use median value from training data
                    input_values.append(0.0)  # Simple fallback
            
            return np.array(input_values).reshape(1, -1)
            
        except Exception as e:
            logger.error(f"Error preparing prediction input: {e}")
            return None
    
    def assess_risk_level(self, fault_prob: np.ndarray, anomaly_score: float) -> str:
        """
        Assess overall risk level based on fault probability and anomaly score
        
        Args:
            fault_prob: Fault probability array
            anomaly_score: Anomaly detection score
            
        Returns:
            Risk level string
        """
        try:
            fault_confidence = max(fault_prob)
            
            # Determine risk level
            if fault_confidence > 0.8 or anomaly_score < -0.5:
                return 'CRITICAL'
            elif fault_confidence > 0.6 or anomaly_score < -0.3:
                return 'HIGH'
            elif fault_confidence > 0.4 or anomaly_score < -0.1:
                return 'MEDIUM'
            else:
                return 'LOW'
                
        except Exception:
            return 'UNKNOWN'
    
    def get_maintenance_recommendation(self, prediction_result: Dict) -> Dict:
        """
        Generate maintenance recommendations based on prediction
        
        Args:
            prediction_result: Result from predict_fault()
            
        Returns:
            Maintenance recommendation dictionary
        """
        try:
            risk_level = prediction_result.get('risk_level', 'UNKNOWN')
            fault_prediction = prediction_result.get('fault_prediction', 'UNKNOWN')
            
            recommendations = {
                'CRITICAL': {
                    'action': 'IMMEDIATE_SHUTDOWN',
                    'description': 'Critical fault detected - immediate shutdown required',
                    'timeline': 'IMMEDIATE',
                    'priority': 'CRITICAL'
                },
                'HIGH': {
                    'action': 'SCHEDULED_MAINTENANCE',
                    'description': 'High risk detected - schedule maintenance within 24 hours',
                    'timeline': '24_HOURS',
                    'priority': 'HIGH'
                },
                'MEDIUM': {
                    'action': 'MONITOR_CLOSELY',
                    'description': 'Medium risk - increase monitoring frequency',
                    'timeline': '7_DAYS',
                    'priority': 'MEDIUM'
                },
                'LOW': {
                    'action': 'ROUTINE_MONITORING',
                    'description': 'Normal operation - continue routine monitoring',
                    'timeline': '30_DAYS',
                    'priority': 'LOW'
                }
            }
            
            base_recommendation = recommendations.get(risk_level, recommendations['LOW'])
            
            return {
                'recommendation': base_recommendation,
                'generated_at': datetime.now().isoformat(),
                'based_on': {
                    'risk_level': risk_level,
                    'fault_prediction': fault_prediction,
                    'model_version': self.model_version
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating maintenance recommendation: {e}")
            return {
                'recommendation': {
                    'action': 'ERROR',
                    'description': 'Unable to generate recommendation',
                    'timeline': 'UNKNOWN',
                    'priority': 'UNKNOWN'
                },
                'error': str(e)
            }
    
    def save_model(self):
        """Save trained model to disk"""
        try:
            if self.fault_classifier is None:
                logger.warning("No trained model to save")
                return
            
            model_data = {
                'fault_classifier': self.fault_classifier,
                'anomaly_detector': self.anomaly_detector,
                'scaler': self.scaler,
                'label_encoder': self.label_encoder,
                'imputer': self.imputer,
                'model_version': self.model_version,
                'last_trained': self.last_trained,
                'feature_names': self.feature_names,
                'target_classes': self.target_classes,
                'training_accuracy': self.training_accuracy,
                'validation_accuracy': self.validation_accuracy,
                'feature_importance': self.feature_importance
            }
            
            model_path = os.path.join(self.model_dir, 'motor_predictive_model.joblib')
            joblib.dump(model_data, model_path)
            
            logger.info(f"Model saved to {model_path}")
            
        except Exception as e:
            logger.error(f"Error saving model: {e}")
    
    def load_model(self):
        """Load trained model from disk"""
        try:
            model_path = os.path.join(self.model_dir, 'motor_predictive_model.joblib')
            
            if not os.path.exists(model_path):
                logger.info("No saved model found")
                return False
            
            model_data = joblib.load(model_path)
            
            # Restore model components
            self.fault_classifier = model_data.get('fault_classifier')
            self.anomaly_detector = model_data.get('anomaly_detector')
            self.scaler = model_data.get('scaler')
            self.label_encoder = model_data.get('label_encoder')
            self.imputer = model_data.get('imputer')
            self.model_version = model_data.get('model_version', 'unknown')
            self.last_trained = model_data.get('last_trained')
            self.feature_names = model_data.get('feature_names', [])
            self.target_classes = model_data.get('target_classes', [])
            self.training_accuracy = model_data.get('training_accuracy', 0.0)
            self.validation_accuracy = model_data.get('validation_accuracy', 0.0)
            self.feature_importance = model_data.get('feature_importance', {})
            
            logger.info(f"Model loaded successfully from {model_path}")
            logger.info(f"Model version: {self.model_version}")
            logger.info(f"Last trained: {self.last_trained}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
    
    def get_model_info(self) -> Dict:
        """Get model information and statistics"""
        return {
            'model_version': self.model_version,
            'last_trained': self.last_trained.isoformat() if self.last_trained else None,
            'feature_names': self.feature_names,
            'target_classes': list(self.target_classes),
            'training_accuracy': self.training_accuracy,
            'validation_accuracy': self.validation_accuracy,
            'feature_importance': self.feature_importance,
            'is_trained': self.fault_classifier is not None,
            'model_type': 'Random Forest Classifier + Isolation Forest'
        }

# Example usage and testing
if __name__ == "__main__":
    # Create sample data for testing
    np.random.seed(42)
    
    sample_data = pd.DataFrame({
        'esp_current': np.random.normal(6.25, 1.0, 1000),
        'esp_voltage': np.random.normal(24.0, 2.0, 1000),
        'esp_rpm': np.random.normal(2750, 100, 1000),
        'plc_motor_temp': np.random.normal(40, 8, 1000),
        'env_temp_c': np.random.normal(25, 5, 1000),
        'env_humidity': np.random.normal(45, 10, 1000),
        'overall_health_score': np.random.normal(85, 15, 1000),
        'electrical_health': np.random.normal(88, 12, 1000),
        'thermal_health': np.random.normal(82, 18, 1000),
        'mechanical_health': np.random.normal(87, 14, 1000),
        'power_consumption': np.random.normal(0.15, 0.05, 1000)
    })
    
    # Initialize and train model
    model = MotorPredictiveModel()
    
    try:
        # Train the model
        results = model.train_model(sample_data)
        print("Training Results:")
        print(f"Validation Accuracy: {results['validation_accuracy']:.3f}")
        print(f"Features: {results['features_used']}")
        
        # Test prediction
        test_reading = {
            'esp_current': 7.5,
            'esp_voltage': 22.0,
            'esp_rpm': 2600,
            'plc_motor_temp': 55.0,
            'env_temp_c': 28.0,
            'env_humidity': 60.0,
            'overall_health_score': 65.0,
            'electrical_health': 70.0,
            'thermal_health': 60.0,
            'mechanical_health': 68.0,
            'power_consumption': 0.18
        }
        
        prediction = model.predict_fault(test_reading)
        print("\nPrediction Results:")
        print(f"Fault Prediction: {prediction['fault_prediction']}")
        print(f"Risk Level: {prediction['risk_level']}")
        print(f"Confidence: {prediction['confidence']:.3f}")
        
        # Get maintenance recommendation
        recommendation = model.get_maintenance_recommendation(prediction)
        print(f"\nRecommendation: {recommendation['recommendation']['action']}")
        print(f"Description: {recommendation['recommendation']['description']}")
        
    except Exception as e:
        print(f"Error: {e}")
