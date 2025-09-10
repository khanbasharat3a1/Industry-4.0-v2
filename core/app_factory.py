"""
Flask Application Factory
Creates and configures the Flask application with all extensions
"""

import os
import logging
from flask import Flask, render_template
from flask_socketio import SocketIO
from config.settings import config
from utils.logger import setup_logging

def create_app() -> tuple[Flask, SocketIO]:
    """
    Create and configure Flask application
    Returns: Tuple of (Flask app, SocketIO instance)
    """
    
    # Create Flask app with proper template and static folders
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    
    # Configure Flask
    app.config['SECRET_KEY'] = config.flask.secret_key
    app.config['DEBUG'] = config.flask.debug
    
    # Setup logging
    setup_logging()
    
    # ✅ CRITICAL FIX: Add root route for dashboard
    @app.route('/')
    def dashboard():
        """Main dashboard route - serves the HTML interface"""
        return render_template('dashboard.html')
    
    # ✅ Add health check route
    @app.route('/health')
    def health_check():
        """Health check endpoint"""
        return {
            'status': 'healthy', 
            'service': 'AI Motor Monitoring System v3.1'
        }
    
    # Create SocketIO instance
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    
    # Register blueprints (with error handling)
    register_blueprints(app)
    
    # Register WebSocket events (with error handling)
    register_socketio_events(socketio)
    
    # Create necessary directories
    create_directories()
    
    return app, socketio

def register_blueprints(app: Flask):
    """Register all API blueprints with error handling"""
    try:
        from api.routes.sensor_data import sensor_bp
        from api.routes.health import health_bp
        from api.routes.alerts import alerts_bp
        from api.routes.control import control_bp
        
        app.register_blueprint(sensor_bp, url_prefix='/api')
        app.register_blueprint(health_bp, url_prefix='/api')
        app.register_blueprint(alerts_bp, url_prefix='/api')
        app.register_blueprint(control_bp, url_prefix='/api')
        
        app.logger.info("All API blueprints registered successfully")
        
    except ImportError as e:
        app.logger.warning(f"Some API blueprints could not be registered: {e}")
        # Continue without API routes - dashboard will still work

def register_socketio_events(socketio: SocketIO):
    """Register WebSocket event handlers with error handling"""
    logger = logging.getLogger('socketio')  # ✅ Fixed: Use standard logging
    
    try:
        from api.websocket.events import register_events
        register_events(socketio)
        logger.info("WebSocket events registered successfully")  # ✅ Fixed
        
    except ImportError as e:
        logger.warning(f"WebSocket events could not be registered: {e}")  # ✅ Fixed
        # Continue without WebSocket - dashboard will still work

def create_directories():
    """Create necessary directories if they don't exist"""
    directories = [
        'data',
        'logs', 
        'models',
        'templates',
        'static',
        'static/css',
        'static/js', 
        'static/images'
    ]
    
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
        except Exception as e:
            logging.getLogger(__name__).warning(f"Could not create directory {directory}: {e}")
