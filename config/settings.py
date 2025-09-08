"""
System Configuration Settings
Centralized configuration management for the AI Motor Monitoring System
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class DatabaseConfig:
    """Database configuration settings"""
    url: str = os.getenv('DATABASE_URL', 'sqlite:///data/motor_monitoring.db')
    csv_export_path: str = os.getenv('CSV_EXPORT_PATH', 'data/sensor_data.csv')
    
@dataclass
class PLCConfig:
    """FX5U PLC configuration settings"""
    ip: str = os.getenv('PLC_IP', '192.168.3.39')
    port: int = int(os.getenv('PLC_PORT', '5007'))
    
@dataclass
class FlaskConfig:
    """Flask application configuration"""
    host: str = os.getenv('FLASK_HOST', '0.0.0.0')
    port: int = int(os.getenv('FLASK_PORT', '5000'))
    debug: bool = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    secret_key: str = os.getenv('SECRET_KEY', 'motor_monitoring_secret')

@dataclass
class ConnectionConfig:
    """Connection timeout configuration"""
    esp_timeout: int = int(os.getenv('ESP_TIMEOUT', '30'))
    plc_timeout: int = int(os.getenv('PLC_TIMEOUT', '60'))
    data_cleanup_interval: int = int(os.getenv('DATA_CLEANUP_INTERVAL', '10'))

@dataclass
class OptimalValues:
    """Motor system optimal values"""
    motor_temp: float = float(os.getenv('OPTIMAL_MOTOR_TEMP', '40.0'))
    voltage: float = float(os.getenv('OPTIMAL_VOLTAGE', '24.0'))
    current: float = float(os.getenv('OPTIMAL_CURRENT', '6.25'))
    dht_temp: float = float(os.getenv('OPTIMAL_DHT_TEMP', '24.0'))
    dht_humidity: float = float(os.getenv('OPTIMAL_DHT_HUMIDITY', '40.0'))
    rpm: float = float(os.getenv('OPTIMAL_RPM', '2750.0'))

@dataclass
class Thresholds:
    """System threshold values"""
    # Motor Temperature Thresholds
    motor_temp_excellent: float = 35.0
    motor_temp_good: float = 40.0
    motor_temp_warning: float = 50.0
    motor_temp_critical: float = 60.0
    
    # Voltage Thresholds (24V ±10%)
    voltage_min_critical: float = 20.0
    voltage_min_warning: float = 22.0
    voltage_max_warning: float = 26.0
    voltage_max_critical: float = 28.0
    
    # Current Thresholds
    current_min_warning: float = 4.0
    current_optimal_min: float = 5.0
    current_optimal_max: float = 7.5
    current_max_warning: float = 9.0
    current_max_critical: float = 12.0
    
    # RPM Thresholds (2750 ±5%)
    rpm_min_critical: float = 2400.0
    rpm_min_warning: float = 2600.0
    rpm_max_warning: float = 2900.0
    rpm_max_critical: float = 3100.0
    
    # Environmental Thresholds
    dht_temp_max_warning: float = 30.0
    dht_temp_max_critical: float = 35.0
    dht_humidity_min_warning: float = 30.0
    dht_humidity_max_warning: float = 70.0
    dht_humidity_max_critical: float = 80.0

@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = os.getenv('LOG_LEVEL', 'INFO')
    file: str = os.getenv('LOG_FILE', 'logs/application.log')
    format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

@dataclass
class SystemConfig:
    """Complete system configuration"""
    database: DatabaseConfig = DatabaseConfig()
    plc: PLCConfig = PLCConfig()
    flask: FlaskConfig = FlaskConfig()
    connection: ConnectionConfig = ConnectionConfig()
    optimal: OptimalValues = OptimalValues()
    thresholds: Thresholds = Thresholds()
    logging: LoggingConfig = LoggingConfig()
    
    # Paths
    model_path: str = 'models/'
    data_retention_days: int = 90

# Global configuration instance
config = SystemConfig()
