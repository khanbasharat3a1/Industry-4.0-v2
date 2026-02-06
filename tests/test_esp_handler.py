"""
ESP Handler Tests
Tests for ESP8266/Arduino data handling and processing.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

class TestESPHandler:
    """Test ESP data handler functionality"""

    @pytest.fixture
    def esp_handler(self):
        """Provides an instance of ESPHandler."""
        from hardware.esp_handler import ESPHandler
        return ESPHandler()

    def test_process_valid_data(self, esp_handler, sample_esp_data):
        """Test that valid ESP data is processed correctly."""
        processed_data = esp_handler.process_esp_data(sample_esp_data)

        assert processed_data is not None
        assert isinstance(processed_data, dict)
        assert processed_data['esp_current'] == 6.25
        assert processed_data['esp_voltage'] == 24.0
        assert processed_data['esp_rpm'] == 2750.0
        assert processed_data['env_temp_c'] == 42.5
        assert processed_data['relay1_status'] == 'ON'
        assert processed_data['esp_connected'] is True
        assert 'timestamp' in processed_data

    def test_process_invalid_data(self, esp_handler):
        """Test that invalid ESP data is rejected."""
        invalid_data = {'invalid': 'data'}
        processed_data = esp_handler.process_esp_data(invalid_data)
        assert processed_data is None

    def test_process_data_with_missing_values(self, esp_handler):
        """Test processing data where some values are missing or invalid."""
        # Missing VAL3 (rpm) and invalid VAL4 (temp)
        data = {
            'TYPE': 'ADU_TEXT',
            'VAL1': '5.0',
            'VAL2': '23.5',
            'VAL4': 'invalid_temp'
        }
        processed_data = esp_handler.process_esp_data(data)

        assert processed_data is not None
        assert processed_data['esp_current'] == 5.0
        assert processed_data['esp_voltage'] == 23.5
        assert processed_data['esp_rpm'] is None  # Should be None as it was missing
        assert processed_data['env_temp_c'] is None # Should be None as it was invalid
        assert processed_data['relay1_status'] == 'OFF' # Should use default

    def test_get_connection_status(self, esp_handler, sample_esp_data):
        """Test the connection status logic."""
        # Initially, no data received, should be disconnected
        status = esp_handler.get_connection_status()
        assert not status['esp_connected']
        assert status['last_update'] is None

        # Process data, should now be connected
        esp_handler.process_esp_data(sample_esp_data)
        status = esp_handler.get_connection_status()
        assert status['esp_connected']
        assert 'last_update' in status

        # Manually set last_update to an old time to simulate a timeout
        esp_handler.last_update = datetime.now() - timedelta(seconds=100)
        status = esp_handler.get_connection_status()
        assert not status['esp_connected']

    def test_get_last_data(self, esp_handler, sample_esp_data):
        """Test retrieval of the last processed data."""
        assert esp_handler.get_last_data() == {} # Should be empty initially

        processed = esp_handler.process_esp_data(sample_esp_data)
        last_data = esp_handler.get_last_data()

        assert last_data is not None
        assert last_data['esp_current'] == processed['esp_current']
