"""
ESP/Arduino Data Handler
Processes incoming data from ESP8266/Arduino via HTTP POST
"""

from typing import Dict, Optional
import logging
from datetime import datetime
from utils.validators import validate_esp_data
from utils.converters import convert_esp_values

logger = logging.getLogger(__name__)

class ESPHandler:
    """Handles ESP/Arduino data reception and processing"""
    
    def __init__(self):
        self.name = "ESP_Handler"
        self.last_data = {}
        self.last_update = None
        
    def process_esp_data(self, raw_data: Dict) -> Optional[Dict]:
        """
        Process incoming ESP data from HTTP POST request
        
        Args:
            raw_data: Raw JSON data from ESP POST request
            
        Returns:
            Processed sensor data dictionary or None if invalid
        """
        try:
            # Validate incoming data
            if not validate_esp_data(raw_data):
                logger.error("Invalid ESP data received")
                return None
            
            # Convert and process ESP data
            esp_data = self._parse_esp_data(raw_data)
            
            if esp_data:
                self.last_data = esp_data
                self.last_update = datetime.now()
                logger.info(f"ESP data processed: Current={esp_data.get('esp_current')}A, "
                           f"Voltage={esp_data.get('esp_voltage')}V, RPM={esp_data.get('esp_rpm')}")
                return esp_data
            
        except Exception as e:
            logger.error(f"Error processing ESP data: {e}")
            
        return None
    
    def _parse_esp_data(self, data: Dict) -> Dict:
        """
        Parse raw ESP data into structured format
        
        Expected format from ESP:
        {
            "TYPE": "ADU_TEXT",
            "VAL1": "current_value",
            "VAL2": "voltage_value", 
            "VAL3": "rpm_value",
            "VAL4": "temp_c",
            "VAL5": "humidity",
            "VAL6": "temp_f",
            "VAL7": "heat_index_c",
            "VAL8": "heat_index_f",
            "VAL9": "relay1_status",
            "VAL10": "relay2_status",
            "VAL11": "relay3_status",
            "VAL12": "combined_status"
        }
        """
        
        esp_data = {
            'esp_current': self._safe_float_convert(data.get('VAL1')),
            'esp_voltage': self._safe_float_convert(data.get('VAL2')),
            'esp_rpm': self._safe_float_convert(data.get('VAL3')),
            'env_temp_c': self._safe_float_convert(data.get('VAL4')),
            'env_humidity': self._safe_float_convert(data.get('VAL5')),
            'env_temp_f': self._safe_float_convert(data.get('VAL6')),
            'heat_index_c': self._safe_float_convert(data.get('VAL7')),
            'heat_index_f': self._safe_float_convert(data.get('VAL8')),
            'relay1_status': self._safe_string_convert(data.get('VAL9'), 'OFF'),
            'relay2_status': self._safe_string_convert(data.get('VAL10'), 'OFF'),
            'relay3_status': self._safe_string_convert(data.get('VAL11'), 'OFF'),
            'combined_status': self._safe_string_convert(data.get('VAL12'), 'NOR'),
            'esp_connected': True,
            'timestamp': datetime.now().isoformat()
        }
        
        return esp_data
    
    def _safe_float_convert(self, value: str) -> Optional[float]:
        """Safely convert string to float"""
        if not value or value == '0' or value == '--':
            return None
        try:
            float_val = float(value)
            return float_val if float_val > 0 else None
        except (ValueError, TypeError):
            return None
    
    def _safe_string_convert(self, value: str, default: str) -> str:
        """Safely convert to string with default"""
        if not value:
            return default
        return str(value).upper()
    
    def get_connection_status(self) -> Dict:
        """Get ESP connection status"""
        if self.last_update:
            time_since_update = (datetime.now() - self.last_update).total_seconds()
            connected = time_since_update < 35  # 5 second buffer on 30s timeout
        else:
            connected = False
            
        return {
            'esp_connected': connected,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'data_available': bool(self.last_data)
        }
    
    def get_last_data(self) -> Dict:
        """Get last processed ESP data"""
        return self.last_data.copy()
