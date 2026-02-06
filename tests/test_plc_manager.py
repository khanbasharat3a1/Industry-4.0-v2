"""
PLC Manager Tests
Tests for FX5U PLC communication and data handling.
"""

import pytest
from unittest.mock import MagicMock

class TestPLCManager:
    """Test PLC manager functionality using dependency injection for mocking."""

    @pytest.fixture
    def mock_mc_protocol(self):
        """Provides a MagicMock for the pymcprotocol client."""
        return MagicMock()

    @pytest.fixture
    def plc_manager(self, mock_mc_protocol):
        """Provides an instance of FX5UPLCManager with a mocked client."""
        from hardware.plc_manager import FX5UPLCManager
        # Inject the mock client into the manager
        return FX5UPLCManager(mc_protocol_client=mock_mc_protocol)

    def test_plc_manager_initialization(self, plc_manager, mock_mc_protocol):
        """Test PLC manager initializes correctly."""
        assert plc_manager.name == "FX5U_PLC"
        assert not plc_manager.connected
        assert plc_manager.mc is mock_mc_protocol  # Check that the mock was injected

    def test_plc_connection_success(self, plc_manager, mock_mc_protocol):
        """Test successful PLC connection."""
        mock_mc_protocol.connect.return_value = 0  # Success code

        result = plc_manager.connect()

        assert result is True
        assert plc_manager.connected is True
        mock_mc_protocol.connect.assert_called_with('127.0.0.1', 5007)

    def test_plc_connection_failure(self, plc_manager, mock_mc_protocol):
        """Test PLC connection failure handling."""
        mock_mc_protocol.connect.return_value = 1  # Failure code

        result = plc_manager.connect()

        assert result is False
        assert plc_manager.connected is False

    def test_read_data_success(self, plc_manager, mock_mc_protocol):
        """Test reading and converting data from PLC registers."""
        # Mock the batch read to return a list of values for each call
        mock_mc_protocol.batchread_wordunits.side_effect = [[1000], [2048]]

        plc_manager.connected = True  # Simulate connected state
        data = plc_manager.read_data()

        assert data is not None
        assert data['plc_connected'] is True
        assert data['raw_d100'] == 1000
        assert data['raw_d102'] == 2048
        assert data['plc_motor_temp'] == 106.0
        assert data['plc_motor_voltage'] == 7.3

    def test_read_data_failure_on_read(self, plc_manager, mock_mc_protocol):
        """Test failure during a register read."""
        # Simulate a read failure
        mock_mc_protocol.batchread_wordunits.return_value = None

        plc_manager.connected = True
        data = plc_manager.read_data()

        assert data is not None
        assert not data['plc_connected']
        assert data['error'] == 'Register read failed'

    def test_plc_disconnect(self, plc_manager, mock_mc_protocol):
        """Test PLC disconnection."""
        plc_manager.connected = True

        plc_manager.disconnect()

        assert not plc_manager.connected
        mock_mc_protocol.close.assert_called_once()
