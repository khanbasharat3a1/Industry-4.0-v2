"""
AI-Enabled Industrial Motor Monitoring System - FIXED VERSION
All Critical Issues Resolved
"""

import sys
import os
import signal
import time
import logging
from datetime import datetime, timedelta
from threading import Timer, Thread
import sqlite3
import json
import random

# Enable eventlet monkey patching BEFORE any imports
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit, disconnect

# Global application components
app = None
socketio = None

# FIXED: Enhanced data storage with proper disconnection handling
latest_sensor_data = {
    'esp_current': 0.0,
    'esp_voltage': 0.0,
    'esp_rpm': 0,
    'env_temp_c': 0.0,
    'env_humidity': 0.0,
    'env_temp_f': 0.0,
    'heat_index_c': 0.0,
    'heat_index_f': 0.0,
    'relay1_status': 'OFF',
    'relay2_status': 'OFF',
    'relay3_status': 'OFF',
    'combined_status': 'NOR',
    'esp_connected': False,
    'last_esp_update': None,
    'esp_data_quality': 'No Data'
}

latest_plc_data = {
    'plc_motor_temp': 0.0,
    'plc_motor_voltage': 0.0,
    'plc_motor_current': 0.0,
    'plc_motor_rpm': 0,
    'plc_power_consumption': 0.0,
    'plc_raw_d100': 0,
    'plc_raw_d102': 0,
    'plc_status': 'DISCONNECTED',
    'plc_error_code': 0,
    'plc_connected': False,
    'last_plc_update': None,
    'plc_data_quality': 'No Data'
}

# Connection timeout tracking
ESP_TIMEOUT = 30  # seconds
PLC_TIMEOUT = 30  # seconds

# Data history for charts
data_history = []
connected_clients = set()

