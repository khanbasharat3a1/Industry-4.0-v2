"""
Test Package for AI Motor Monitoring System

This package contains all automated tests for the motor monitoring system,
including unit tests, integration tests, and API endpoint tests.
"""

# Test configuration constants
TEST_DATABASE_URL = "sqlite:///:memory:"
TEST_PLC_IP = "127.0.0.1" 
TEST_PLC_PORT = 5007
TEST_ESP_DATA_SAMPLE = {
    'TYPE': 'ADU_TEXT',
    'VAL1': '6.25',  # Current
    'VAL2': '24.0',  # Voltage
    'VAL3': '2750',  # RPM
    'VAL4': '42.5',  # Temperature
    'VAL5': '45.8',  # Humidity
    'VAL9': 'ON',    # Relay 1
    'VAL10': 'OFF',  # Relay 2
    'VAL11': 'ON'    # Relay 3
}
