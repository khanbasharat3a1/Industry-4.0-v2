"""
Data Processor Service
Handles data processing, validation, and storage for sensor readings
"""

import os
import logging
import sqlite3
from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, Any, Optional

class DataProcessor:
    """
    Handles all data processing operations for sensor data
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db_path = os.path.join('database', 'sensor_history.db')
        self.data_lock = Lock()
        self.socketio = None
        
        # Data validation thresholds
        self.validation_ranges = {
            'esp_current': (0, 20),      # 0-20 Amps
            'esp_voltage': (0, 30),      # 0-30 Volts
            'esp_rpm': (0, 4000),        # 0-4000 RPM
            'env_temp_c': (-20, 80),     # -20 to 80°C
            'env_humidity': (0, 100),    # 0-100%
            'plc_motor_temp': (0, 120),  # 0-120°C
            'plc_motor_voltage': (0, 30), # 0-30 Volts
            'plc_motor_current': (0, 25), # 0-25 Amps
            'plc_motor_rpm': (0, 4000)   # 0-4000 RPM
        }
        
        self.logger.info("Data processor initialized")
    
    def set_socketio(self, socketio):
        """Set SocketIO instance for real-time updates"""
        self.socketio = socketio
        self.logger.info("SocketIO instance configured")
    
    def validate_sensor_data(self, data: Dict[str, Any], data_type: str) -> Dict[str, Any]:
        """
        Validate and clean sensor data
        
        Args:
            data: Raw sensor data dictionary
            data_type: 'esp' or 'plc'
            
        Returns:
            Validated and cleaned data dictionary
        """
        cleaned_data = {}
        validation_errors = []
        
        try:
            for key, value in data.items():
                if key in self.validation_ranges:
                    try:
                        # Convert to float and validate range
                        float_val = float(value)
                        min_val, max_val = self.validation_ranges[key]
                        
                        if min_val <= float_val <= max_val:
                            cleaned_data[key] = float_val
                        else:
                            # Clamp to valid range
                            cleaned_data[key] = max(min_val, min(max_val, float_val))
                            validation_errors.append(f"{key} clamped from {float_val} to {cleaned_data[key]}")
                            
                    except (ValueError, TypeError):
                        # Use safe default if conversion fails
                        default_val = (self.validation_ranges[key][0] + self.validation_ranges[key][1]) / 2
                        cleaned_data[key] = default_val
                        validation_errors.append(f"{key} invalid value, using default {default_val}")
                else:
                    # Pass through non-numeric data
                    cleaned_data[key] = value
            
            # Log validation errors if any
            if validation_errors:
                self.logger.warning(f"{data_type} data validation errors: {validation_errors}")
            
            # Add data quality indicator
            cleaned_data['data_quality'] = 'Good' if not validation_errors else 'Cleaned'
            cleaned_data['validation_errors'] = len(validation_errors)
            
            return cleaned_data
            
        except Exception as e:
            self.logger.error(f"Error validating {data_type} data: {e}")
            return data  # Return original data if validation fails
    
    def process_esp_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process ESP8266 sensor data
        
        Args:
            raw_data: Raw ESP data from API endpoint
            
        Returns:
            Processed data dictionary
        """
        try:
            # Validate data
            validated_data = self.validate_sensor_data(raw_data, 'esp')
            
            # Add processing timestamp
            validated_data['processed_at'] = datetime.now().isoformat()
            validated_data['data_source'] = 'esp8266'
            
            # Calculate derived values
            if 'esp_current' in validated_data and 'esp_voltage' in validated_data:
                validated_data['power_consumption'] = round(
                    validated_data['esp_current'] * validated_data['esp_voltage'] / 1000, 3
                )  # Power in kW
            
            # Convert temperature units if needed
            if 'env_temp_c' in validated_data:
                validated_data['env_temp_f'] = round(
                    validated_data['env_temp_c'] * 9/5 + 32, 1
                )
            
            # Store processed data
            self.store_sensor_data(validated_data, 'esp')
            
            # Emit real-time update
            if self.socketio:
                self.socketio.emit('esp_data_processed', validated_data)
            
            self.logger.debug(f"ESP data processed: {validated_data.get('esp_current')}A, {validated_data.get('esp_voltage')}V")
            
            return validated_data
            
        except Exception as e:
            self.logger.error(f"Error processing ESP data: {e}")
            return raw_data
    
    def process_plc_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process PLC sensor data
        
        Args:
            raw_data: Raw PLC data from API endpoint
            
        Returns:
            Processed data dictionary
        """
        try:
            # Validate data
            validated_data = self.validate_sensor_data(raw_data, 'plc')
            
            # Add processing timestamp
            validated_data['processed_at'] = datetime.now().isoformat()
            validated_data['data_source'] = 'fx5u_plc'
            
            # Calculate derived values
            if 'plc_motor_current' in validated_data and 'plc_motor_voltage' in validated_data:
                validated_data['plc_power_consumption'] = round(
                    validated_data['plc_motor_current'] * validated_data['plc_motor_voltage'] / 1000, 3
                )  # Power in kW
            
            # Calculate motor efficiency (simplified)
            if 'plc_motor_rpm' in validated_data and 'plc_power_consumption' in validated_data:
                if validated_data['plc_power_consumption'] > 0:
                    # Simplified efficiency calculation
                    validated_data['motor_efficiency'] = round(
                        min(100, validated_data['plc_motor_rpm'] / (validated_data['plc_power_consumption'] * 1000) * 0.1), 1
                    )
                else:
                    validated_data['motor_efficiency'] = 0
            
            # Store processed data
            self.store_sensor_data(validated_data, 'plc')
            
            # Emit real-time update
            if self.socketio:
                self.socketio.emit('plc_data_processed', validated_data)
            
            self.logger.debug(f"PLC data processed: {validated_data.get('plc_motor_temp')}°C, {validated_data.get('plc_motor_rpm')} RPM")
            
            return validated_data
            
        except Exception as e:
            self.logger.error(f"Error processing PLC data: {e}")
            return raw_data
    
    def store_sensor_data(self, data: Dict[str, Any], data_type: str):
        """
        Store processed sensor data to database
        
        Args:
            data: Processed sensor data
            data_type: 'esp' or 'plc'
        """
        try:
            with self.data_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                if data_type == 'esp':
                    cursor.execute('''
                        INSERT INTO sensor_data (
                            timestamp, esp_current, esp_voltage, esp_rpm, 
                            env_temp_c, env_humidity, esp_connected,
                            data_source
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        datetime.now().isoformat(),
                        data.get('esp_current', 0),
                        data.get('esp_voltage', 0),
                        data.get('esp_rpm', 0),
                        data.get('env_temp_c', 0),
                        data.get('env_humidity', 0),
                        True,  # esp_connected
                        'esp8266'
                    ))
                
                elif data_type == 'plc':
                    cursor.execute('''
                        INSERT INTO sensor_data (
                            timestamp, plc_motor_temp, plc_motor_voltage, 
                            plc_motor_current, plc_motor_rpm, plc_connected,
                            data_source
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        datetime.now().isoformat(),
                        data.get('plc_motor_temp', 0),
                        data.get('plc_motor_voltage', 0),
                        data.get('plc_motor_current', 0),
                        data.get('plc_motor_rpm', 0),
                        True,  # plc_connected
                        'fx5u_plc'
                    ))
                
                conn.commit()
                conn.close()
                
        except Exception as e:
            self.logger.error(f"Error storing {data_type} data: {e}")
    
    def get_recent_data(self, hours_back: int = 24, limit: int = 100) -> Dict[str, Any]:
        """
        Retrieve recent sensor data from database
        
        Args:
            hours_back: Hours to look back
            limit: Maximum number of records
            
        Returns:
            Dictionary with averaged recent data
        """
        try:
            with self.data_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cutoff_time = datetime.now() - timedelta(hours=hours_back)
                
                cursor.execute('''
                    SELECT 
                        AVG(esp_current), AVG(esp_voltage), AVG(esp_rpm), 
                        AVG(env_temp_c), AVG(env_humidity),
                        AVG(plc_motor_temp), AVG(plc_motor_voltage), 
                        AVG(plc_motor_current), AVG(plc_motor_rpm),
                        COUNT(*) as record_count,
                        MAX(timestamp) as latest_record
                    FROM sensor_data 
                    WHERE timestamp > ? 
                    LIMIT ?
                ''', (cutoff_time.isoformat(), limit))
                
                row = cursor.fetchone()
                conn.close()
                
                if row and row[0] is not None:
                    return {
                        'esp_current': round(row[0] or 0, 2),
                        'esp_voltage': round(row[1] or 0, 2),
                        'esp_rpm': int(row[2] or 0),
                        'env_temp_c': round(row[3] or 0, 1),
                        'env_humidity': round(row[4] or 0, 1),
                        'plc_motor_temp': round(row[5] or 0, 1),
                        'plc_motor_voltage': round(row[6] or 0, 2),
                        'plc_motor_current': round(row[7] or 0, 2),
                        'plc_motor_rpm': int(row[8] or 0),
                        'record_count': row[9],
                        'latest_record': row[10],
                        'data_source': 'historical_database',
                        'hours_covered': hours_back
                    }
                else:
                    # Return safe defaults if no data found
                    return self.get_safe_defaults()
                    
        except Exception as e:
            self.logger.error(f"Error retrieving recent data: {e}")
            return self.get_safe_defaults()
    
    def get_safe_defaults(self) -> Dict[str, Any]:
        """
        Get safe default values for fallback
        
        Returns:
            Dictionary with safe default sensor values
        """
        return {
            'esp_current': 6.0,
            'esp_voltage': 24.0,
            'esp_rpm': 2750,
            'env_temp_c': 25.0,
            'env_humidity': 45.0,
            'plc_motor_temp': 40.0,
            'plc_motor_voltage': 24.0,
            'plc_motor_current': 6.0,
            'plc_motor_rpm': 2750,
            'record_count': 0,
            'latest_record': None,
            'data_source': 'safe_defaults',
            'hours_covered': 0
        }
    
    def calculate_data_quality_score(self, esp_data: Dict, plc_data: Dict) -> Dict[str, Any]:
        """
        Calculate overall data quality score
        
        Args:
            esp_data: ESP sensor data
            plc_data: PLC sensor data
            
        Returns:
            Data quality assessment
        """
        try:
            score = 100
            issues = []
            
            # Check ESP data quality
            esp_connected = esp_data.get('esp_connected', False)
            esp_errors = esp_data.get('validation_errors', 0)
            
            if not esp_connected:
                score -= 25
                issues.append('ESP disconnected')
            
            if esp_errors > 0:
                score -= min(20, esp_errors * 5)
                issues.append(f'ESP validation errors: {esp_errors}')
            
            # Check PLC data quality
            plc_connected = plc_data.get('plc_connected', False)
            plc_errors = plc_data.get('validation_errors', 0)
            
            if not plc_connected:
                score -= 25
                issues.append('PLC disconnected')
            
            if plc_errors > 0:
                score -= min(20, plc_errors * 5)
                issues.append(f'PLC validation errors: {plc_errors}')
            
            # Determine quality level
            if score >= 90:
                quality_level = 'Excellent'
            elif score >= 75:
                quality_level = 'Good'
            elif score >= 60:
                quality_level = 'Fair'
            elif score >= 40:
                quality_level = 'Poor'
            else:
                quality_level = 'Critical'
            
            return {
                'data_quality_score': max(0, score),
                'quality_level': quality_level,
                'issues': issues,
                'esp_connected': esp_connected,
                'plc_connected': plc_connected,
                'total_errors': esp_errors + plc_errors,
                'assessment_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating data quality: {e}")
            return {
                'data_quality_score': 50,
                'quality_level': 'Unknown',
                'issues': ['Quality calculation error'],
                'esp_connected': False,
                'plc_connected': False,
                'total_errors': 0
            }
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """
        Clean up old sensor data from database
        
        Args:
            days_to_keep: Number of days of data to retain
        """
        try:
            with self.data_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cutoff_date = datetime.now() - timedelta(days=days_to_keep)
                
                cursor.execute('''
                    DELETE FROM sensor_data 
                    WHERE timestamp < ?
                ''', (cutoff_date.isoformat(),))
                
                deleted_rows = cursor.rowcount
                conn.commit()
                conn.close()
                
                if deleted_rows > 0:
                    self.logger.info(f"Cleaned up {deleted_rows} old sensor records")
                
        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {e}")
    
    def get_data_statistics(self) -> Dict[str, Any]:
        """
        Get database statistics
        
        Returns:
            Dictionary with database statistics
        """
        try:
            with self.data_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Get total record count
                cursor.execute('SELECT COUNT(*) FROM sensor_data')
                total_records = cursor.fetchone()[0]
                
                # Get date range
                cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM sensor_data')
                date_range = cursor.fetchone()
                
                # Get recent activity
                cutoff = datetime.now() - timedelta(hours=24)
                cursor.execute('SELECT COUNT(*) FROM sensor_data WHERE timestamp > ?', 
                             (cutoff.isoformat(),))
                recent_records = cursor.fetchone()[0]
                
                conn.close()
                
                return {
                    'total_records': total_records,
                    'earliest_record': date_range[0],
                    'latest_record': date_range[1],
                    'records_24h': recent_records,
                    'database_path': self.db_path,
                    'database_size_mb': round(os.path.getsize(self.db_path) / 1024 / 1024, 2) if os.path.exists(self.db_path) else 0
                }
                
        except Exception as e:
            self.logger.error(f"Error getting database statistics: {e}")
            return {
                'total_records': 0,
                'error': str(e)
            }
    
    def stop(self):
        """Stop the data processor"""
        self.logger.info("Data processor stopped")

# Example usage
if __name__ == "__main__":
    processor = DataProcessor()
    
    # Test ESP data processing
    esp_test_data = {
        'esp_current': 6.25,
        'esp_voltage': 24.1,
        'esp_rpm': 2750,
        'env_temp_c': 25.5,
        'env_humidity': 45.0
    }
    
    processed_esp = processor.process_esp_data(esp_test_data)
    print("Processed ESP data:", processed_esp)
    
    # Test PLC data processing
    plc_test_data = {
        'plc_motor_temp': 42.0,
        'plc_motor_voltage': 24.0,
        'plc_motor_current': 6.0,
        'plc_motor_rpm': 2750
    }
    
    processed_plc = processor.process_plc_data(plc_test_data)
    print("Processed PLC data:", processed_plc)
    
    # Get statistics
    stats = processor.get_data_statistics()
    print("Database statistics:", stats)
