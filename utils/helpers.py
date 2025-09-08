"""
Helper Utilities
General utility functions for common operations
"""

import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import logging
import os
import psutil

logger = logging.getLogger(__name__)

def format_timestamp(timestamp: Any, format_string: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    Format timestamp for display
    
    Args:
        timestamp: Timestamp to format
        format_string: Format string
        
    Returns:
        Formatted timestamp string
    """
    try:
        if timestamp is None:
            return "N/A"
        
        if isinstance(timestamp, str):
            # Try to parse ISO format
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        elif isinstance(timestamp, datetime):
            dt = timestamp
        else:
            return str(timestamp)
        
        return dt.strftime(format_string)
        
    except Exception as e:
        logger.error(f"Error formatting timestamp: {e}")
        return str(timestamp) if timestamp else "N/A"

def calculate_uptime(start_time: datetime, end_time: datetime = None) -> Dict:
    """
    Calculate uptime between two timestamps
    
    Args:
        start_time: Start timestamp
        end_time: End timestamp (defaults to now)
        
    Returns:
        Dictionary with uptime information
    """
    try:
        if end_time is None:
            end_time = datetime.now()
        
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        if isinstance(end_time, str):
            end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        
        uptime_delta = end_time - start_time
        
        days = uptime_delta.days
        hours, remainder = divmod(uptime_delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        total_seconds = uptime_delta.total_seconds()
        total_hours = total_seconds / 3600
        
        return {
            'total_seconds': total_seconds,
            'total_hours': round(total_hours, 2),
            'days': days,
            'hours': hours,
            'minutes': minutes,
            'seconds': seconds,
            'formatted': f"{days}d {hours}h {minutes}m {seconds}s",
            'short_format': f"{days}d {hours}h {minutes}m"
        }
        
    except Exception as e:
        logger.error(f"Error calculating uptime: {e}")
        return {
            'total_seconds': 0,
            'total_hours': 0,
            'days': 0,
            'hours': 0,
            'minutes': 0,
            'seconds': 0,
            'formatted': "N/A",
            'short_format': "N/A"
        }

def generate_report_id(prefix: str = "RPT") -> str:
    """
    Generate unique report ID
    
    Args:
        prefix: ID prefix
        
    Returns:
        Unique report ID
    """
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_part = str(uuid.uuid4())[:8].upper()
        return f"{prefix}_{timestamp}_{unique_part}"
        
    except Exception as e:
        logger.error(f"Error generating report ID: {e}")
        return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def calculate_hash(data: Any) -> str:
    """
    Calculate MD5 hash of data
    
    Args:
        data: Data to hash
        
    Returns:
        MD5 hash string
    """
    try:
        if isinstance(data, dict):
            # Sort dictionary for consistent hashing
            data_string = str(sorted(data.items()))
        else:
            data_string = str(data)
        
        return hashlib.md5(data_string.encode('utf-8')).hexdigest()
        
    except Exception as e:
        logger.error(f"Error calculating hash: {e}")
        return "unknown"

def get_system_info() -> Dict:
    """
    Get system information
    
    Returns:
        Dictionary with system information
    """
    try:
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage_percent': psutil.disk_usage('/').percent,
            'boot_time': datetime.fromtimestamp(psutil.boot_time()).isoformat(),
            'process_count': len(psutil.pids()),
            'platform': os.name,
            'python_version': f"{psutil.PYTHON_MAJOR}.{psutil.PYTHON_MINOR}",
            'collected_at': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        return {
            'error': str(e),
            'collected_at': datetime.now().isoformat()
        }

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    try:
        if size_bytes == 0:
            return "0B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"
        
    except Exception as e:
        logger.error(f"Error formatting file size: {e}")
        return f"{size_bytes}B"

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers
    
    Args:
        numerator: Numerator
        denominator: Denominator
        default: Default value if division fails
        
    Returns:
        Division result or default
    """
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except (TypeError, ValueError):
        return default

def clamp_value(value: float, min_val: float, max_val: float) -> float:
    """
    Clamp value between min and max
    
    Args:
        value: Value to clamp
        min_val: Minimum value
        max_val: Maximum value
        
    Returns:
        Clamped value
    """
    try:
        return max(min_val, min(max_val, value))
    except (TypeError, ValueError):
        return min_val

def create_backup_filename(original_path: str) -> str:
    """
    Create backup filename with timestamp
    
    Args:
        original_path: Original file path
        
    Returns:
        Backup filename
    """
    try:
        directory = os.path.dirname(original_path)
        filename = os.path.basename(original_path)
        name, ext = os.path.splitext(filename)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"{name}_backup_{timestamp}{ext}"
        
        return os.path.join(directory, backup_filename)
        
    except Exception as e:
        logger.error(f"Error creating backup filename: {e}")
        return f"{original_path}.backup"

def ensure_directory_exists(directory_path: str) -> bool:
    """
    Ensure directory exists, create if necessary
    
    Args:
        directory_path: Directory path to check/create
        
    Returns:
        True if directory exists or was created successfully
    """
    try:
        os.makedirs(directory_path, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error creating directory {directory_path}: {e}")
        return False

def retry_operation(operation, max_retries: int = 3, delay: float = 1.0):
    """
    Retry operation with exponential backoff
    
    Args:
        operation: Function to retry
        max_retries: Maximum number of retries
        delay: Initial delay between retries
        
    Returns:
        Operation result or raises last exception
    """
    import time
    
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return operation()
        except Exception as e:
            last_exception = e
            
            if attempt < max_retries:
                wait_time = delay * (2 ** attempt)  # Exponential backoff
                logger.warning(f"Operation failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
            else:
                logger.error(f"Operation failed after {max_retries + 1} attempts: {e}")
                raise last_exception

def format_number(number: Any, decimals: int = 2) -> str:
    """
    Format number for display with proper decimal places
    
    Args:
        number: Number to format
        decimals: Number of decimal places
        
    Returns:
        Formatted number string
    """
    try:
        if number is None:
            return "N/A"
        
        float_number = float(number)
        return f"{float_number:.{decimals}f}"
        
    except (ValueError, TypeError):
        return str(number) if number is not None else "N/A"

def merge_dictionaries(*dicts: Dict) -> Dict:
    """
    Merge multiple dictionaries, later ones override earlier ones
    
    Args:
        *dicts: Dictionaries to merge
        
    Returns:
        Merged dictionary
    """
    result = {}
    for d in dicts:
        if isinstance(d, dict):
            result.update(d)
    return result
