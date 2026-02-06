"""
Pytest Configuration and Fixtures
Contains shared fixtures and configuration for all tests in the motor monitoring system.
"""

import pytest
import os
from unittest.mock import Mock
from flask import Flask
from datetime import datetime
import pandas as pd

# Set a dedicated test environment to prevent accidental use of production resources
os.environ['FLASK_ENV'] = 'testing'

@pytest.fixture(scope='session')
def monkeypatch_session():
    """A session-scoped monkeypatch fixture."""
    from _pytest.monkeypatch import MonkeyPatch
    mp = MonkeyPatch()
    yield mp
    mp.undo()

@pytest.fixture(scope='session')
def app(monkeypatch_session):
    """
    Creates and configures a new Flask application instance for each test session.
    This fixture uses the application factory `create_app` and `monkeypatch` to
    ensure tests run against the real application with a controlled configuration.
    """
    # Use monkeypatch to set test-specific config values before the app is created.
    monkeypatch_session.setattr("config.settings.config.database.url", "sqlite:///:memory:")
    monkeypatch_session.setattr("config.settings.config.flask.debug", False)
    monkeypatch_session.setattr("config.settings.config.plc.ip", "127.0.0.1")
    monkeypatch_session.setattr("config.settings.config.plc.port", 5007)

    from core.app_factory import create_app
    app, socketio = create_app()

    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-secret-key",
    })

    with app.app_context():
        from database.manager import DatabaseManager
        # This ensures the in-memory database is created with the correct schema
        db_manager = DatabaseManager()

    yield app

@pytest.fixture
def client(app):
    """Provides a test client for the application, allowing to send HTTP requests."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Provides a CLI runner for testing Flask CLI commands."""
    return app.test_cli_runner()

# --- Mock Fixtures ---

@pytest.fixture
def mock_plc_manager():
    """Mocks the PLC manager to isolate tests from hardware dependencies."""
    mock_plc = Mock()
    mock_plc.connect.return_value = True
    mock_plc.read_device.return_value = 1024
    mock_plc.get_connection_status.return_value = {'plc_connected': True}
    return mock_plc

@pytest.fixture
def mock_database_manager():
    """Mocks the DatabaseManager to isolate services from the database."""
    mock_db = Mock()
    mock_db.save_sensor_data.return_value = True
    mock_db.get_recent_data_df.return_value = pd.DataFrame()
    mock_db.get_system_statistics.return_value = {'total_sensor_readings': 0}
    return mock_db

# --- Data Fixtures ---

@pytest.fixture
def sample_sensor_data():
    """Provides a sample dictionary of sensor data for testing."""
    return {
        'esp_current': 6.25,
        'esp_voltage': 24.1,
        'esp_rpm': 2750,
        'plc_motor_temp': 42.5,
        'env_temp_c': 24.8,
        'env_humidity': 45.2,
    }

@pytest.fixture
def sample_esp_data():
    """Provides a complete sample dictionary mimicking a POST from an ESP device."""
    return {
        'TYPE': 'ADU_TEXT',
        'VAL1': '6.25',
        'VAL2': '24.0',
        'VAL3': '2750',
        'VAL4': '42.5',
        'VAL5': '45.8',
        'VAL6': '108.5', # Temp F for 42.5 C
        'VAL7': '43.0',  # Heat Index C
        'VAL8': '109.4', # Heat Index F
        'VAL9': 'ON',
        'VAL10': 'OFF',
        'VAL11': 'ON',
        'VAL12': 'NOR'
    }

@pytest.fixture
def sample_dataframe():
    """Provides a sample pandas DataFrame for testing functions that process data over time."""
    data = {
        'timestamp': pd.to_datetime(pd.date_range('2025-09-09', periods=100, freq='T')),
        'esp_current': [6.25 + i * 0.01 for i in range(100)],
        'esp_voltage': [24.0 - i * 0.01 for i in range(100)],
        'esp_rpm': [2750 - i for i in range(100)],
        'plc_motor_temp': [42.5 + i * 0.1 for i in range(100)],
        'overall_health_score': [85.0 - i * 0.2 for i in range(100)],
    }
    return pd.DataFrame(data)
