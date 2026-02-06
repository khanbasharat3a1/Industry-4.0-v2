"""
Health Analyzer Tests
Tests for motor health analysis and scoring algorithms.
"""

import pytest
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np

# Import the SKLEARN_AVAILABLE flag to conditionally skip tests
try:
    from ai.anomaly_detector import SKLEARN_AVAILABLE
except ImportError:
    SKLEARN_AVAILABLE = False

class TestHealthAnalyzer:
    """Test health analysis functionality"""
    
    def test_calculate_comprehensive_health(self, sample_sensor_data):
        """Test overall health score calculation"""
        from ai.health_analyzer import MotorHealthAnalyzer

        analyzer = MotorHealthAnalyzer()
        # Pass a dummy dataframe for recent_data to avoid DB calls
        health_data = analyzer.calculate_comprehensive_health(sample_sensor_data, pd.DataFrame())

        assert isinstance(health_data, dict)
        assert 'overall_health_score' in health_data
        health_score = health_data['overall_health_score']
        assert isinstance(health_score, (int, float))
        assert 0 <= health_score <= 100
            
    def test_electrical_health_scoring(self):
        """Test electrical health component scoring"""
        from ai.health_analyzer import MotorHealthAnalyzer
        analyzer = MotorHealthAnalyzer()

        # Test normal values
        normal_data = {'esp_current': 6.25, 'esp_voltage': 24.0}
        score, issues = analyzer.calculate_electrical_health(normal_data)
        assert isinstance(score, (int, float))
        assert score >= 80
        assert isinstance(issues, list)

        # Test abnormal values
        abnormal_data = {'esp_current': 18.0, 'esp_voltage': 15.0}
        score, issues = analyzer.calculate_electrical_health(abnormal_data)
        assert isinstance(score, (int, float))
        assert score <= 60
        assert isinstance(issues, list)
        assert len(issues) > 0

    def test_thermal_health_scoring(self):
        """Test thermal health component scoring"""
        from ai.health_analyzer import MotorHealthAnalyzer
        analyzer = MotorHealthAnalyzer()

        # Test normal temperature
        normal_data = {'plc_motor_temp': 40.0, 'env_temp_c': 25.0}
        score, issues = analyzer.calculate_thermal_health(normal_data)
        assert isinstance(score, (int, float))
        assert score >= 80

        # Test high temperature
        hot_data = {'plc_motor_temp': 95.0, 'env_temp_c': 40.0}
        score, issues = analyzer.calculate_thermal_health(hot_data)
        assert isinstance(score, (int, float))
        assert score <= 50

    def test_mechanical_health_scoring(self):
        """Test mechanical health component scoring"""
        from ai.health_analyzer import MotorHealthAnalyzer
        analyzer = MotorHealthAnalyzer()

        # Test normal RPM
        normal_data = {'esp_rpm': 2750}
        score, issues = analyzer.calculate_mechanical_health(normal_data)
        assert isinstance(score, (int, float))
        assert score >= 80

    @pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn is not installed")
    def test_anomaly_detection(self, sample_dataframe):
        """Test anomaly detection in sensor data"""
        from ai.anomaly_detector import MotorAnomalyDetector

        detector = MotorAnomalyDetector()

        # Train with sample data
        assert detector.train_model(sample_dataframe)

        # Test normal data point
        normal_df = pd.DataFrame([{
            'esp_current': 6.25, 'esp_voltage': 24.0, 'esp_rpm': 2750,
            'plc_motor_temp': 42.5, 'env_temp_c': 25.0, 'env_humidity': 45.0
        }])
        result = detector.detect_anomalies(normal_df)
        assert isinstance(result, dict)
        assert not result['anomalies_detected']

        # Test anomalous data point
        anomaly_df = pd.DataFrame([{
            'esp_current': 50.0, 'esp_voltage': 5.0, 'esp_rpm': 1000,
            'plc_motor_temp': 100.0, 'env_temp_c': 50.0, 'env_humidity': 90.0
        }])
        result = detector.detect_anomalies(anomaly_df)
        assert isinstance(result, dict)
        # We can't guarantee detection, but we can check the structure
        assert 'anomalies_detected' in result

    def test_health_score_bounds(self):
        """Test that health scores are always within valid bounds"""
        from ai.health_analyzer import MotorHealthAnalyzer
        analyzer = MotorHealthAnalyzer()

        # Test with extreme values
        extreme_data = {
            'esp_current': 999, 'esp_voltage': -100, 'esp_rpm': -5000,
            'plc_motor_temp': 200, 'env_temp_c': -50
        }
        health_data = analyzer.calculate_comprehensive_health(extreme_data, pd.DataFrame())
        health_score = health_data['overall_health_score']

        assert 0 <= health_score <= 100

class TestHealthThresholds:
    """Test health scoring thresholds"""
    
    @pytest.fixture
    def config(self):
        """Load config for testing thresholds."""
        from config.settings import config
        return config

    def test_temperature_thresholds(self, config):
        """Test temperature threshold classifications"""
        assert hasattr(config.thresholds, 'motor_temp_warning')
        assert hasattr(config.thresholds, 'motor_temp_critical')
        assert config.thresholds.motor_temp_critical > config.thresholds.motor_temp_warning
    
    def test_voltage_thresholds(self, config):
        """Test voltage threshold classifications"""
        assert hasattr(config.thresholds, 'voltage_min_warning')
        assert hasattr(config.thresholds, 'voltage_max_warning')
        assert config.thresholds.voltage_max_warning > config.thresholds.voltage_min_warning
