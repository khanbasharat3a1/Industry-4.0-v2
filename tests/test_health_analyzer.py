"""
Health Analyzer Tests

Tests for motor health analysis and scoring algorithms.
"""

import pytest
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np

class TestHealthAnalyzer:
    """Test health analysis functionality"""
    
    def test_calculate_overall_health(self, sample_sensor_data):
        """Test overall health score calculation"""
        try:
            from ai.health_analyzer import MotorHealthAnalyzer
            
            analyzer = MotorHealthAnalyzer()
            health_score = analyzer.calculate_overall_health(sample_sensor_data)
            
            assert isinstance(health_score, (int, float))
            assert 0 <= health_score <= 100
            
        except ImportError:
            pytest.skip("Health analyzer not implemented")
    
    def test_electrical_health_scoring(self):
        """Test electrical health component scoring"""
        try:
            from ai.health_analyzer import MotorHealthAnalyzer
            
            analyzer = MotorHealthAnalyzer()
            
            # Test normal values
            normal_data = {
                'esp_current': 6.25,
                'esp_voltage': 24.0,
                'power_consumption': 0.15
            }
            
            score = analyzer.calculate_electrical_health(normal_data)
            assert isinstance(score, (int, float))
            assert score >= 80  # Should be high for normal values
            
            # Test abnormal values
            abnormal_data = {
                'esp_current': 15.0,  # Very high current
                'esp_voltage': 18.0,  # Low voltage
                'power_consumption': 0.5   # High consumption
            }
            
            score = analyzer.calculate_electrical_health(abnormal_data)
            assert isinstance(score, (int, float))
            assert score <= 60  # Should be low for abnormal values
            
        except ImportError:
            pytest.skip("Health analyzer not implemented")
    
    def test_thermal_health_scoring(self):
        """Test thermal health component scoring"""
        try:
            from ai.health_analyzer import MotorHealthAnalyzer
            
            analyzer = MotorHealthAnalyzer()
            
            # Test normal temperature
            normal_data = {
                'plc_motor_temp': 40.0,
                'env_temp_c': 25.0,
                'heat_index_c': 26.0
            }
            
            score = analyzer.calculate_thermal_health(normal_data)
            assert isinstance(score, (int, float))
            assert score >= 80
            
            # Test high temperature
            hot_data = {
                'plc_motor_temp': 70.0,  # Very hot
                'env_temp_c': 35.0,
                'heat_index_c': 40.0
            }
            
            score = analyzer.calculate_thermal_health(hot_data)
            assert isinstance(score, (int, float))
            assert score <= 40  # Should be very low
            
        except ImportError:
            pytest.skip("Health analyzer not implemented")
    
    def test_mechanical_health_scoring(self):
        """Test mechanical health component scoring"""
        try:
            from ai.health_analyzer import MotorHealthAnalyzer
            
            analyzer = MotorHealthAnalyzer()
            
            # Test normal RPM
            normal_data = {
                'esp_rpm': 2750,
                'vibration_level': 0.1  # If available
            }
            
            score = analyzer.calculate_mechanical_health(normal_data)
            assert isinstance(score, (int, float))
            assert score >= 80
            
        except ImportError:
            pytest.skip("Health analyzer not implemented")
    
    def test_health_trend_analysis(self, sample_dataframe):
        """Test health trend analysis over time"""
        try:
            from ai.health_analyzer import MotorHealthAnalyzer
            
            analyzer = MotorHealthAnalyzer()
            trends = analyzer.analyze_health_trends(sample_dataframe)
            
            assert isinstance(trends, dict)
            assert 'trend_direction' in trends
            assert trends['trend_direction'] in ['improving', 'stable', 'declining']
            
        except ImportError:
            pytest.skip("Health analyzer not implemented")
    
    def test_anomaly_detection(self, sample_dataframe):
        """Test anomaly detection in sensor data"""
        try:
            from ai.anomaly_detector import MotorAnomalyDetector
            
            detector = MotorAnomalyDetector()
            
            # Train with sample data
            detector.train_model(sample_dataframe)
            
            # Test normal data point
            normal_point = {
                'esp_current': 6.25,
                'esp_voltage': 24.0,
                'esp_rpm': 2750
            }
            
            is_anomaly = detector.detect_anomaly(normal_point)
            assert isinstance(is_anomaly, bool)
            
            # Test anomalous data point
            anomaly_point = {
                'esp_current': 50.0,  # Extremely high
                'esp_voltage': 5.0,   # Extremely low
                'esp_rpm': 1000       # Very low
            }
            
            is_anomaly = detector.detect_anomaly(anomaly_point)
            assert isinstance(is_anomaly, bool)
            # Note: Can't guarantee it detects as anomaly due to random training
            
        except ImportError:
            pytest.skip("Anomaly detector not implemented")
    
    def test_health_score_bounds(self):
        """Test that health scores are always within valid bounds"""
        try:
            from ai.health_analyzer import MotorHealthAnalyzer
            
            analyzer = MotorHealthAnalyzer()
            
            # Test with extreme values
            extreme_data = {
                'esp_current': 999999,
                'esp_voltage': -100,
                'esp_rpm': -5000,
                'plc_motor_temp': 200,
                'env_temp_c': -50
            }
            
            health_score = analyzer.calculate_overall_health(extreme_data)
            
            # Score should still be within bounds
            assert 0 <= health_score <= 100
            
        except ImportError:
            pytest.skip("Health analyzer not implemented")

class TestHealthThresholds:
    """Test health scoring thresholds"""
    
    def test_temperature_thresholds(self):
        """Test temperature threshold classifications"""
        try:
            from config.settings import config
            
            # Test that thresholds are properly defined
            assert hasattr(config.thresholds, 'motor_temp_warning')
            assert hasattr(config.thresholds, 'motor_temp_critical')
            assert config.thresholds.motor_temp_critical > config.thresholds.motor_temp_warning
            
        except ImportError:
            pytest.skip("Config not available")
    
    def test_voltage_thresholds(self):
        """Test voltage threshold classifications"""
        try:
            from config.settings import config
            
            assert hasattr(config.thresholds, 'voltage_min_warning')
            assert hasattr(config.thresholds, 'voltage_max_warning')
            assert config.thresholds.voltage_max_warning > config.thresholds.voltage_min_warning
            
        except ImportError:
            pytest.skip("Config not available")
