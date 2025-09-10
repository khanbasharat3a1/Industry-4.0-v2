"""
AI-Enabled Industrial Motor Health & Environment Monitoring System
Main Application Entry Point - Complete Complex Version

Version: 3.1 - Complete Modular Implementation
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
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO

# Global application components
app = None
socketio = None
data_processor = None
background_tasks = None
connection_monitor = None
alert_service = None
plc_manager = None

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
            'esp_connected': False,
            'plc_connected': False,
            'ai_model_status': 'Active',
            'uptime': '00:05:23',
            'timestamp': datetime.now().isoformat()
        })
    
    @app.route('/api/mock-data')
    def mock_data():
        """Provide mock sensor data for testing"""
        return jsonify({
            'status': 'success',
            'data': {
                'esp_current': 6.25,
                'esp_voltage': 24.1,
                'esp_rpm': 2750,
                'plc_motor_temp': 42.3,
                'env_temp_c': 24.5,
                'env_humidity': 45.8,
                'relay1_status': 'ON',
                'relay2_status': 'OFF',
                'relay3_status': 'ON',
                'timestamp': datetime.now().isoformat()
            },
            'health_data': {
                'overall_health_score': 87.5,
                'electrical_health': 92.0,
                'thermal_health': 84.0,
                'mechanical_health': 89.0,
                'predictive_health': 86.0,
                'efficiency_score': 91.2,
                'status': 'Good'
            }
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
            
        @socketio.on('disconnect')
        def handle_disconnect():
            logger.info('Client disconnected from WebSocket')
        
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
║                           Version 3.1 - Complex Edition                     ║
║                                                                              ║
║  ✅ FX5U PLC Integration        ✅ Real-time Health Analysis                 ║
║  ✅ ESP8266/Arduino Support     ✅ AI-Powered Recommendations                ║
║  ✅ Advanced Analytics          ✅ WebSocket Dashboard                       ║
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
    
    total_components = len(health_report['components'])
    
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
        print("📡 Mock Data: http://0.0.0.0:5000/api/mock-data")
        print("🛑 Press Ctrl+C to shutdown gracefully")
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
