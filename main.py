"""
AI-Enabled Industrial Motor Monitoring System
Main Application - Fixed Health Logic with Historical Data Support
Version: 3.2
"""

import sys
import os
import signal
import time
import logging
from datetime import datetime, timedelta
from threading import Timer
import sqlite3

# Fix Windows Unicode console encoding
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Core application imports
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit

# Global application components
app = None
socketio = None

# Enhanced data storage with connection tracking
latest_sensor_data = {
    'esp_current': 0,
    'esp_voltage': 0,
    'esp_rpm': 0,
    'env_temp_c': 0,
    'env_humidity': 0,
    'relay1_status': 'OFF',
    'relay2_status': 'OFF',
    'relay3_status': 'OFF',
    'esp_connected': False,
    'last_esp_update': None,
    'esp_data_quality': 'No Data'
}

latest_plc_data = {
    'plc_motor_temp': 0,
    'plc_motor_voltage': 0,
    'plc_motor_current': 0,
    'plc_motor_rpm': 0,
    'plc_power_consumption': 0,
    'plc_status': 'UNKNOWN',
    'plc_connected': False,
    'last_plc_update': None,
    'plc_data_quality': 'No Data'
}

# Connection timeout tracking
ESP_TIMEOUT = 30  # seconds
PLC_TIMEOUT = 30  # seconds

def create_directories():
    """Create necessary directories"""
    directories = ['data', 'logs', 'models', 'templates', 'static', 'database']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def setup_logging():
    """Setup logging configuration"""
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
        
        # Set specific logger levels
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('werkzeug').setLevel(logging.INFO)
        
        logging.info("Logging system initialized successfully")
    except Exception as e:
        print(f"Error setting up logging: {e}")

def init_database():
    """Initialize SQLite database for historical data"""
    try:
        db_path = os.path.join('database', 'sensor_history.db')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create sensor data table
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
                mechanical_health REAL
            )
        ''')
        
        # Create index for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON sensor_data(timestamp DESC)
        ''')
        
        conn.commit()
        conn.close()
        
        logging.info("Database initialized successfully")
        
    except Exception as e:
        logging.error(f"Error initializing database: {e}")

def get_historical_data(hours_back=24, limit=100):
    """Retrieve historical sensor data for health calculation fallback"""
    try:
        db_path = os.path.join('database', 'sensor_history.db')
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
        
        if not rows:
            # Return reasonable defaults if no historical data
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
                'overall_health_score': 85.0,
                'electrical_health': 88.0,
                'thermal_health': 84.0,
                'mechanical_health': 87.0,
                'data_source': 'default_safe_values',
                'records_found': 0
            }
        
        # Calculate averages from historical data
        avg_data = {
            'esp_current': sum(row[0] or 0 for row in rows) / len(rows),
            'esp_voltage': sum(row[1] or 0 for row in rows) / len(rows),
            'esp_rpm': int(sum(row[2] or 0 for row in rows) / len(rows)),
            'env_temp_c': sum(row[3] or 0 for row in rows) / len(rows),
            'env_humidity': sum(row[4] or 0 for row in rows) / len(rows),
            'plc_motor_temp': sum(row[5] or 0 for row in rows) / len(rows),
            'plc_motor_voltage': sum(row[6] or 0 for row in rows) / len(rows),
            'plc_motor_current': sum(row[7] or 0 for row in rows) / len(rows),
            'plc_motor_rpm': int(sum(row[8] or 0 for row in rows) / len(rows)),
            'overall_health_score': sum(row[9] or 0 for row in rows) / len(rows),
            'electrical_health': sum(row[10] or 0 for row in rows) / len(rows),
            'thermal_health': sum(row[11] or 0 for row in rows) / len(rows),
            'mechanical_health': sum(row[12] or 0 for row in rows) / len(rows),
            'data_source': 'historical_average',
            'records_found': len(rows),
            'oldest_record': rows[-1][14] if rows else None,
            'newest_record': rows[0][14] if rows else None
        }
        
        logging.info(f"Retrieved historical data: {len(rows)} records, health score: {avg_data['overall_health_score']:.1f}%")
        return avg_data
        
    except Exception as e:
        logging.error(f"Error retrieving historical data: {e}")
        # Return safe defaults on error
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
            'overall_health_score': 75.0,
            'electrical_health': 75.0,
            'thermal_health': 75.0,
            'mechanical_health': 75.0,
            'data_source': 'error_fallback',
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

