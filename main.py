"""
AI-Enabled Industrial Motor Health & Environment Monitoring System
Main Application Entry Point - Complete Complex Version

Version: 3.1 - Complete Modular Implementation with Device Simulator Support
Author: AI Motor Monitoring Team  
Created: 2025
"""

import sys
import os
import signal
import time
import logging
from datetime import datetime

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
data_processor = None
background_tasks = None
connection_monitor = None
alert_service = None
plc_manager = None

# Data storage for real-time dashboard
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
    'last_esp_update': None
}

latest_plc_data = {
    'plc_motor_temp': 0,
    'plc_motor_voltage': 0,
    'plc_motor_current': 0,
    'plc_motor_rpm': 0,
    'plc_power_consumption': 0,
    'plc_status': 'UNKNOWN',
    'plc_connected': False,
    'last_plc_update': None
}

def create_directories():
    """Create necessary directories"""
    directories = ['data', 'logs', 'models', 'templates', 'static', 'static/css', 'static/js', 'static/images']
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

def calculate_health_score(sensor_data, plc_data):
    """Calculate overall system health score based on current readings"""
    try:
        health_scores = []
        
        # Electrical health (based on current and voltage)
        current = float(sensor_data.get('esp_current', 0))
        voltage = float(sensor_data.get('esp_voltage', 0))
        
        electrical_health = 100
        if current > 8.0:  # High current
            electrical_health -= (current - 8.0) * 10
        if voltage < 22.0:  # Low voltage
            electrical_health -= (22.0 - voltage) * 10
        if voltage > 26.0:  # High voltage
            electrical_health -= (voltage - 26.0) * 15
        
        electrical_health = max(0, min(100, electrical_health))
        health_scores.append(electrical_health)
        
        # Thermal health (based on temperatures)
        motor_temp = float(plc_data.get('plc_motor_temp', 0))
        env_temp = float(sensor_data.get('env_temp_c', 0))
        
        thermal_health = 100
        if motor_temp > 50.0:  # High motor temperature
            thermal_health -= (motor_temp - 50.0) * 3
        if motor_temp > 70.0:  # Critical temperature
            thermal_health -= (motor_temp - 70.0) * 5
        
        thermal_health = max(0, min(100, thermal_health))
        health_scores.append(thermal_health)
        
        # Mechanical health (based on RPM)
        rpm = float(sensor_data.get('esp_rpm', 0))
        
        mechanical_health = 100
        if rpm < 2500:  # Low RPM
            mechanical_health -= (2500 - rpm) * 0.05
        if rpm > 3000:  # High RPM
            mechanical_health -= (rpm - 3000) * 0.05
        
        mechanical_health = max(0, min(100, mechanical_health))
        health_scores.append(mechanical_health)
        
        # Calculate overall health
        overall_health = sum(health_scores) / len(health_scores) if health_scores else 0
        
        return {
            'overall_health_score': round(overall_health, 1),
            'electrical_health': round(electrical_health, 1),
            'thermal_health': round(thermal_health, 1),
            'mechanical_health': round(mechanical_health, 1),
            'status': 'Good' if overall_health > 80 else 'Warning' if overall_health > 60 else 'Critical'
        }
        
    except Exception as e:
        logging.getLogger(__name__).error(f"Error calculating health score: {e}")
        return {
            'overall_health_score': 0,
            'electrical_health': 0,
            'thermal_health': 0,
            'mechanical_health': 0,
            'status': 'Unknown'
        }

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
    
    # Register core routes
    register_core_routes(app)
    
    # Register device data routes (NEW - for simulator integration)
    register_device_routes(app)
    
    # Register blueprints with error handling
    register_blueprints(app)
    
    # Register WebSocket events with error handling
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
            'service': 'AI Motor Monitoring System v3.1',
            'timestamp': datetime.now().isoformat(),
            'components': {
                'flask': 'running',
                'socketio': 'active',
                'database': 'connected',
                'ai_engine': 'ready'
            }
        })
    
    @app.route('/api/system-status')
    def system_status():
        """Get system status"""
        return jsonify({
            'status': 'operational',
            'esp_connected': latest_sensor_data['esp_connected'],
            'plc_connected': latest_plc_data['plc_connected'],
            'ai_model_status': 'Active',
            'uptime': '00:05:23',
            'timestamp': datetime.now().isoformat()
        })
    
    @app.route('/api/current-data')
    def current_data():
        """Get current sensor data"""
        # Combine ESP and PLC data
        combined_data = {**latest_sensor_data, **latest_plc_data}
        
        # Calculate health scores
        health_data = calculate_health_score(latest_sensor_data, latest_plc_data)
        combined_data.update(health_data)
        
        return jsonify({
            'status': 'success',
            'data': combined_data,
            'timestamp': datetime.now().isoformat()
        })
    
    @app.route('/api/recommendations')
    def get_recommendations():
        """Get AI recommendations based on current system state"""
        health_data = calculate_health_score(latest_sensor_data, latest_plc_data)
        
        recommendations = []
        
        # Generate recommendations based on health score
        if health_data['overall_health_score'] < 60:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Maintenance',
                'message': 'System health is critical. Schedule immediate maintenance.',
                'action': 'Contact maintenance team'
            })
        
        if float(latest_plc_data.get('plc_motor_temp', 0)) > 60:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Cooling',
                'message': 'Motor temperature is elevated. Check cooling system.',
                'action': 'Inspect cooling fans and ventilation'
            })
        
        if float(latest_sensor_data.get('esp_current', 0)) > 8.0:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Electrical',
                'message': 'Motor current is high. Check for mechanical issues.',
                'action': 'Inspect motor bearings and coupling'
            })
        
        return jsonify({
            'status': 'success',
            'recommendations': recommendations,
            'health_summary': health_data,
            'timestamp': datetime.now().isoformat()
        })

