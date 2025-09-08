"""
FX5U PLC Manager
Handles communication with Mitsubishi FX5U PLC via MC Protocol
"""

from typing import Dict, Optional
import logging
import pymcprotocol
from datetime import datetime
from hardware.base_hardware import BaseHardware
from config.settings import config

logger = logging.getLogger(__name__)

class FX5UPLCManager(BaseHardware):
    """Manages FX5U PLC communication and data conversion"""
    
    def __init__(self):
        super().__init__("FX5U_PLC")
        self.mc = pymcprotocol.Type3E()
        self.last_successful_read = None
        
    def connect(self) -> bool:
        """Connect to FX5U PLC"""
        try:
            if self.mc.connect(config.plc.ip, config.plc.port):
                self.connected = True
                self.log_info(f"Connected successfully to {config.plc.ip}:{config.plc.port}")
                return True
            else:
                self.connected = False
                self.log_error("Failed to establish connection")
                return False
        except Exception as e:
            self.connected = False
            self.log_error(f"Connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from FX5U PLC"""
        try:
            if self.connected and self.mc:
                self.mc.close()
                self.connected = False
                self.log_info("Disconnected successfully")
        except Exception as e:
            self.log_error(f"Error during disconnect: {e}")
    
    def read_data(self) -> Dict:
        """Read and convert data from FX5U PLC registers"""
        if not self.connected:
            if not self.connect():
                return {'plc_connected': False, 'error': 'Connection failed'}
        
        try:
            # Read raw values from FX5U registers
            raw_d100 = self._read_register("D100")  # Voltage register
            raw_d102 = self._read_register("D102")  # Temperature register
            
            if raw_d100 is None or raw_d102 is None:
                self.log_error("Failed to read PLC registers")
                return {'plc_connected': False, 'error': 'Register read failed'}
            
            # Convert raw values to engineering units
            motor_voltage = self.convert_voltage(raw_d100)
            motor_temp = self.convert_temperature(raw_d102)
            
            # Prepare data dictionary
            plc_data = {
                'plc_motor_temp': motor_temp,
                'plc_motor_voltage': motor_voltage,
                'plc_connected': True,
                'timestamp': datetime.now().isoformat(),
                # Debug information
                'raw_d100': raw_d100,
                'raw_d102': raw_d102
            }
            
            self.last_data = plc_data
            self.last_successful_read = datetime.now()
            
            self.log_info(f"Data read: D100({raw_d100}) -> {motor_voltage}V, "
                         f"D102({raw_d102}) -> {motor_temp}°C")
            
            return plc_data
            
        except Exception as e:
            self.log_error(f"Error reading data: {e}")
            self.connected = False
            return {'plc_connected': False, 'error': str(e)}
    
    def _read_register(self, register: str) -> Optional[int]:
        """Read a single register from PLC"""
        try:
            value = self.mc.batchread_wordunits(headdevice=register, readsize=1)
            return int(value) if value is not None else None
        except Exception as e:
            self.log_error(f"Failed to read register {register}: {e}")
            return None
    
    def convert_voltage(self, raw_value: int) -> float:
        """
        Convert D100 raw value to actual voltage
        For 24V system: assumes raw value represents voltage measurement
        
        Args:
            raw_value: Raw register value from D100
            
        Returns:
            Converted voltage value in Volts
        """
        if raw_value <= 0:
            return 0.0
        
        # Scale raw value to voltage range
        # Assuming 4095 (12-bit) represents ~30V full scale for 24V system
        voltage = (raw_value / 4095.0) * 30.0
        
        # Apply bounds checking
        voltage = max(0.0, min(30.0, voltage))
        
        return round(voltage, 1)
    
    def convert_temperature(self, raw_value: int) -> float:
        """
        Convert D102 raw value to actual temperature
        Using provided formula: Temperature (°C) = 0.05175 × Raw Value
        
        Args:
            raw_value: Raw register value from D102
            
        Returns:
            Converted temperature value in Celsius
        """
        if raw_value <= 0:
            return 0.0
        
        # Apply the provided conversion formula
        temperature = 0.05175 * raw_value
        
        # Apply reasonable bounds checking (0-150°C)
        temperature = max(0.0, min(150.0, temperature))
        
        return round(temperature, 1)
    
    def write_register(self, register: str, value: int) -> bool:
        """
        Write value to PLC register
        
        Args:
            register: Register name (e.g., "D200")
            value: Value to write
            
        Returns:
            True if successful, False otherwise
        """
        if not self.connected:
            self.log_error("Cannot write - PLC not connected")
            return False
        
        try:
            self.mc.batchwrite_wordunits(headdevice=register, values=[value])
            self.log_info(f"Successfully wrote {value} to {register}")
            return True
        except Exception as e:
            self.log_error(f"Failed to write to {register}: {e}")
            return False
    
    def get_connection_status(self) -> Dict:
        """Get detailed PLC connection status"""
        if self.last_successful_read:
            time_since_read = (datetime.now() - self.last_successful_read).total_seconds()
            healthy = time_since_read < config.connection.plc_timeout
        else:
            healthy = False
        
        return {
            'plc_connected': self.connected,
            'last_successful_read': self.last_successful_read.isoformat() if self.last_successful_read else None,
            'connection_healthy': healthy,
            'plc_ip': config.plc.ip,
            'plc_port': config.plc.port
        }
    
    def test_connection(self) -> Dict:
        """Test PLC connection and return diagnostic information"""
        result = {
            'connection_test': False,
            'register_test': False,
            'conversion_test': False,
            'error_messages': []
        }
        
        try:
            # Test basic connection
            if self.connect():
                result['connection_test'] = True
                
                # Test register reading
                test_d100 = self._read_register("D100")
                test_d102 = self._read_register("D102")
                
                if test_d100 is not None and test_d102 is not None:
                    result['register_test'] = True
                    
                    # Test conversions
                    voltage = self.convert_voltage(test_d100)
                    temperature = self.convert_temperature(test_d102)
                    
                    if 0 <= voltage <= 30 and 0 <= temperature <= 150:
                        result['conversion_test'] = True
                        result['test_values'] = {
                            'raw_d100': test_d100,
                            'raw_d102': test_d102,
                            'converted_voltage': voltage,
                            'converted_temperature': temperature
                        }
                    else:
                        result['error_messages'].append("Converted values out of expected range")
                else:
                    result['error_messages'].append("Failed to read test registers")
            else:
                result['error_messages'].append("Failed to establish connection")
                
        except Exception as e:
            result['error_messages'].append(f"Test exception: {e}")
        
        return result