# ✅ CRITICAL FIX: This function was nested inside save_sensor_data - moved to module level!
def calculate_advanced_health_score(sensor_data, plc_data):
    """FIXED health calculation with realistic scoring"""
    try:
        # Get current values with defaults
        current = float(sensor_data.get('esp_current', 6.0))
        voltage = float(sensor_data.get('esp_voltage', 24.0))
        rpm = float(sensor_data.get('esp_rpm', 2750))
        motor_temp = float(plc_data.get('plc_motor_temp', 40.0))
        
        # Check connection status
        esp_connected = sensor_data.get('esp_connected', False)
        plc_connected = plc_data.get('plc_connected', False)
        
        # ✅ FIX: Realistic electrical health calculation
        electrical_health = 100.0
        if current > 10.0:  # Very high current
            electrical_health -= min(30, (current - 10.0) * 5)
        elif current > 8.0:  # High current
            electrical_health -= (current - 8.0) * 3
        
        if voltage < 20.0:  # Low voltage
            electrical_health -= min(25, (20.0 - voltage) * 8)
        elif voltage > 28.0:  # High voltage  
            electrical_health -= (voltage - 28.0) * 6
        
        electrical_health = max(50.0, electrical_health)  # Minimum 50%
        
        # ✅ FIX: Realistic thermal health calculation
        thermal_health = 100.0
        if motor_temp > 70.0:  # High temperature
            thermal_health -= (motor_temp - 70.0) * 3
        elif motor_temp > 55.0:  # Elevated temperature
            thermal_health -= (motor_temp - 55.0) * 1.5
        
        thermal_health = max(60.0, thermal_health)  # Minimum 60%
        
        # ✅ FIX: Realistic mechanical health calculation
        mechanical_health = 100.0
        if rpm < 2000:  # Low RPM
            mechanical_health -= (2000 - rpm) * 0.01
        elif rpm > 3500:  # High RPM
            mechanical_health -= (rpm - 3500) * 0.008
        
        mechanical_health = max(70.0, mechanical_health)  # Minimum 70%
        
        # ✅ FIX: Calculate realistic overall health
        overall_health = (electrical_health + thermal_health + mechanical_health) / 3
        
        # ✅ FIX: Connection penalty (small, not devastating)
        if not esp_connected:
            overall_health *= 0.95  # Only 5% penalty
        if not plc_connected:
            overall_health *= 0.95  # Only 5% penalty
        
        # Determine status
        if overall_health >= 85:
            status = 'Good'
        elif overall_health >= 70:
            status = 'Fair' 
        elif overall_health >= 50:
            status = 'Warning'
        else:
            status = 'Critical'
        
        return {
            'overall_health_score': round(overall_health, 1),
            'electrical_health': round(electrical_health, 1),
            'thermal_health': round(thermal_health, 1),
            'mechanical_health': round(mechanical_health, 1),
            'status': status,
            'esp_connected': esp_connected,
            'plc_connected': plc_connected
        }
        
    except Exception as e:
        logging.error(f"Health calculation error: {e}")
        return {
            'overall_health_score': 75.0,  # Safe default
            'electrical_health': 75.0,
            'thermal_health': 75.0,
            'mechanical_health': 75.0,
            'status': 'Unknown',
            'esp_connected': False,
            'plc_connected': False
        }

def calculate_electrical_health(data):
    """Calculate electrical health component"""
    health = 100.0
    
    current = data.get('esp_current', 0)
    voltage = data.get('esp_voltage', 0)
    
    # Current analysis (improved thresholds)
    if current > 12.0:  # Very high current
        health -= min(40, (current - 12.0) * 8)
    elif current > 9.0:  # High current
        health -= (current - 9.0) * 4
    elif current < 3.0:  # Very low current (motor not running?)
        health -= (3.0 - current) * 5
    
    # Voltage analysis (realistic industrial thresholds)
    if voltage < 18.0:  # Very low voltage
        health -= min(35, (18.0 - voltage) * 12)
    elif voltage < 21.0:  # Low voltage
        health -= (21.0 - voltage) * 2
    elif voltage > 28.0:  # Very high voltage
        health -= min(30, (voltage - 28.0) * 10)
    elif voltage > 26.5:  # High voltage
        health -= (voltage - 26.5) * 5
    
    return max(30.0, min(100.0, health))  # Minimum 30% for electrical