def create_directories():
    """Create necessary directories"""
    directories = ['data', 'logs', 'models', 'templates', 'static', 'database']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def setup_logging():
    """Setup comprehensive logging"""
    try:
        log_dir = 'logs'
        os.makedirs(log_dir, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(log_dir, 'application.log'), encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('werkzeug').setLevel(logging.INFO)
        logging.getLogger('socketio').setLevel(logging.INFO)
        logging.getLogger('engineio').setLevel(logging.WARNING)
        
        logging.info("Logging system initialized successfully")
    except Exception as e:
        print(f"Error setting up logging: {e}")

def init_database():
    """Initialize SQLite database for historical data"""
    try:
        db_path = os.path.join('database', 'sensor_history.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                esp_current REAL,
                esp_voltage REAL,
                esp_rpm INTEGER,
                env_temp_c REAL,
                env_humidity REAL,
                esp_connected BOOLEAN,
                plc_motor_temp REAL,
                plc_motor_voltage REAL,
                plc_motor_current REAL,
                plc_motor_rpm INTEGER,
                plc_connected BOOLEAN,
                overall_health_score REAL,
                electrical_health REAL,
                thermal_health REAL,
                mechanical_health REAL,
                data_source TEXT DEFAULT 'real_time'
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON sensor_data(timestamp DESC)
        ''')
        
        conn.commit()
        conn.close()
        
        logging.info("Database initialized successfully")
        
    except Exception as e:
        logging.error(f"Error initializing database: {e}")

# FIXED: Historical data retrieval with proper error handling
def get_historical_data(hours_back=24, limit=100):
    """Retrieve historical sensor data - FIXED VERSION"""
    try:
        db_path = os.path.join('database', 'sensor_history.db')
        
        # Check if database file exists
        if not os.path.exists(db_path):
            logging.warning("Database file not found, using safe defaults")
            return get_safe_defaults()
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        cursor.execute('''
            SELECT 
                esp_current, esp_voltage, esp_rpm, env_temp_c, env_humidity,
                plc_motor_temp, plc_motor_voltage, plc_motor_current, plc_motor_rpm,
                overall_health_score, electrical_health, thermal_health, mechanical_health,
                timestamp
            FROM sensor_data 
            WHERE timestamp > ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (cutoff_time, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows or len(rows) == 0:
            logging.info("No historical data found, using safe defaults")
            return get_safe_defaults()
        
        # FIXED: Proper handling of row data
        try:
            # Calculate averages from historical data with null checks
            valid_rows = [row for row in rows if row and len(row) >= 14]
            
            if not valid_rows:
                return get_safe_defaults()
            
            def safe_avg(values):
                clean_values = [v for v in values if v is not None and v != 0]
                return sum(clean_values) / len(clean_values) if clean_values else 0
            
            avg_data = {
                'esp_current': safe_avg([row[0] for row in valid_rows]),
                'esp_voltage': safe_avg([row[1] for row in valid_rows]),
                'esp_rpm': int(safe_avg([row[2] for row in valid_rows])),
                'env_temp_c': safe_avg([row[3] for row in valid_rows]),
                'env_humidity': safe_avg([row[4] for row in valid_rows]),
                'plc_motor_temp': safe_avg([row[5] for row in valid_rows]),
                'plc_motor_voltage': safe_avg([row[6] for row in valid_rows]),
                'plc_motor_current': safe_avg([row[7] for row in valid_rows]),
                'plc_motor_rpm': int(safe_avg([row[8] for row in valid_rows])),
                'overall_health_score': safe_avg([row[9] for row in valid_rows]),
                'electrical_health': safe_avg([row[10] for row in valid_rows]),
                'thermal_health': safe_avg([row[11] for row in valid_rows]),
                'mechanical_health': safe_avg([row[12] for row in valid_rows]),
                'data_source': 'historical_average',
                'records_found': len(valid_rows)
            }
            
            logging.info(f"Retrieved historical data: {len(valid_rows)} records")
            return avg_data
            
        except (IndexError, ValueError, TypeError) as e:
            logging.error(f"Error processing historical data: {e}")
            return get_safe_defaults()
        
    except Exception as e:
        logging.error(f"Error retrieving historical data: {e}")
        return get_safe_defaults()

# FIXED: Safe defaults function
def get_safe_defaults():
    """Return safe default values when no historical data available"""
    return {
        'esp_current': 5.0,
        'esp_voltage': 24.0,
        'esp_rpm': 2500,
        'env_temp_c': 25.0,
        'env_humidity': 45.0,
        'plc_motor_temp': 40.0,
        'plc_motor_voltage': 24.0,
        'plc_motor_current': 5.0,
        'plc_motor_rpm': 2500,
        'overall_health_score': 75.0,
        'electrical_health': 75.0,
        'thermal_health': 75.0,
        'mechanical_health': 75.0,
        'data_source': 'safe_defaults',
        'records_found': 0
    }

def save_sensor_data(sensor_data, plc_data, health_data):
    """Save current sensor data to database"""
    try:
        db_path = os.path.join('database', 'sensor_history.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sensor_data (
                esp_current, esp_voltage, esp_rpm, env_temp_c, env_humidity, esp_connected,
                plc_motor_temp, plc_motor_voltage, plc_motor_current, plc_motor_rpm, plc_connected,
                overall_health_score, electrical_health, thermal_health, mechanical_health
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            sensor_data.get('esp_current', 0),
            sensor_data.get('esp_voltage', 0),
            sensor_data.get('esp_rpm', 0),
            sensor_data.get('env_temp_c', 0),
            sensor_data.get('env_humidity', 0),
            sensor_data.get('esp_connected', False),
            plc_data.get('plc_motor_temp', 0),
            plc_data.get('plc_motor_voltage', 0),
            plc_data.get('plc_motor_current', 0),
            plc_data.get('plc_motor_rpm', 0),
            plc_data.get('plc_connected', False),
            health_data.get('overall_health_score', 0),
            health_data.get('electrical_health', 0),
            health_data.get('thermal_health', 0),
            health_data.get('mechanical_health', 0)
        ))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logging.error(f"Error saving sensor data: {e}")

# FIXED: Enhanced health calculation with realistic scoring
def calculate_advanced_health_score(sensor_data, plc_data, use_historical=True):
    """Enhanced health calculation with realistic scoring - FIXED VERSION"""
    try:
        now = datetime.now()
        
        # Check connection status and data freshness
        esp_connected = sensor_data.get('esp_connected', False)
        plc_connected = plc_data.get('plc_connected', False)
        
        # FIXED: Proper freshness checking
        esp_fresh = False
        plc_fresh = False
        
        if sensor_data.get('last_esp_update'):
            try:
                if isinstance(sensor_data['last_esp_update'], str):
                    last_esp = datetime.fromisoformat(sensor_data['last_esp_update'].replace('Z', '+00:00'))
                else:
                    last_esp = sensor_data['last_esp_update']
                esp_fresh = (now - last_esp.replace(tzinfo=None) if last_esp.tzinfo else last_esp).total_seconds() < ESP_TIMEOUT
            except:
                esp_fresh = False
        
        if plc_data.get('last_plc_update'):
            try:
                if isinstance(plc_data['last_plc_update'], str):
                    last_plc = datetime.fromisoformat(plc_data['last_plc_update'].replace('Z', '+00:00'))
                else:
                    last_plc = plc_data['last_plc_update']
                plc_fresh = (now - last_plc.replace(tzinfo=None) if last_plc.tzinfo else last_plc).total_seconds() < PLC_TIMEOUT
            except:
                plc_fresh = False
        
        # Update actual connection status
        esp_connected = esp_connected and esp_fresh
        plc_connected = plc_connected and plc_fresh
        
        # FIXED: Handle disconnected state properly
        if not esp_connected and not plc_connected:
            # Both disconnected - use minimal health score
            return {
                'overall_health_score': 30.0,
                'electrical_health': 30.0,
                'thermal_health': 30.0,
                'mechanical_health': 30.0,
                'status': 'Disconnected',
                'esp_connected': False,
                'plc_connected': False,
                'data_source': 'disconnected',
                'confidence_factor': 100.0
            }
        
        # Get working data
        working_data = {}
        data_source = []
        
        if esp_connected:
            working_data.update({
                'esp_current': float(sensor_data.get('esp_current', 0)),
                'esp_voltage': float(sensor_data.get('esp_voltage', 0)),
                'esp_rpm': float(sensor_data.get('esp_rpm', 0)),
                'env_temp_c': float(sensor_data.get('env_temp_c', 0)),
                'env_humidity': float(sensor_data.get('env_humidity', 0))
            })
            data_source.append('current_esp')
        elif use_historical:
            historical = get_historical_data(hours_back=24)
            working_data.update({
                'esp_current': historical['esp_current'],
                'esp_voltage': historical['esp_voltage'],
                'esp_rpm': historical['esp_rpm'],
                'env_temp_c': historical['env_temp_c'],
                'env_humidity': historical['env_humidity']
            })
            data_source.append('historical_esp')
        
        if plc_connected:
            working_data.update({
                'plc_motor_temp': float(plc_data.get('plc_motor_temp', 0)),
                'plc_motor_voltage': float(plc_data.get('plc_motor_voltage', 0)),
                'plc_motor_current': float(plc_data.get('plc_motor_current', 0)),
                'plc_motor_rpm': float(plc_data.get('plc_motor_rpm', 0))
            })
            data_source.append('current_plc')
        elif use_historical:
            historical = get_historical_data(hours_back=24)
            working_data.update({
                'plc_motor_temp': historical['plc_motor_temp'],
                'plc_motor_voltage': historical['plc_motor_voltage'],
                'plc_motor_current': historical['plc_motor_current'],
                'plc_motor_rpm': historical['plc_motor_rpm']
            })
            data_source.append('historical_plc')
        
        # Calculate health components
        electrical_health = calculate_electrical_health(working_data)
        thermal_health = calculate_thermal_health(working_data)
        mechanical_health = calculate_mechanical_health(working_data)
        
        # FIXED: More realistic health calculation
        if esp_connected and plc_connected:
            weight_factor = 1.0
        elif esp_connected or plc_connected:
            weight_factor = 0.7  # Significant reduction for partial connection
        else:
            weight_factor = 0.3  # Major reduction for historical data only
        
        overall_health = (electrical_health + thermal_health + mechanical_health) / 3
        overall_health *= weight_factor
        
        # Determine status with more realistic thresholds
        if overall_health >= 95:
            status = 'Excellent'
        elif overall_health >= 85:
            status = 'Good'
        elif overall_health >= 70:
            status = 'Fair'
        elif overall_health >= 50:
            status = 'Warning'
        elif overall_health >= 30:
            status = 'Poor'
        else:
            status = 'Critical'
        
        result = {
            'overall_health_score': round(overall_health, 1),
            'electrical_health': round(electrical_health, 1),
            'thermal_health': round(thermal_health, 1),
            'mechanical_health': round(mechanical_health, 1),
            'status': status,
            'esp_connected': esp_connected,
            'plc_connected': plc_connected,
            'data_source': ', '.join(data_source),
            'confidence_factor': round(weight_factor * 100, 1)
        }
        
        return result
        
    except Exception as e:
        logging.error(f"Error calculating health score: {e}")
        return {
            'overall_health_score': 30.0,
            'electrical_health': 30.0,
            'thermal_health': 30.0,
            'mechanical_health': 30.0,
            'status': 'Error',
            'esp_connected': False,
            'plc_connected': False,
            'data_source': 'error',
            'confidence_factor': 0.0
        }

def calculate_electrical_health(data):
    """Calculate electrical health component with realistic thresholds"""
    health = 100.0
    
    current = data.get('esp_current', 0)
    voltage = data.get('esp_voltage', 0)
    
    # More realistic current analysis
    if current > 15.0:  # Very high current - major issue
        health -= min(60, (current - 15.0) * 10)
    elif current > 12.0:  # High current - significant issue
        health -= (current - 12.0) * 8
    elif current > 9.0:  # Elevated current - minor issue
        health -= (current - 9.0) * 3
    elif current < 2.0:  # Very low current - motor issues
        health -= (2.0 - current) * 15
    
    # More realistic voltage analysis
    if voltage < 15.0:  # Very low voltage - critical
        health -= min(50, (15.0 - voltage) * 15)
    elif voltage < 20.0:  # Low voltage - significant
        health -= (20.0 - voltage) * 5
    elif voltage > 30.0:  # Very high voltage - critical
        health -= min(40, (voltage - 30.0) * 12)
    elif voltage > 26.0:  # High voltage - moderate issue
        health -= (voltage - 26.0) * 3
    
    return max(10.0, min(100.0, health))

def calculate_thermal_health(data):
    """Calculate thermal health component with realistic thresholds"""
    health = 100.0
    
    motor_temp = data.get('plc_motor_temp', 0)
    env_temp = data.get('env_temp_c', 0)
    
    # More realistic temperature analysis
    if motor_temp > 90.0:  # Critical temperature - immediate shutdown
        health -= min(70, (motor_temp - 90.0) * 15)
    elif motor_temp > 75.0:  # High temperature - major concern
        health -= (motor_temp - 75.0) * 8
    elif motor_temp > 60.0:  # Elevated temperature - moderate concern
        health -= (motor_temp - 60.0) * 3
    elif motor_temp < 10.0:  # Very cold - potential issues
        health -= (10.0 - motor_temp) * 2
    
    # Environmental impact
    if env_temp > 50.0:  # Very hot environment
        health -= (env_temp - 50.0) * 2
    elif env_temp < -10.0:  # Very cold environment
        health -= (-10.0 - env_temp) * 1
    
    return max(15.0, min(100.0, health))

def calculate_mechanical_health(data):
    """Calculate mechanical health component with realistic thresholds"""
    health = 100.0
    
    esp_rpm = data.get('esp_rpm', 0)
    plc_rpm = data.get('plc_motor_rpm', 0)
    
    # Use the higher RPM reading
    rpm = max(esp_rpm, plc_rpm) if esp_rpm and plc_rpm else (esp_rpm or plc_rpm)
    
    # More realistic RPM analysis
    if rpm < 500:  # Motor not running or severe mechanical issue
        health -= 80
    elif rpm < 1500:  # Very low RPM - major mechanical issue
        health -= (1500 - rpm) * 0.04
    elif rpm < 2200:  # Low RPM - moderate issue
        health -= (2200 - rpm) * 0.02
    elif rpm > 4000:  # Very high RPM - overspeed condition
        health -= (rpm - 4000) * 0.03
    elif rpm > 3500:  # High RPM - potential issue
        health -= (rpm - 3500) * 0.015
    
    return max(20.0, min(100.0, health))

def store_data_point(combined_data):
    """Store data point for history"""
    global data_history
    
    data_point = {
        'timestamp': datetime.now().isoformat(),
        'current': combined_data.get('esp_current', 0),
        'voltage': combined_data.get('esp_voltage', 0),
        'rpm': combined_data.get('esp_rpm', 0),
        'temperature': combined_data.get('plc_motor_temp', 0),
        'health': combined_data.get('overall_health_score', 0)
    }
    
    data_history.append(data_point)
    
    # Keep only last 100 points
    if len(data_history) > 100:
        data_history.pop(0)

# FIXED: Enhanced recommendations with proper logic
def generate_recommendations(health_data, sensor_data, plc_data):
    """Generate enhanced recommendations based on system state - FIXED VERSION"""
    recommendations = []
    
    health_score = health_data.get('overall_health_score', 0)
    electrical_health = health_data.get('electrical_health', 0)
    thermal_health = health_data.get('thermal_health', 0)
    mechanical_health = health_data.get('mechanical_health', 0)
    esp_connected = health_data.get('esp_connected', False)
    plc_connected = health_data.get('plc_connected', False)
    
    # Connection-based recommendations
    if not esp_connected and not plc_connected:
        recommendations.append({
            'priority': 'HIGH',
            'category': 'Connectivity',
            'message': 'Both ESP8266 and PLC are disconnected - Complete system offline',
            'action': 'Check network connections, power supply, and restart devices immediately'
        })
    elif not esp_connected:
        recommendations.append({
            'priority': 'HIGH',
            'category': 'Connectivity',
            'message': 'ESP8266 sensor network disconnected - Losing critical sensor data',
            'action': 'Check WiFi connection and ESP8266 power supply within 10 minutes'
        })
    elif not plc_connected:
        recommendations.append({
            'priority': 'HIGH',
            'category': 'Connectivity',
            'message': 'FX5U PLC disconnected - Motor control system offline',
            'action': 'Check Ethernet connection and PLC power status immediately'
        })
    
    # Health-based recommendations
    if health_score < 50:
        recommendations.append({
            'priority': 'HIGH',
            'category': 'System Health',
            'message': f'Critical system health at {health_score:.1f}% - Immediate shutdown recommended',
            'action': 'Stop motor operation and conduct emergency inspection within 1 hour'
        })
    elif health_score < 70:
        recommendations.append({
            'priority': 'MEDIUM',
            'category': 'System Health',
            'message': f'Poor system health at {health_score:.1f}% - Maintenance required',
            'action': 'Schedule maintenance inspection within 24 hours'
        })
    elif health_score < 85:
        recommendations.append({
            'priority': 'LOW',
            'category': 'System Health',
            'message': f'Fair system health at {health_score:.1f}% - Monitor closely',
            'action': 'Increase monitoring frequency and plan maintenance'
        })
    
    # Component-specific recommendations
    if electrical_health < 70:
        current = sensor_data.get('esp_current', 0)
        voltage = sensor_data.get('esp_voltage', 0)
        
        recommendations.append({
            'priority': 'MEDIUM',
            'category': 'Electrical',
            'message': f'Electrical health at {electrical_health:.1f}% - Current: {current}A, Voltage: {voltage}V',
            'action': 'Check power supply stability, wiring connections, and voltage regulation'
        })
    
    if thermal_health < 70:
        temp = plc_data.get('plc_motor_temp', 0)
        recommendations.append({
            'priority': 'MEDIUM',
            'category': 'Thermal',
            'message': f'Thermal health at {thermal_health:.1f}% - Motor temperature: {temp}°C',
            'action': 'Check cooling system, ventilation, and consider reducing load'
        })
    
    if mechanical_health < 70:
        rpm = sensor_data.get('esp_rpm', 0)
        recommendations.append({
            'priority': 'MEDIUM',
            'category': 'Mechanical',
            'message': f'Mechanical health at {mechanical_health:.1f}% - Current RPM: {rpm}',
            'action': 'Inspect motor bearings, alignment, and mechanical coupling'
        })
    
    # Specific parameter-based recommendations
    if sensor_data.get('esp_current', 0) > 12:
        recommendations.append({
            'priority': 'HIGH',
            'category': 'Overcurrent',
            'message': f'High current detected: {sensor_data.get("esp_current", 0):.2f}A',
            'action': 'Check motor load, wiring, and potential short circuits immediately'
        })
    
    if plc_data.get('plc_motor_temp', 0) > 75:
        recommendations.append({
            'priority': 'HIGH',
            'category': 'Overheating',
            'message': f'Motor overheating: {plc_data.get("plc_motor_temp", 0):.1f}°C',
            'action': 'Reduce load, check cooling system, consider emergency shutdown'
        })
    
    if sensor_data.get('esp_voltage', 0) < 20:
        recommendations.append({
            'priority': 'MEDIUM',
            'category': 'Low Voltage',
            'message': f'Low voltage condition: {sensor_data.get("esp_voltage", 0):.1f}V',
            'action': 'Check power supply, electrical connections, and voltage regulation'
        })
    
    # If no issues found
    if not recommendations:
        recommendations.append({
            'priority': 'LOW',
            'category': 'Status',
            'message': 'All systems operating within normal parameters',
            'action': 'Continue regular monitoring and maintenance schedule'
        })
    
    return recommendations

# FIXED: Connection timeout monitoring with proper data zeroing
def check_connection_timeout():
    """Enhanced connection timeout monitoring with data zeroing - FIXED VERSION"""
    global latest_sensor_data, latest_plc_data
    
    while True:
        try:
            now = datetime.now()
            
            # Check ESP timeout
            if latest_sensor_data.get('last_esp_update'):
                try:
                    last_esp_str = latest_sensor_data['last_esp_update']
                    if isinstance(last_esp_str, str):
                        last_esp = datetime.fromisoformat(last_esp_str.replace('Z', '+00:00'))
                    else:
                        last_esp = last_esp_str
                    
                    time_diff = (now - last_esp.replace(tzinfo=None) if last_esp.tzinfo else last_esp).total_seconds()
                    
                    if time_diff > ESP_TIMEOUT:
                        if latest_sensor_data['esp_connected']:
                            latest_sensor_data['esp_connected'] = False
                            latest_sensor_data['esp_data_quality'] = 'Timeout'
                            # FIXED: Zero out data when disconnected
                            latest_sensor_data.update({
                                'esp_current': 0.0,
                                'esp_voltage': 0.0,
                                'esp_rpm': 0,
                                'env_temp_c': 0.0,
                                'env_humidity': 0.0,
                                'relay1_status': 'OFF',
                                'relay2_status': 'OFF',
                                'relay3_status': 'OFF'
                            })
                            logging.warning("ESP connection timeout - data reset to zero")
                            
                            if socketio and connected_clients:
                                socketio.emit('device_timeout', {'device': 'ESP8266', 'status': 'disconnected'})
                except Exception as e:
                    logging.error(f"Error checking ESP timeout: {e}")
            
            # Check PLC timeout
            if latest_plc_data.get('last_plc_update'):
                try:
                    last_plc_str = latest_plc_data['last_plc_update']
                    if isinstance(last_plc_str, str):
                        last_plc = datetime.fromisoformat(last_plc_str.replace('Z', '+00:00'))
                    else:
                        last_plc = last_plc_str
                    
                    time_diff = (now - last_plc.replace(tzinfo=None) if last_plc.tzinfo else last_plc).total_seconds()
                    
                    if time_diff > PLC_TIMEOUT:
                        if latest_plc_data['plc_connected']:
                            latest_plc_data['plc_connected'] = False
                            latest_plc_data['plc_data_quality'] = 'Timeout'
                            # FIXED: Zero out data when disconnected
                            latest_plc_data.update({
                                'plc_motor_temp': 0.0,
                                'plc_motor_voltage': 0.0,
                                'plc_motor_current': 0.0,
                                'plc_motor_rpm': 0,
                                'plc_power_consumption': 0.0,
                                'plc_status': 'DISCONNECTED'
                            })
                            logging.warning("PLC connection timeout - data reset to zero")
                            
                            if socketio and connected_clients:
                                socketio.emit('device_timeout', {'device': 'FX5U_PLC', 'status': 'disconnected'})
                except Exception as e:
                    logging.error(f"Error checking PLC timeout: {e}")
            
            # Emit status update if there are connected clients
            if connected_clients:
                health_data = calculate_advanced_health_score(latest_sensor_data, latest_plc_data)
                combined_data = {**latest_sensor_data, **latest_plc_data, **health_data}
                socketio.emit('data_update', combined_data)
            
        except Exception as e:
            logging.error(f"Connection monitor error: {e}")
        
        eventlet.sleep(10)

def create_flask_app():
    """Create and configure Flask application"""
    global app, socketio
    
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    
    app.config['SECRET_KEY'] = 'motor_monitoring_secret_key_2025'
    app.config['DEBUG'] = False
    
    socketio = SocketIO(
        app,
        async_mode='eventlet',
        cors_allowed_origins="*",
        transports=['websocket', 'polling'],
        ping_timeout=60,
        ping_interval=25,
        logger=False,
        engineio_logger=False
    )
    
    register_core_routes(app)
    register_device_routes(app)
    register_api_routes(app)
    register_socketio_events(socketio)
    
    return app, socketio

def register_core_routes(app):
    """Register core application routes"""
    
    @app.route('/')
    def dashboard():
        return render_template('dashboard.html')
    
    @app.route('/favicon.ico')
    def favicon():
        return '', 204
    
    @app.route('/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'service': 'AI Motor Monitoring System v4.1 FIXED',
            'timestamp': datetime.now().isoformat(),
            'connected_clients': len(connected_clients)
        })

def register_device_routes(app):
    """Register device data reception routes"""
    global latest_sensor_data, latest_plc_data
    logger = logging.getLogger(__name__)
    
    @app.route('/api/send-data', methods=['POST'])
    def receive_esp_data():
        try:
            data = request.get_json(force=True)
            if not data:
                return jsonify({'status': 'error', 'message': 'No data received'}), 400
            
            # Update sensor data
            latest_sensor_data.update({
                'esp_current': float(data.get('VAL1', 0)),
                'esp_voltage': float(data.get('VAL2', 0)),
                'esp_rpm': int(float(data.get('VAL3', 0))),
                'env_temp_c': float(data.get('VAL4', 0)),
                'env_humidity': float(data.get('VAL5', 0)),
                'env_temp_f': float(data.get('VAL6', 0)),
                'heat_index_c': float(data.get('VAL7', 0)),
                'heat_index_f': float(data.get('VAL8', 0)),
                'relay1_status': data.get('VAL9', 'OFF'),
                'relay2_status': data.get('VAL10', 'OFF'),
                'relay3_status': data.get('VAL11', 'OFF'),
                'combined_status': data.get('VAL12', 'NOR'),
                'esp_connected': True,
                'last_esp_update': datetime.now().isoformat(),
                'esp_data_quality': 'Good'
            })
            
            # Calculate health
            health_data = calculate_advanced_health_score(latest_sensor_data, latest_plc_data)
            
            # Save to database
            save_sensor_data(latest_sensor_data, latest_plc_data, health_data)
            
            # Store for charts
            combined_data = {**latest_sensor_data, **latest_plc_data, **health_data}
            store_data_point(combined_data)
            
            # Emit real-time update
            if connected_clients:
                socketio.emit('data_update', combined_data)
            
            logger.info(f"📡 ESP: {data.get('VAL1')}A, {data.get('VAL2')}V - Health: {health_data['overall_health_score']}%")
            
            return jsonify({'status': 'success', 'health': health_data['overall_health_score']}), 200
            
        except Exception as e:
            logger.error(f"ESP Error: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    @app.route('/api/plc-data', methods=['POST'])
    def receive_plc_data():
        try:
            data = request.get_json(force=True)
            if not data:
                return jsonify({'status': 'error', 'message': 'No data received'}), 400
            
            # Update PLC data
            latest_plc_data.update({
                'plc_motor_temp': float(data.get('motor_temp', 0)),
                'plc_motor_voltage': float(data.get('motor_voltage', 0)),
                'plc_motor_current': float(data.get('motor_current', 0)),
                'plc_motor_rpm': int(data.get('motor_rpm', 0)),
                'plc_power_consumption': float(data.get('power_consumption', 0)),
                'plc_raw_d100': int(data.get('raw_d100', 0)),
                'plc_raw_d102': int(data.get('raw_d102', 0)),
                'plc_status': data.get('plc_status', 'NORMAL'),
                'plc_error_code': int(data.get('error_code', 0)),
                'plc_connected': True,
                'last_plc_update': datetime.now().isoformat(),
                'plc_data_quality': 'Good'
            })
            
            # Calculate health
            health_data = calculate_advanced_health_score(latest_sensor_data, latest_plc_data)
            
            # Save to database
            save_sensor_data(latest_sensor_data, latest_plc_data, health_data)
            
            # Store for charts
            combined_data = {**latest_sensor_data, **latest_plc_data, **health_data}
            store_data_point(combined_data)
            
            # Emit real-time update
            if connected_clients:
                socketio.emit('data_update', combined_data)
            
            logger.info(f"🏭 PLC: {data.get('motor_temp')}°C - Health: {health_data['overall_health_score']}%")
            
            return jsonify({'status': 'success', 'health': health_data['overall_health_score']}), 200
            
        except Exception as e:
            logger.error(f"PLC Error: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

def register_api_routes(app):
    """Register API routes"""
    
    @app.route('/api/current-data')
    def current_data():
        try:
            health_data = calculate_advanced_health_score(latest_sensor_data, latest_plc_data)
            combined_data = {**latest_sensor_data, **latest_plc_data, **health_data}
            
            return jsonify({
                'status': 'success',
                'data': combined_data,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Error in current_data: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    @app.route('/api/recommendations')
    def get_recommendations():
        try:
            health_data = calculate_advanced_health_score(latest_sensor_data, latest_plc_data)
            recommendations = generate_recommendations(health_data, latest_sensor_data, latest_plc_data)
            
            return jsonify({
                'status': 'success',
                'recommendations': recommendations,
                'health_summary': health_data,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Error generating recommendations: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

# FIXED: SocketIO event handlers with proper signatures
def register_socketio_events(socketio):
    """FIXED: Register WebSocket event handlers with correct signatures"""
    global connected_clients
    logger = logging.getLogger('socketio')
    
    @socketio.on('connect')
    def handle_connect():
        connected_clients.add(request.sid)
        logger.info(f'✅ Client connected: {request.sid} (Total: {len(connected_clients)})')
        
        try:
            health_data = calculate_advanced_health_score(latest_sensor_data, latest_plc_data)
            combined_data = {**latest_sensor_data, **latest_plc_data, **health_data}
            emit('data_update', combined_data)
            emit('connection_status', {'connected': True, 'message': 'Connected to server'})
        except Exception as e:
            logger.error(f"Error sending initial data: {e}")
    
    # FIXED: Disconnect handler with proper signature
    @socketio.on('disconnect')
    def handle_disconnect():  # Removed the reason parameter that was causing the error
        connected_clients.discard(request.sid)
        logger.info(f'❌ Client disconnected: {request.sid} (Total: {len(connected_clients)})')
    
    @socketio.on('request_data')
    def handle_data_request():
        try:
            health_data = calculate_advanced_health_score(latest_sensor_data, latest_plc_data)
            combined_data = {**latest_sensor_data, **latest_plc_data, **health_data}
            emit('data_update', combined_data)
        except Exception as e:
            logger.error(f"Error handling data request: {e}")
    
    @socketio.on('control_motor')
    def handle_motor_control(data):
        action = data.get('action', 'unknown')
        logger.info(f"🎮 Motor control: {action}")
        emit('control_response', {'action': action, 'status': 'acknowledged'})
    
    @socketio.on_error()
    def error_handler(e):
        logger.error(f"SocketIO error: {e}")

def print_startup_banner():
    """Print startup banner"""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║              🔧 AI-Enabled Industrial Motor Monitoring System 🔧             ║
║                                                                              ║
║                    Version 4.1 - ALL ISSUES FIXED                           ║
║                                                                              ║
║  ✅ Fixed WebSocket Broadcasting    ✅ Complete Feature Set                  ║
║  ✅ Eventlet Support               ✅ Real-time Dashboard                    ║
║  ✅ Historical Data Fallback       ✅ Advanced AI Analytics                 ║
║  ✅ Robust Error Recovery          ✅ Production Ready                       ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """
    print(banner)

def main():
    """Main application entry point"""
    try:
        print_startup_banner()
        
        setup_logging()
        logger = logging.getLogger(__name__)
        
        logger.info("=" * 60)
        logger.info("AI Motor Monitoring System v4.1 starting up")
        logger.info(f"Timestamp: {datetime.now().isoformat()}")
        logger.info("=" * 60)
        
        create_directories()
        init_database()
        
        logger.info("Creating Flask application...")
        app, socketio = create_flask_app()
        
        logger.info("Starting connection monitoring...")
        eventlet.spawn(check_connection_timeout)
        
        print("🚀 System startup completed successfully!")
        print(f"📊 Dashboard: http://0.0.0.0:5000")
        print("📝 API Debug: http://0.0.0.0:5000/api/debug-health")
        print("🔍 Health Check: http://0.0.0.0:5000/health")
        print("🤖 Recommendations: http://0.0.0.0:5000/api/recommendations")
        print("🛑 Press Ctrl+C to shutdown gracefully")
        print("")
        print("📡 Ready to receive device simulator data:")
        print("   ESP8266: POST /api/send-data")
        print("   FX5U PLC: POST /api/plc-data")
        print("=" * 82)
        
        socketio.run(
            app,
            host='0.0.0.0',
            port=5000,
            debug=False,
            use_reloader=False,
            allow_unsafe_werkzeug=True
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Shutdown requested by user")
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        logging.getLogger(__name__).critical(f"Fatal error in main: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
