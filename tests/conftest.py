"""
Pytest Configuration and Fixtures

Contains shared fixtures and configuration for all tests in the motor monitoring system.
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch
from flask import Flask
from datetime import datetime
import pandas as pd

# Set test environment
os.environ['TESTING'] = 'True'

@pytest.fixture(scope='session')
def app():
    """Create Flask application for testing"""
    try:
        from main import create_flask_app
        app, socketio = create_flask_app()
        
        app.config.update({
            'TESTING': True,
            'WTF_CSRF_ENABLED': False,
            'SECRET_KEY': 'test-secret-key',
            'DATABASE_URL': 'sqlite:///:memory:'
        })
        
        yield app
        
    except ImportError:
        # Fallback if main module not available
        app = Flask(__name__)
        app.config['TESTING'] = True
        
        @app.route('/')
        def index():
            return 'Test App'
            
        @app.route('/health')
        def health():
            return {'status': 'healthy'}
            
        yield app

@pytest.fixture
def client(app):
    """Flask test client"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Flask CLI runner"""
    return app.test_cli_runner()

@pytest.fixture
def sample_sensor_data():
    """Sample sensor data for testing"""
    return {
        'esp_current': 6.25,
        'esp_voltage': 24.1,
        'esp_rpm': 2750,
        'plc_motor_temp': 42.5,
        'env_temp_c': 24.8,
        'env_humidity': 45.2,
        'relay1_status': 'ON',
        'relay2_status': 'OFF',
        'relay3_status': 'ON',
        'timestamp': datetime.now().isoformat()
    }

@pytest.fixture
def sample_esp_data():
    """Sample ESP POST data"""
    return {
        'TYPE': 'ADU_TEXT',
        'VAL1': '6.25',  # Current
        'VAL2': '24.0',  # Voltage  
        'VAL3': '2750',  # RPM
        'VAL4': '42.5',  # Motor temp
        'VAL5': '45.8',  # Humidity
        'VAL6': '76.5',  # Temp F
        'VAL7': '24.8',  # Heat index C
        'VAL8': '76.6',  # Heat index F
        'VAL9': 'ON',    # Relay 1
        'VAL10': 'OFF',  # Relay 2
        'VAL11': 'ON',   # Relay 3
        'VAL12': 'NOR'   # Combined status
    }

@pytest.fixture
def mock_plc_manager():
    """Mock PLC manager for testing"""
    mock_plc = Mock()
    mock_plc.connect.return_value = True
    mock_plc.read_device.return_value = 1024  # Sample raw value
    mock_plc.get_connection_status.return_value = {
        'plc_connected': True,
        'plc_ip': '192.168.3.39',
        'plc_port': 5007,
        'last_reading': datetime.now().isoformat()
    }
    return mock_plc

@pytest.fixture
def sample_dataframe():
    """Sample pandas DataFrame for testing"""
    data = {
        'timestamp': pd.date_range('2025-09-09', periods=100, freq='min'),
        'esp_current': [6.25 + i*0.01 for i in range(100)],
        'esp_voltage': [24.0 + i*0.02 for i in range(100)],
        'esp_rpm': [2750 + i*2 for i in range(100)],
        'plc_motor_temp': [42.5 + i*0.1 for i in range(100)],
        'overall_health_score': [85.0 + i*0.1 for i in range(100)]
    }
    return pd.DataFrame(data)

@pytest.fixture
def mock_database_manager():
    """Mock database manager for testing"""
    mock_db = Mock()
    mock_db.save_sensor_data.return_value = True
    mock_db.get_recent_data.return_value = []
    mock_db.get_system_statistics.return_value = {
        'total_sensor_readings': 1000,
        'current_health_score': 85.5,
        'active_alerts': 2,
        'system_uptime_24h': 98.5
    }
    return mock_db

@pytest.fixture(autouse=True)
def cleanup_temp_files():
    """Automatically cleanup temporary files after each test"""
    yield
    # Cleanup any temporary files created during tests
    temp_files = [f for f in os.listdir('.') if f.startswith('test_') and f.endswith('.db')]
    for temp_file in temp_files:
        try:
            os.remove(temp_file)
        except OSError:
            pass