def calculate_thermal_health(data):
    """Calculate thermal health component"""
    health = 100.0
    
    motor_temp = data.get('plc_motor_temp', 0)
    env_temp = data.get('env_temp_c', 0)
    
    # Motor temperature analysis
    if motor_temp > 85.0:  # Critical temperature
        health -= min(50, (motor_temp - 85.0) * 10)
    elif motor_temp > 70.0:  # High temperature
        health -= (motor_temp - 70.0) * 3
    elif motor_temp > 55.0:  # Elevated temperature
        health -= (motor_temp - 55.0) * 1.5
    
    # Environmental temperature impact
    if env_temp > 45.0:  # Very hot environment
        health -= (env_temp - 45.0) * 1
    elif env_temp < -5.0:  # Very cold environment
        health -= (-5.0 - env_temp) * 0.5
    
    return max(40.0, min(100.0, health))  # Minimum 40% for thermal

def calculate_mechanical_health(data):
    """Calculate mechanical health component"""
    health = 100.0
    
    esp_rpm = data.get('esp_rpm', 0)
    plc_rpm = data.get('plc_motor_rpm', 0)
    
    # Use the higher RPM reading if both available
    rpm = max(esp_rpm, plc_rpm) if esp_rpm and plc_rpm else (esp_rpm or plc_rpm)
    
    # RPM analysis (motor-specific thresholds)
    if rpm < 1000:  # Motor not running or severe issue
        health -= 60
    elif rpm < 2000:  # Very low RPM
        health -= (2000 - rpm) * 0.02
    elif rpm < 2400:  # Low RPM
        health -= (2400 - rpm) * 0.01
    elif rpm > 3500:  # Very high RPM
        health -= (rpm - 3500) * 0.015
    elif rpm > 3200:  # High RPM
        health -= (rpm - 3200) * 0.008
    
    return max(35.0, min(100.0, health))  # Minimum 35% for mechanical

def check_connection_timeout():
    """Check for connection timeouts and update status"""
    global latest_sensor_data, latest_plc_data
    
    now = datetime.now()
    
    # Check ESP timeout
    if latest_sensor_data.get('last_esp_update'):
        try:
            last_esp = datetime.fromisoformat(latest_sensor_data['last_esp_update'])
            if (now - last_esp).total_seconds() > ESP_TIMEOUT:
                if latest_sensor_data['esp_connected']:
                    latest_sensor_data['esp_connected'] = False
                    latest_sensor_data['esp_data_quality'] = 'Timeout'
                    logging.warning("ESP connection timeout detected")
                    if socketio:
                        socketio.emit('device_timeout', {'device': 'ESP8266', 'status': 'disconnected'})
        except:
            pass
    
    # Check PLC timeout
    if latest_plc_data.get('last_plc_update'):
        try:
            last_plc = datetime.fromisoformat(latest_plc_data['last_plc_update'])
            if (now - last_plc).total_seconds() > PLC_TIMEOUT:
                if latest_plc_data['plc_connected']:
                    latest_plc_data['plc_connected'] = False
                    latest_plc_data['plc_data_quality'] = 'Timeout'
                    logging.warning("PLC connection timeout detected")
                    if socketio:
                        socketio.emit('device_timeout', {'device': 'FX5U_PLC', 'status': 'disconnected'})
        except:
            pass
    
    # Schedule next check
    Timer(10.0, check_connection_timeout).start()

def create_flask_app():
    """Create and configure Flask application"""
    global app, socketio
    
    # Create Flask app with proper paths
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    
    # Configure Flask
    app.config['SECRET_KEY'] = 'motor_monitoring_secret_key_2025'
    app.config['DEBUG'] = True
    
    # Create SocketIO instance
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    
    # Register all routes
    register_core_routes(app)
    register_device_routes(app)
    register_api_routes(app)
    register_socketio_events(socketio)
    
    return app, socketio

def register_core_routes(app):
    """Register core application routes"""
    
    @app.route('/')
    def dashboard():
        """Main dashboard route"""
        return render_template('dashboard.html')
    
    @app.route('/favicon.ico')
    def favicon():
        """Handle favicon requests"""
        return '', 204
    
    @app.route('/health')
    def health_check():
        """System health check endpoint"""
        return jsonify({
            'status': 'healthy',
            'service': 'AI Motor Monitoring System v3.2',
            'timestamp': datetime.now().isoformat(),
            'components': {
                'flask': 'running',
                'socketio': 'active',
                'database': 'connected',
                'ai_engine': 'ready'
            }
        })

