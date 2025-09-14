"""
Data Processor Service
Handles data processing, validation, and orchestrates storage via the DatabaseManager.
"""

import logging
from typing import Dict, Any

from database.manager import DatabaseManager
from hardware.esp_handler import ESPHandler
from hardware.plc_manager import FX5UPLCManager as PLCManager

logger = logging.getLogger(__name__)

class DataProcessor:
    """
    Validates incoming sensor data and uses the DatabaseManager to process and store it.
    This class acts as a bridge between the API routes and the core data services.
    """

    def __init__(self, socketio=None):
        self.logger = logging.getLogger(__name__)
        self.db_manager = DatabaseManager()
        self.esp_handler = ESPHandler()
        self.plc_manager = PLCManager()
        self.socketio = socketio
        
        # In-memory store for the latest data from each source
        self.latest_data = {
            "esp": {},
            "plc": {}
        }
        
        self.logger.info("DataProcessor initialized, using DatabaseManager for all DB operations.")

    def set_socketio(self, socketio):
        """Allows setting the SocketIO instance after initialization."""
        self.socketio = socketio

    def process_and_store_data(self, raw_data: Dict[str, Any], source: str) -> bool:
        """
        Processes raw data from a source ('esp' or 'plc') and stores it.

        Args:
            raw_data: The raw data dictionary from the device.
            source: The source of the data, either 'esp' or 'plc'.

        Returns:
            True if processing and storage were successful, False otherwise.
        """
        try:
            # 1. Process the raw data using the appropriate handler
            processed_data = None
            if source == 'esp':
                processed_data = self.esp_handler.process_esp_data(raw_data)
                if processed_data:
                    self.latest_data['esp'] = processed_data
            elif source == 'plc':
                # The PLC data from the simulator is already processed.
                # The PLCManager is for connecting to real hardware, not processing this dict.
                processed_data = raw_data
                if processed_data:
                    self.latest_data['plc'] = processed_data
            else:
                self.logger.error(f"Unknown data source for processing: {source}")
                return False

            if not processed_data:
                self.logger.warning(f"Failed to process data from source: {source}")
                return False

            # 2. Combine data from all sources for a complete picture
            combined_data = self.get_latest_combined_data()
            
            # 3. Get connection status
            # This should be handled by the ConnectionMonitor, but we can infer it here for now.
            connection_status = {
                'esp_connected': bool(self.latest_data['esp']),
                'plc_connected': bool(self.latest_data['plc'])
            }
            
            # 4. Save the combined data using the DatabaseManager
            # The DatabaseManager will perform health analysis before saving.
            success = self.db_manager.save_sensor_data(combined_data, connection_status)

            if success:
                self.logger.info(f"Successfully processed and stored data from {source}.")
                # 5. Emit real-time updates via WebSocket
                if self.socketio:
                    # We need the full health data which is calculated inside save_sensor_data.
                    # For now, we'll get the latest record from the DB. A better approach
                    # would be for save_sensor_data to return the calculated data.
                    latest_record = self.db_manager.get_recent_data_df(limit=1)
                    if not latest_record.empty:
                        self.socketio.emit('data_update', latest_record.to_dict('records')[0])
            else:
                self.logger.error(f"Failed to save sensor data for source: {source}")

            return success

        except Exception as e:
            self.logger.error(f"Error in process_and_store_data for source {source}: {e}", exc_info=True)
            return False

    def get_latest_combined_data(self) -> Dict[str, Any]:
        """
        Merges the latest data from ESP and PLC into a single dictionary.
        """
        return {**self.latest_data['esp'], **self.latest_data['plc']}

    def get_latest_health_data(self) -> Dict[str, Any]:
        """
        Retrieves the most recent health data from the database.
        """
        latest_record = self.db_manager.get_recent_data_df(limit=1)
        if not latest_record.empty:
            health_columns = [
                'overall_health_score', 'electrical_health', 'thermal_health',
                'mechanical_health', 'predictive_health', 'efficiency_score'
            ]
            return latest_record[health_columns].to_dict('records')[0]
        return {}

    def get_system_status(self):
        # This functionality is now better handled by the ConnectionMonitor and DatabaseManager
        # and can be deprecated from here.
        self.logger.warning("get_system_status in DataProcessor is deprecated.")
        return self.db_manager.get_system_statistics()