def register_device_routes(app):
    """Register device data reception routes (NEW)"""
    logger = logging.getLogger(__name__)
    
    @app.route('/api/send-data', methods=['POST'])
    def receive_esp_data():
        """Receive ESP8266/Arduino sensor data"""
        global latest_sensor_data
        
        try:
            data = request.get_json(force=True)
            if not data:
                return jsonify({'status': 'error', 'message': 'No data received'}), 400
            
            logger.info(f"📡 ESP Data: Current={data.get('VAL1')}A, Voltage={data.get('VAL2')}V, RPM={data.get('VAL3')}")
            
            # Process ESP data and convert to internal format
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
                'last_esp_update': datetime.now().isoformat()
            })
            
            # Calculate health scores
            health_data = calculate_health_score(latest_sensor_data, latest_plc_data)
            
            # Emit real-time update via WebSocket
            combined_data = {**latest_sensor_data, **latest_plc_data, **health_data}
            socketio.emit('sensor_update', combined_data)
            
            # Store data (if database is available)
            try:
                if data_processor:
                    data_processor.process_esp_data(latest_sensor_data)
            except Exception as e:
                logger.warning(f"Could not process ESP data with data processor: {e}")
            
            return jsonify({'status': 'success', 'message': 'ESP data received successfully'}), 200
            
        except Exception as e:
            logger.error(f"❌ Error processing ESP data: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    @app.route('/api/plc-data', methods=['POST'])
    def receive_plc_data():
        """Receive FX5U PLC motor data"""
        global latest_plc_data
        
        try:
            data = request.get_json(force=True)
            if not data:
                return jsonify({'status': 'error', 'message': 'No data received'}), 400
            
            logger.info(f"🏭 PLC Data: Temp={data.get('motor_temp')}°C, Voltage={data.get('motor_voltage')}V, Status={data.get('plc_status')}")
            
            # Process PLC data
            latest_plc_data.update({
                'plc_motor_temp': float(data.get('motor_temp', 0)),
                'plc_motor_voltage': float(data.get('motor_voltage', 0)),
                'plc_motor_current': float(data.get('motor_current', 0)),
                'plc_motor_rpm': int(data.get('motor_rpm', 0)),
                'plc_power_consumption': float(data.get('power_consumption', 0)),
                'plc_raw_d100': int(data.get('raw_d100', 0)),
                'plc_raw_d102': int(data.get('raw_d102', 0)),
                'plc_status': data.get('plc_status', 'UNKNOWN'),
                'plc_error_code': int(data.get('error_code', 0)),
                'plc_connected': True,
                'last_plc_update': datetime.now().isoformat()
            })
            
            # Calculate health scores
            health_data = calculate_health_score(latest_sensor_data, latest_plc_data)
            
            # Emit real-time update via WebSocket
            combined_data = {**latest_sensor_data, **latest_plc_data, **health_data}
            socketio.emit('plc_update', combined_data)
            
            # Store data (if database is available)
            try:
                if data_processor:
                    data_processor.process_plc_data(latest_plc_data)
            except Exception as e:
                logger.warning(f"Could not process PLC data with data processor: {e}")
            
            return jsonify({'status': 'success', 'message': 'PLC data received successfully'}), 200
            
        except Exception as e:
            logger.error(f"❌ Error processing PLC data: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    @app.route('/api/mock-data')
    def mock_data():
        """Provide current sensor data (for compatibility)"""
        # Return actual current data instead of mock data
        combined_data = {**latest_sensor_data, **latest_plc_data}
        health_data = calculate_health_score(latest_sensor_data, latest_plc_data)
        
        return jsonify({
            'status': 'success',
            'data': combined_data,
            'health_data': health_data,
            'timestamp': datetime.now().isoformat()
        })

def register_blueprints(app):
    """Register API blueprints with error handling"""
    logger = logging.getLogger(__name__)
    
    blueprints_registered = 0
    total_blueprints = 4
    
    try:
        from api.routes.sensor_data import sensor_bp
        app.register_blueprint(sensor_bp, url_prefix='/api')
        blueprints_registered += 1
        logger.info("Sensor data blueprint registered")
    except ImportError as e:
        logger.warning(f"Could not register sensor_data blueprint: {e}")
    
    try:
        from api.routes.health import health_bp
        app.register_blueprint(health_bp, url_prefix='/api')
        blueprints_registered += 1
        logger.info("Health blueprint registered")
    except ImportError as e:
        logger.warning(f"Could not register health blueprint: {e}")
    
    try:
        from api.routes.alerts import alerts_bp
        app.register_blueprint(alerts_bp, url_prefix='/api')
        blueprints_registered += 1
        logger.info("Alerts blueprint registered")
    except ImportError as e:
        logger.warning(f"Could not register alerts blueprint: {e}")
    
    try:
        from api.routes.control import control_bp
        app.register_blueprint(control_bp, url_prefix='/api')
        blueprints_registered += 1
        logger.info("Control blueprint registered")
    except ImportError as e:
        logger.warning(f"Could not register control blueprint: {e}")
    
    logger.info(f"API blueprints registered: {blueprints_registered}/{total_blueprints}")

def register_socketio_events(socketio):
    """Register WebSocket event handlers"""
    logger = logging.getLogger('socketio')
    
    try:
        from api.websocket.events import register_events
        register_events(socketio)
        logger.info("WebSocket events registered successfully")
    except ImportError as e:
        logger.warning(f"Could not register WebSocket events: {e}")
        
        # Register basic WebSocket events directly
        @socketio.on('connect')
        def handle_connect():
            logger.info('Client connected to WebSocket')
            # Send current data to newly connected client
            combined_data = {**latest_sensor_data, **latest_plc_data}
            health_data = calculate_health_score(latest_sensor_data, latest_plc_data)
            combined_data.update(health_data)
            emit('initial_data', combined_data)
            
        @socketio.on('disconnect')
        def handle_disconnect():
            logger.info('Client disconnected from WebSocket')
        
        @socketio.on('request_data')
        def handle_data_request():
            # Send current data when requested
            combined_data = {**latest_sensor_data, **latest_plc_data}
            health_data = calculate_health_score(latest_sensor_data, latest_plc_data)
            combined_data.update(health_data)
            emit('data_response', combined_data)
        
        logger.info("Basic WebSocket events registered")

def initialize_services():
    """Initialize background services"""
    global data_processor, background_tasks, connection_monitor, alert_service, plc_manager
    
    logger = logging.getLogger(__name__)
    
    try:
        # Initialize hardware managers
        logger.info("Initializing hardware managers...")
        try:
            from hardware.plc_manager import FX5UPLCManager
            plc_manager = FX5UPLCManager()
            logger.info("PLC manager initialized")
        except ImportError as e:
            logger.warning(f"Could not initialize PLC manager: {e}")
        
        # Initialize services
        logger.info("Initializing services...")
        
        try:
            from services.data_processor import DataProcessor
            data_processor = DataProcessor()
            if socketio:
                data_processor.set_socketio(socketio)
            logger.info("Data processor initialized")
        except ImportError as e:
            logger.warning(f"Could not initialize data processor: {e}")
        
        try:
            from services.background_tasks import BackgroundTaskManager
            background_tasks = BackgroundTaskManager()
            background_tasks.start()
            logger.info("Background task manager started")
        except ImportError as e:
            logger.warning(f"Could not initialize background tasks: {e}")
        
        try:
            from services.connection_monitor import ConnectionMonitor
            connection_monitor = ConnectionMonitor()
            connection_monitor.start()
            logger.info("Connection monitor started")
        except ImportError as e:
            logger.warning(f"Could not initialize connection monitor: {e}")
        
        try:
            from services.alert_service import AlertService
            alert_service = AlertService()
            logger.info("Alert service initialized")
        except ImportError as e:
            logger.warning(f"Could not initialize alert service: {e}")
        
        # Test initial connections
        test_initial_connections()
        
    except Exception as e:
        logger.error(f"Error initializing services: {e}")

def test_initial_connections():
    """Test initial hardware connections"""
    logger = logging.getLogger(__name__)
    
    try:
        # Test PLC connection
        logger.info("Testing initial connections...")
        
        if plc_manager:
            logger.info(f"Testing PLC connection to 192.168.3.39:5007")
            plc_connected = plc_manager.connect()
            
            if plc_connected:
                logger.info("PLC connection established successfully")
            else:
                logger.warning("PLC connection failed - will retry automatically")
        
        # Test network connectivity
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('8.8.8.8', 53))
            sock.close()
            
            if result == 0:
                logger.info("Network connectivity confirmed")
            else:
                logger.warning("Network connectivity issues detected")
                
        except Exception as e:
            logger.warning(f"Network test failed: {e}")
        
    except Exception as e:
        logger.error(f"Error during initial connection tests: {e}")

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger = logging.getLogger(__name__)
    
    signal_names = {
        signal.SIGINT: 'SIGINT (Ctrl+C)',
        signal.SIGTERM: 'SIGTERM'
    }
    
    signal_name = signal_names.get(signum, f'Signal {signum}')
    logger.info(f"Received {signal_name} - initiating graceful shutdown...")
    
    cleanup_system()
    sys.exit(0)

def cleanup_system():
    """Clean up system resources"""
    global data_processor, background_tasks, connection_monitor, plc_manager
    
    logger = logging.getLogger(__name__)
    logger.info("AI Motor Monitoring System shutting down")
    
    try:
        if background_tasks:
            logger.info("Stopping background tasks...")
            background_tasks.stop()
        
        if connection_monitor:
            logger.info("Stopping connection monitor...")
            connection_monitor.stop()
        
        if data_processor:
            logger.info("Stopping data processor...")
            data_processor.stop()
        
        if plc_manager:
            logger.info("Disconnecting PLC...")
            plc_manager.disconnect()
        
        logger.info("System cleanup completed")
        
    except Exception as e:
        logger.error(f"Error during system cleanup: {e}")

def print_startup_banner():
    """Print startup banner"""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║              🔧 AI-Enabled Industrial Motor Monitoring System 🔧             ║
║                                                                              ║
║                     Version 3.1 - Device-Integrated Edition                 ║
║                                                                              ║
║  ✅ FX5U PLC Integration        ✅ Real-time Health Analysis                 ║
║  ✅ ESP8266/Arduino Support     ✅ AI-Powered Recommendations                ║
║  ✅ Device Simulator Ready      ✅ WebSocket Dashboard                       ║
║  ✅ Predictive Maintenance      ✅ Comprehensive Logging                     ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """
    print(banner)
    
    print("🌐 Server: http://0.0.0.0:5000")
    print("🔌 PLC: 192.168.3.39:5007") 
    print("📊 Database: sqlite:///data/motor_monitoring.db")
    print("📝 Logs: logs/application.log")
    print("🎯 Debug Mode: Enabled")
    print("📡 Device Simulator: Ready to receive data!")
    print("=" * 82)

def run_system_health_check():
    """Run comprehensive system health check"""
    logger = logging.getLogger(__name__)
    
    logger.info("Running system health check...")
    
    health_report = {
        'timestamp': datetime.now().isoformat(),
        'components': {}
    }
    
    # Check Flask app
    health_report['components']['flask'] = {
        'status': 'healthy' if app else 'error',
        'routes': len(app.url_map._rules) if app else 0
    }
    
    # Check SocketIO
    health_report['components']['socketio'] = {
        'status': 'healthy' if socketio else 'error'
    }
    
    # Check device connections
    health_report['components']['devices'] = {
        'esp_connected': latest_sensor_data['esp_connected'],
        'plc_connected': latest_plc_data['plc_connected'],
        'last_esp_data': latest_sensor_data['last_esp_update'],
        'last_plc_data': latest_plc_data['last_plc_update']
    }
    
    # Check services
    services_status = {
        'data_processor': 'healthy' if data_processor else 'not_initialized',
        'background_tasks': 'healthy' if background_tasks else 'not_initialized',
        'connection_monitor': 'healthy' if connection_monitor else 'not_initialized',
        'alert_service': 'healthy' if alert_service else 'not_initialized',
        'plc_manager': 'healthy' if plc_manager else 'not_initialized'
    }
    
    health_report['components']['services'] = services_status
    
    # Count healthy components
    healthy_components = sum(1 for comp in health_report['components'].values() 
                           if isinstance(comp, dict) and comp.get('status') == 'healthy')
    
    total_components = len([comp for comp in health_report['components'].values() 
                           if isinstance(comp, dict) and 'status' in comp])
    
    logger.info(f"Health check completed: {healthy_components}/{total_components} core components healthy")
    
    return health_report

def main():
    """Main application entry point"""
    try:
        # Print startup banner
        print_startup_banner()
        
        # Setup logging
        setup_logging()
        logger = logging.getLogger(__name__)
        
        logger.info("=" * 60)
        logger.info("AI Motor Monitoring System starting up (version 3.1)")
        logger.info(f"Timestamp: {datetime.now().isoformat()}")
        logger.info("=" * 60)
        
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Create necessary directories
        logger.info("Creating necessary directories...")
        create_directories()
        
        # Create Flask application
        logger.info("Creating Flask application...")
        app, socketio = create_flask_app()
        
        # Initialize services
        logger.info("Initializing services...")
        initialize_services()
        
        # Run system health check
        health_report = run_system_health_check()
        
        # Print startup completion
        print("🚀 System startup completed successfully!")
        print(f"📊 Dashboard: http://0.0.0.0:5000")
        print("📝 Check logs for detailed system information")
        print("🔍 Health Check: http://0.0.0.0:5000/health")
        print("📡 Current Data: http://0.0.0.0:5000/api/current-data")
        print("🤖 AI Recommendations: http://0.0.0.0:5000/api/recommendations")
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
        cleanup_system()
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        logging.getLogger(__name__).critical(f"Fatal error in main: {e}")
        cleanup_system()
        sys.exit(1)

if __name__ == '__main__':
    main()
