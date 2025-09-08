"""
Data Conversion Utilities
Functions for converting between different data formats and units
"""

import logging
from typing import Any, Optional, Dict, Union
from datetime import datetime
import json

logger = logging.getLogger(__name__)

def safe_float_convert(value: Any, default: float = None) -> Optional[float]:
    """
    Safely convert value to float
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Float value or default
    """
    try:
        if value is None or value == '' or value == '--':
            return default
        
        # Handle string representations
        if isinstance(value, str):
            value = value.strip()
            if value.lower() in ['null', 'none', 'n/a']:
                return default
        
        float_val = float(value)
        
        # Check for invalid float values
        if not (-1e10 <= float_val <= 1e10):  # Reasonable range check
            logger.warning(f"Float value out of reasonable range: {float_val}")
            return default
        
        return float_val
        
    except (ValueError, TypeError, OverflowError) as e:
        logger.debug(f"Float conversion failed for '{value}': {e}")
        return default

def safe_int_convert(value: Any, default: int = None) -> Optional[int]:
    """
    Safely convert value to integer
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
        
    Returns:
        Integer value or default
    """
    try:
        if value is None or value == '' or value == '--':
            return default
        
        # Handle string representations
        if isinstance(value, str):
            value = value.strip()
            if value.lower() in ['null', 'none', 'n/a']:
                return default
        
        # First convert to float to handle decimal strings, then to int
        int_val = int(float(value))
        
        return int_val
        
    except (ValueError, TypeError, OverflowError) as e:
        logger.debug(f"Integer conversion failed for '{value}': {e}")
        return default

def convert_esp_values(raw_data: Dict) -> Dict:
    """
    Convert ESP raw values to appropriate data types
    
    Args:
        raw_data: Raw ESP data dictionary
        
    Returns:
        Dictionary with converted values
    """
    try:
        converted = {}
        
        # Convert numeric sensor values
        numeric_fields = {
            'VAL1': 'esp_current',      # Current (A)
            'VAL2': 'esp_voltage',      # Voltage (V) 
            'VAL3': 'esp_rpm',          # RPM
            'VAL4': 'env_temp_c',       # Temperature (C)
            'VAL5': 'env_humidity',     # Humidity (%)
            'VAL6': 'env_temp_f',       # Temperature (F)
            'VAL7': 'heat_index_c',     # Heat Index (C)
            'VAL8': 'heat_index_f'      # Heat Index (F)
        }
        
        for esp_field, output_field in numeric_fields.items():
            if esp_field in raw_data:
                converted[output_field] = safe_float_convert(raw_data[esp_field])
        
        # Convert status/relay values
        status_fields = {
            'VAL9': 'relay1_status',
            'VAL10': 'relay2_status', 
            'VAL11': 'relay3_status',
            'VAL12': 'combined_status'
        }
        
        for esp_field, output_field in status_fields.items():
            if esp_field in raw_data:
                converted[output_field] = convert_status_value(raw_data[esp_field])
        
        # Add metadata
        converted['esp_connected'] = True
        converted['timestamp'] = datetime.now().isoformat()
        
        return converted
        
    except Exception as e:
        logger.error(f"Error converting ESP values: {e}")
        return {}

def convert_status_value(value: Any) -> str:
    """
    Convert status value to standardized format
    
    Args:
        value: Status value to convert
        
    Returns:
        Standardized status string
    """
    try:
        if value is None:
            return 'UNKNOWN'
        
        str_val = str(value).strip().upper()
        
        # Map various representations to standard values
        if str_val in ['1', 'TRUE', 'ON', 'ACTIVE', 'HIGH']:
            return 'ON'
        elif str_val in ['0', 'FALSE', 'OFF', 'INACTIVE', 'LOW']:
            return 'OFF'
        elif str_val in ['NOR', 'NORMAL']:
            return 'NOR'
        elif str_val in ['ALM', 'ALARM']:
            return 'ALM'
        elif str_val in ['BUZ', 'BUZZER']:
            return 'BUZ'
        else:
            return str_val if str_val else 'UNKNOWN'
            
    except Exception as e:
        logger.error(f"Error converting status value '{value}': {e}")
        return 'UNKNOWN'

def celsius_to_fahrenheit(celsius: float) -> float:
    """Convert Celsius to Fahrenheit"""
    try:
        return (celsius * 9.0 / 5.0) + 32.0
    except (TypeError, ValueError):
        return None