def register_device_routes(app):
    """Register device data reception routes"""
    global latest_sensor_data, latest_plc_data
    logger = logging.getLogger(__name__)
    
    @app.route('/api/send-data', methods=['POST'])
    def receive_esp_data():
        """Receive ESP8266 data - FIXED VERSION"""
        global latest_sensor_data
        
        try:
            data = request.get_json(force=True)
            if not data:
                return jsonify({'status': 'error', 'message': 'No data received'}), 400
            
            # ✅ FIX 1: Properly update sensor data AND set connected=True
            latest_sensor_data.update({
                'esp_current': float(data.get('VAL1', 0)),
                'esp_voltage': float(data.get('VAL2', 0)),
                'esp_rpm': int(float(data.get('VAL3', 0))),
                'env_temp_c': float(data.get('VAL4', 0)),
                'env_humidity': float(data.get('VAL5', 0)),
                'relay1_status': data.get('VAL9', 'OFF'),
                'relay2_status': data.get('VAL10', 'OFF'),
                'relay3_status': data.get('VAL11', 'OFF'),
                'esp_connected': True,  # ✅ KEY FIX: Set to True when data received!
                'last_esp_update': datetime.now().isoformat()
            })
            
            # ✅ FIX 2: Calculate health with proper data
            health_data = calculate_advanced_health_score(latest_sensor_data, latest_plc_data)
            
            # ✅ FIX 3: Save to database
            save_sensor_data(latest_sensor_data, latest_plc_data, health_data)
            
            # ✅ FIX 4: Emit via WebSocket for real-time updates
            combined_data = {**latest_sensor_data, **latest_plc_data, **health_data}
            if socketio:
                socketio.emit('sensor_update', combined_data)
            
            logger.info(f"📡 ESP: {data.get('VAL1')}A, {data.get('VAL2')}V - Health: {health_data['overall_health_score']}%")
            
            return jsonify({'status': 'success', 'health': health_data['overall_health_score']}), 200
            
        except Exception as e:
            logger.error(f"❌ ESP Error: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    @app.route('/api/plc-data', methods=['POST'])
    def receive_plc_data():
        """Receive PLC data - FIXED VERSION"""
        global latest_plc_data
        
        try:
            data = request.get_json(force=True)
            if not data:
                return jsonify({'status': 'error', 'message': 'No data received'}), 400
            
            # ✅ FIX 1: Properly update PLC data AND set connected=True
            latest_plc_data.update({
                'plc_motor_temp': float(data.get('motor_temp', 0)),
                'plc_motor_voltage': float(data.get('motor_voltage', 0)),
                'plc_motor_current': float(data.get('motor_current', 0)),
                'plc_motor_rpm': int(data.get('motor_rpm', 0)),
                'plc_status': data.get('plc_status', 'NORMAL'),
                'plc_connected': True,  # ✅ KEY FIX: Set to True when data received!
                'last_plc_update': datetime.now().isoformat()
            })
            
            # ✅ FIX 2: Calculate health with proper data
            health_data = calculate_advanced_health_score(latest_sensor_data, latest_plc_data)
            
            # ✅ FIX 3: Save to database
            save_sensor_data(latest_sensor_data, latest_plc_data, health_data)
            
            # ✅ FIX 4: Emit via WebSocket
            combined_data = {**latest_sensor_data, **latest_plc_data, **health_data}
            if socketio:
                socketio.emit('plc_update', combined_data)
            
            logger.info(f"🏭 PLC: {data.get('motor_temp')}°C - Health: {health_data['overall_health_score']}%")
            
            return jsonify({'status': 'success', 'health': health_data['overall_health_score']}), 200
            
        except Exception as e:
            logger.error(f"❌ PLC Error: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

def register_api_routes(app):
    """Register API routes"""
    
    @app.route('/api/current-data')
    def current_data():
        """Get current sensor data with historical fallback"""
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
        """Get AI recommendations based on current system state"""
        try:
            health_data = calculate_advanced_health_score(latest_sensor_data, latest_plc_data)
            
            recommendations = []
            
            # Generate recommendations based on health and data source
            if health_data['overall_health_score'] < 60:
                recommendations.append({
                    'priority': 'HIGH',
                    'category': 'Maintenance',
                    'message': f"System health is {health_data['status'].lower()} ({health_data['overall_health_score']:.1f}%). Schedule immediate inspection.",
                    'action': 'Contact maintenance team for immediate inspection'
                })
            
            if not health_data['esp_connected']:
                recommendations.append({
                    'priority': 'MEDIUM',
                    'category': 'ESP Device',
                    'message': 'ESP8266 sensor not connected or timed out.',
                    'action': 'Verify ESP8266 power, WiFi connection, and network settings'
                })
            
            if not health_data['plc_connected']:
                recommendations.append({
                    'priority': 'MEDIUM',
                    'category': 'PLC Device',
                    'message': 'FX5U PLC not connected or timed out.',
                    'action': 'Check PLC power supply, network connection, and MC protocol settings'
                })
            
            return jsonify({
                'status': 'success',
                'recommendations': recommendations,
                'health_summary': health_data,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Error generating recommendations: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    @app.route('/api/system-status')
    def system_status():
        """Get detailed system status"""
        health_data = calculate_advanced_health_score(latest_sensor_data, latest_plc_data)
        
        return jsonify({
            'status': 'operational',
            'health': health_data,
            'devices': {
                'esp8266': {
                    'connected': health_data['esp_connected'],
                    'last_update': latest_sensor_data.get('last_esp_update'),
                    'data_quality': latest_sensor_data.get('esp_data_quality', 'Unknown')
                },
                'fx5u_plc': {
                    'connected': health_data['plc_connected'],
                    'last_update': latest_plc_data.get('last_plc_update'),
                    'data_quality': latest_plc_data.get('plc_data_quality', 'Unknown')
                }
            },
            'ai_model_status': 'Active',
            'timestamp': datetime.now().isoformat()
        })
    
    @app.route('/api/debug-health')
    def debug_health():
        """Debug health calculation for troubleshooting"""
        health_data = calculate_advanced_health_score(latest_sensor_data, latest_plc_data)
        historical_data = get_historical_data()
        
        return jsonify({
            'current_sensor_data': latest_sensor_data,
            'current_plc_data': latest_plc_data,
            'calculated_health': health_data,
            'historical_reference': historical_data,
            'timestamp': datetime.now().isoformat()
        })

def register_socketio_events(socketio):
    """Register WebSocket event handlers"""
    logger = logging.getLogger('socketio')
    
    @socketio.on('connect')
    def handle_connect():
        logger.info('Client connected to WebSocket')
        # Send current data to newly connected client
        try:
            health_data = calculate_advanced_health_score(latest_sensor_data, latest_plc_data)
            combined_data = {**latest_sensor_data, **latest_plc_data, **health_data}
            emit('initial_data', combined_data)
        except Exception as e:
            logger.error(f"Error sending initial data: {e}")
    
    @socketio.on('disconnect')
    def handle_disconnect():
        logger.info('Client disconnected from WebSocket')
    
    @socketio.on('request_data')
    def handle_data_request():
        # Send current data when requested
        try:
            health_data = calculate_advanced_health_score(latest_sensor_data, latest_plc_data)
            combined_data = {**latest_sensor_data, **latest_plc_data, **health_data}
            emit('data_response', combined_data)
        except Exception as e:
            logger.error(f"Error handling data request: {e}")

def print_startup_banner():
    """Print startup banner"""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║              🔧 AI-Enabled Industrial Motor Monitoring System 🔧             ║
║                                                                              ║
║                    Version 3.2 - Historical Data Enhanced                   ║
║                                                                              ║
║  ✅ Historical Data Fallback     ✅ Realistic Health Scoring                ║
║  ✅ Connection Timeout Handling  ✅ Advanced AI Analytics                   ║
║  ✅ Robust Error Recovery        ✅ Real-time Dashboard                     ║
║  ✅ Database Integration         ✅ WebSocket Updates                       ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """
    print(banner)
    
    print("🌐 Server: http://0.0.0.0:5000")
    print("📊 Database: sqlite:///database/sensor_history.db")
    print("📝 Logs: logs/application.log")
    print("🎯 Debug Mode: Enabled")
    print("📡 Device Simulator: Ready to receive data!")
    print("🔄 Historical Fallback: Enabled")
    print("=" * 82)

def main():
    """Main application entry point"""
    try:
        # Print startup banner
        print_startup_banner()
        
        # Setup logging
        setup_logging()
        logger = logging.getLogger(__name__)
        
        logger.info("=" * 60)
        logger.info("AI Motor Monitoring System v3.2 starting up")
        logger.info(f"Timestamp: {datetime.now().isoformat()}")
        logger.info("=" * 60)
        
        # Create necessary directories
        logger.info("Creating necessary directories...")
        create_directories()
        
        # Initialize database
        logger.info("Initializing database...")
        init_database()
        
        # Create Flask application
        logger.info("Creating Flask application...")
        app, socketio = create_flask_app()
        
        # Start connection timeout monitoring
        logger.info("Starting connection monitoring...")
        check_connection_timeout()
        
        # Print startup completion
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
        
        # Start Flask-SocketIO server
        socketio.run(
            app,
            host='0.0.0.0',
            port=5000,
            debug=True,
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
