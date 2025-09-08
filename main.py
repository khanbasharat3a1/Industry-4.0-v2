"""
AI-Enabled Industrial Motor Health & Environment Monitoring System
Main Application Entry Point

Version: 3.1 - Complete Modular Implementation
Author: AI Motor Monitoring Team
Created: 2025
"""

import sys
import os
import signal
import time
from datetime import datetime
import logging

# Fix Windows Unicode console encoding
if sys.platform == 'win32':
    # Set console to UTF-8
    os.system('chcp 65001 >nul 2>&1')
    
    # Reconfigure stdout/stderr for UTF-8
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # For older Python versions
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Core application imports
from core.app_factory import create_app
from services.data_processor import DataProcessor
from services.background_tasks import BackgroundTaskManager
from services.connection_monitor import ConnectionMonitor
from services.alert_service import AlertService
from hardware.plc_manager import FX5UPLCManager
from utils.logger import setup_logging, log_system_startup, log_system_shutdown
from config.settings import config

# Global application components
app = None
socketio = None
data_processor = None
background_tasks = None
connection_monitor = None
alert_service = None
plc_manager = None

def initialize_system():
    """Initialize all system components"""
    global app, socketio, data_processor, background_tasks, connection_monitor, alert_service, plc_manager
    
    try:
        # Setup logging first
        setup_logging()
        logger = logging.getLogger(__name__)
        
        log_system_startup("AI Motor Monitoring System", "3.1")
        
        # Create Flask application
        logger.info("Creating Flask application...")
        app, socketio = create_app()
        
        # Add missing root route for dashboard
        @app.route('/')
        def dashboard():
            """Main dashboard route"""
            return app.send_static_file('/templates/dashboard.html')
        
        # Add health check route
        @app.route('/health')
        def health_check():
            """Health check endpoint"""
            return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}
        
        # Initialize hardware managers
        logger.info("Initializing hardware managers...")
        plc_manager = FX5UPLCManager()
        
        # Initialize services
        logger.info("Initializing services...")
        data_processor = DataProcessor()
        background_tasks = BackgroundTaskManager()
        connection_monitor = ConnectionMonitor()
        alert_service = AlertService()
        
        # Connect SocketIO to data processor for real-time updates
        data_processor.set_socketio(socketio)
        
        # Register connection monitor callbacks
        connection_monitor.register_callback(handle_connection_event)
        
        # Start background services
        logger.info("Starting background services...")
        background_tasks.start()
        connection_monitor.start()
        
        # Test initial connections
        logger.info("Testing initial connections...")
        test_initial_connections()
        
        logger.info("System initialization completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"System initialization failed: {e}")
        cleanup_system()
        return False

def test_initial_connections():
    """Test initial hardware connections"""
    logger = logging.getLogger(__name__)
    
    try:
        # Test PLC connection
        logger.info(f"Testing PLC connection to {config.plc.ip}:{config.plc.port}")
        plc_connected = plc_manager.connect()
        
        if plc_connected:
            logger.info("PLC connection established successfully")
            
            # Test PLC functionality
            test_result = plc_manager.test_connection()
            if test_result.get('connection_test', False):
                logger.info("PLC functionality test passed")
                logger.info(f"Test values: D100={test_result.get('test_values', {}).get('raw_d100', 'N/A')}, "
                           f"D102={test_result.get('test_values', {}).get('raw_d102', 'N/A')}")
            else:
                logger.warning("PLC functionality test failed")
                
        else:
            logger.warning("PLC connection failed - will retry automatically")
        
        # Update connection monitor
        connection_monitor.update_plc_status(plc_connected)
        
        # Test network connectivity
        network_ok = connection_monitor.test_network_connectivity()
        if network_ok:
            logger.info("Network connectivity confirmed")
        else:
            logger.warning("Network connectivity issues detected")
        
    except Exception as e:
        logger.error(f"Error during initial connection tests: {e}")

def handle_connection_event(event_data):
    """Handle connection events from connection monitor"""
    logger = logging.getLogger(__name__)
    
    try:
        event_type = event_data.get('event_type')
        logger.info(f"Connection event: {event_type}")
        
        # Emit event via WebSocket if available
        if socketio:
            socketio.emit('connection_event', event_data)
            
        # Handle specific events
        if event_type in ['esp_disconnected', 'plc_disconnected']:
            component = 'ESP' if 'esp' in event_type else 'PLC'
            logger.warning(f"{component} connection lost - system functionality reduced")
            
    except Exception as e:
        logger.error(f"Error handling connection event: {e}")

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
    log_system_shutdown("AI Motor Monitoring System")
    
    try:
        # Stop background services
        if background_tasks:
            logger.info("Stopping background tasks...")
            background_tasks.stop()
        
        if connection_monitor:
            logger.info("Stopping connection monitor...")
            connection_monitor.stop()
        
        if data_processor:
            logger.info("Stopping data processor...")
            data_processor.stop()
        
        # Disconnect hardware
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
║                           Version 3.1 - Modular Edition                     ║
║                                                                              ║
║  ✅ FX5U PLC Integration        ✅ Real-time Health Analysis                 ║
║  ✅ ESP8266/Arduino Support     ✅ AI-Powered Recommendations                ║
║  ✅ Advanced Analytics          ✅ WebSocket Dashboard                       ║
║  ✅ Predictive Maintenance      ✅ Comprehensive Logging                     ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """
    print(banner)
    
    # Print configuration summary
    print(f"🌐 Server: http://{config.flask.host}:{config.flask.port}")
    print(f"🔌 PLC: {config.plc.ip}:{config.plc.port}")
    print(f"📊 Database: {config.database.url}")
    print(f"📝 Logs: {config.logging.file}")
    print(f"🎯 Debug Mode: {'Enabled' if config.flask.debug else 'Disabled'}")
    print("═" * 82)

def run_health_check():
    """Run system health check"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Running system health check...")
        
        health_report = {
            'timestamp': datetime.now().isoformat(),
            'components': {}
        }
        
        # Check database
        try:
            from database.manager import DatabaseManager
            db_manager = DatabaseManager()
            stats = db_manager.get_system_statistics()
            health_report['components']['database'] = {
                'status': 'healthy',
                'total_records': stats.get('total_sensor_readings', 0)
            }
        except Exception as e:
            health_report['components']['database'] = {
                'status': 'error',
                'error': str(e)
            }
        
        # Check PLC connection
        if plc_manager:
            plc_status = plc_manager.get_connection_status()
            health_report['components']['plc'] = {
                'status': 'healthy' if plc_status['plc_connected'] else 'disconnected',
                'ip': plc_status.get('plc_ip'),
                'port': plc_status.get('plc_port')
            }
        
        # Check network
        if connection_monitor:
            network_ok = connection_monitor.test_network_connectivity()
            health_report['components']['network'] = {
                'status': 'healthy' if network_ok else 'issues'
            }
        
        # Log health report
        healthy_components = len([c for c in health_report['components'].values() 
                                if c.get('status') == 'healthy'])
        total_components = len(health_report['components'])
        
        logger.info(f"Health check completed: {healthy_components}/{total_components} components healthy")
        
        return health_report
        
    except Exception as e:
        logger.error(f"Error during health check: {e}")
        return {'error': str(e)}

def main():
    """Main application entry point"""
    try:
        # Print startup banner
        print_startup_banner()
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Initialize system
        if not initialize_system():
            print("❌ System initialization failed. Check logs for details.")
            sys.exit(1)
        
        # Run initial health check
        health_report = run_health_check()
        
        # Print startup completion
        print("🚀 System startup completed successfully!")
        print(f"📊 Dashboard: http://{config.flask.host}:{config.flask.port}")
        print("📝 Check logs for detailed system information")
        print("🛑 Press Ctrl+C to shutdown gracefully")
        print("═" * 82)
        
        # Start Flask-SocketIO server
        socketio.run(
            app,
            host=config.flask.host,
            port=config.flask.port,
            debug=config.flask.debug,
            use_reloader=False,  # Disable reloader to prevent double initialization
            allow_unsafe_werkzeug=True  # Allow for development
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