def fahrenheit_to_celsius(fahrenheit: float) -> float:
    """Convert Fahrenheit to Celsius"""
    try:
        return (fahrenheit - 32.0) * 5.0 / 9.0
    except (TypeError, ValueError):
        return None

def calculate_power(voltage: float, current: float) -> Optional[float]:
    """
    Calculate power in watts
    
    Args:
        voltage: Voltage in volts
        current: Current in amperes
        
    Returns:
        Power in watts or None if calculation fails
    """
    try:
        if voltage is None or current is None:
            return None
        
        if voltage <= 0 or current < 0:
            return None
        
        power = voltage * current
        return round(power, 2)
        
    except (TypeError, ValueError) as e:
        logger.error(f"Error calculating power: {e}")
        return None

def format_sensor_value(value: Any, unit: str = '', precision: int = 1) -> str:
    """
    Format sensor value for display
    
    Args:
        value: Sensor value
        unit: Unit string
        precision: Decimal precision
        
    Returns:
        Formatted string
    """
    try:
        if value is None:
            return f"--{unit}"
        
        if isinstance(value, (int, float)):
            formatted = f"{value:.{precision}f}{unit}"
            return formatted
        else:
            return f"{value}{unit}"
            
    except Exception as e:
        logger.error(f"Error formatting sensor value: {e}")
        return f"--{unit}"

def convert_timestamp_format(timestamp: Any, target_format: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    Convert timestamp to specified format
    
    Args:
        timestamp: Timestamp to convert
        target_format: Target format string
        
    Returns:
        Formatted timestamp string
    """
    try:
        if timestamp is None:
            return ""
        
        # Handle different input types
        if isinstance(timestamp, str):
            # Try to parse ISO format first
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError:
                # Try other common formats
                dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        elif isinstance(timestamp, datetime):
            dt = timestamp
        else:
            return str(timestamp)
        
        return dt.strftime(target_format)
        
    except Exception as e:
        logger.error(f"Error converting timestamp format: {e}")
        return str(timestamp) if timestamp else ""

def json_serialize_data(data: Dict) -> str:
    """
    Serialize data to JSON with proper handling of special types
    
    Args:
        data: Data dictionary to serialize
        
    Returns:
        JSON string
    """
    try:
        def json_serializer(obj):
            """Custom JSON serializer for special types"""
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif hasattr(obj, '__dict__'):
                return obj.__dict__
            else:
                return str(obj)
        
        return json.dumps(data, default=json_serializer, indent=2)
        
    except Exception as e:
        logger.error(f"Error serializing data to JSON: {e}")
        return "{}"

def parse_json_data(json_string: str) -> Dict:
    """
    Parse JSON string with error handling
    
    Args:
        json_string: JSON string to parse
        
    Returns:
        Parsed dictionary or empty dict on error
    """
    try:
        if not json_string:
            return {}
        
        return json.loads(json_string)
        
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON: {e}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error parsing JSON: {e}")
        return {}

def normalize_health_score(score: Any) -> float:
    """
    Normalize health score to 0-100 range
    
    Args:
        score: Health score value
        
    Returns:
        Normalized score (0-100)
    """
    try:
        if score is None:
            return 0.0
        
        score_float = float(score)
        
        # Clamp to 0-100 range
        normalized = max(0.0, min(100.0, score_float))
        
        return round(normalized, 1)
        
    except (ValueError, TypeError):
        return 0.0

def convert_efficiency_percentage(actual: float, optimal: float) -> float:
    """
    Convert actual vs optimal values to efficiency percentage
    
    Args:
        actual: Actual measured value
        optimal: Optimal target value
        
    Returns:
        Efficiency percentage (0-100)
    """
    try:
        if actual is None or optimal is None or optimal <= 0:
            return 0.0
        
        if actual <= 0:
            return 0.0
        
        # Calculate efficiency as percentage
        if actual <= optimal:
            # For values that should be at or below optimal (like temperature)
            efficiency = (actual / optimal) * 100
        else:
            # For values that exceed optimal, efficiency decreases
            efficiency = (optimal / actual) * 100
        
        return round(max(0.0, min(100.0, efficiency)), 1)
        
    except Exception as e:
        logger.error(f"Error calculating efficiency: {e}")
        return 0.0
