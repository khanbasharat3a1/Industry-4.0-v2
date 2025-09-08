"""
Data Validation Utilities
Input validation functions for sensor data and API requests
"""

import logging
from typing import Dict, Any, Optional
import re
from datetime import datetime

logger = logging.getLogger(__name__)

def validate_esp_data(data: Dict) -> bool:
    """
    Validate ESP/Arduino sensor data format
    
    Args:
        data: Raw data dictionary from ESP
        
    Returns:
        True if data is valid, False otherwise
    """
    try:
        if not isinstance(data, dict):
            logger.error("ESP data must be a dictionary")
            return False
        
        # Check for required TYPE field
        if not data.get('TYPE'):
            logger.error("ESP data missing TYPE field")
            return False
        
        # Validate TYPE field
        valid_types = ['ADU_TEXT', 'SENSOR_DATA', 'STATUS_UPDATE']
        if data['TYPE'] not in valid_types:
            logger.warning(f"Unknown ESP data type: {data['TYPE']}")
            # Don't fail validation for unknown types, just warn
        
        # Check for at least some value fields
        value_fields = [f'VAL{i}' for i in range(1, 13)]
        has_values = any(data.get(field) for field in value_fields)
        
        if not has_values:
            logger.error("ESP data contains no value fields")
            return False
        
        # Validate individual value fields if present
        for field in value_fields:
            if field in data:
                if not validate_sensor_value(data[field], field):
                    logger.warning(f"Invalid value in field {field}: {data[field]}")
                    # Don't fail validation, just warn about individual bad values
        
        return True
        
    except Exception as e:
        logger.error(f"Error validating ESP data: {e}")
        return False

def validate_sensor_value(value: Any, field_name: str = '') -> bool:
    """
    Validate individual sensor value
    
    Args:
        value: Sensor value to validate
        field_name: Name of the field being validated
        
    Returns:
        True if value is valid, False otherwise
    """
    try:
        if value is None:
            return True  # Null values are acceptable
        
        # Convert to string for validation
        str_value = str(value).strip()
        
        # Empty or placeholder values
        if str_value in ['', '--', 'N/A', 'NULL', 'null']:
            return True
        
        # Check for numeric values (for sensor readings)
        if field_name.startswith('VAL') and field_name not in ['VAL9', 'VAL10', 'VAL11', 'VAL12']:
            # VAL1-8 should be numeric, VAL9-12 are typically status strings
            try:
                float_val = float(str_value)
                # Check for reasonable ranges
                if abs(float_val) > 100000:  # Extremely large values
                    logger.warning(f"Unusually large value for {field_name}: {float_val}")
                return True
            except ValueError:
                logger.error(f"Non-numeric value for {field_name}: {str_value}")
                return False
        
        # Check for status/relay values (should be ON/OFF or similar)
        if field_name in ['VAL9', 'VAL10', 'VAL11', 'VAL12']:
            valid_status = ['ON', 'OFF', 'NOR', 'ALM', 'BUZ', '1', '0', 'TRUE', 'FALSE']
            if str_value.upper() not in valid_status:
                logger.warning(f"Unknown status value for {field_name}: {str_value}")
                # Don't fail validation for unknown status values
        
        return True
        
    except Exception as e:
        logger.error(f"Error validating sensor value {field_name}: {e}")
        return False

def validate_api_request(data: Dict, required_fields: list = None, optional_fields: list = None) -> tuple[bool, str]:
    """
    Validate API request data
    
    Args:
        data: Request data dictionary
        required_fields: List of required field names
        optional_fields: List of optional field names
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        if not isinstance(data, dict):
            return False, "Request data must be a JSON object"
        
        # Check required fields
        if required_fields:
            for field in required_fields:
                if field not in data:
                    return False, f"Missing required field: {field}"
                
                if data[field] is None or str(data[field]).strip() == '':
                    return False, f"Field {field} cannot be empty"
        
        # Check for unexpected fields
        if required_fields or optional_fields:
            allowed_fields = set(required_fields or []) | set(optional_fields or [])
            for field in data.keys():
                if field not in allowed_fields:
                    logger.warning(f"Unexpected field in request: {field}")
        
        return True, "Valid"
        
    except Exception as e:
        return False, f"Validation error: {e}"

def validate_datetime_string(date_string: str) -> bool:
    """
    Validate datetime string format
    
    Args:
        date_string: Date/time string to validate
        
    Returns:
        True if valid datetime format, False otherwise
    """
    try:
        if not date_string:
            return False
        
        # Try common datetime formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S.%fZ'
        ]
        
        for fmt in formats:
            try:
                datetime.strptime(date_string, fmt)
                return True
            except ValueError:
                continue
        
        # Try ISO format parsing
        try:
            datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            return True
        except ValueError:
            pass
        
        return False
        
    except Exception as e:
        logger.error(f"Error validating datetime string: {e}")
        return False

def validate_ip_address(ip_string: str) -> bool:
    """
    Validate IP address format
    
    Args:
        ip_string: IP address string to validate
        
    Returns:
        True if valid IP address, False otherwise
    """
    try:
        import ipaddress
        ipaddress.ip_address(ip_string)
        return True
    except ValueError:
        return False

def validate_port_number(port: Any) -> bool:
    """
    Validate port number
    
    Args:
        port: Port number to validate
        
    Returns:
        True if valid port, False otherwise
    """
    try:
        port_int = int(port)
        return 1 <= port_int <= 65535
    except (ValueError, TypeError):
        return False

def sanitize_string(input_string: str, max_length: int = 255) -> str:
    """
    Sanitize string input for database storage
    
    Args:
        input_string: String to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    try:
        if not input_string:
            return ""
        
        # Convert to string and strip whitespace
        sanitized = str(input_string).strip()
        
        # Remove control characters
        sanitized = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', sanitized)
        
        # Truncate to maximum length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized
        
    except Exception as e:
        logger.error(f"Error sanitizing string: {e}")
        return ""

def validate_health_score(score: Any) -> bool:
    """
    Validate health score value
    
    Args:
        score: Health score to validate
        
    Returns:
        True if valid score (0-100), False otherwise
    """
    try:
        score_float = float(score)
        return 0.0 <= score_float <= 100.0
    except (ValueError, TypeError):
        return False
