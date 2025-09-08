"""
Flask Application Factory
Creates and configures the Flask application with all extensions
"""

import os
from flask import Flask
from flask_socketio import SocketIO
from config.settings import config
from utils.logger import setup_logging

def create_app() -> tuple[Flask, SocketIO]:
    """
    Create and configure Flask application
    Returns: Tuple of (Flask app, SocketIO instance)
    """
    
    # Create Flask app
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    
    # Configure Flask
    app.config['SECRET_KEY'] = config.flask.secret_key
    app.config['DEBUG'] = config.flask.debug
    
    # Setup logging
    setup_logging()
    
    # Create SocketIO instance
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    
    # Register blueprints
    register_blueprints(app)
    
    # Register WebSocket events
    register_socketio_events(socketio)
    
    # Create necessary directories
    create_directories()
    
    return app, socketio

def register_blueprints(app: Flask):
    """Register all API blueprints"""
    from api.routes.sensor_data import sensor_bp
    from api.routes.health import health_bp
    from api.routes.alerts import alerts_bp
    from api.routes.control import control_bp
    
    app.register_blueprint(sensor_bp, url_prefix='/api')
    app.register_blueprint(health_bp, url_prefix='/api')
    app.register_blueprint(alerts_bp, url_prefix='/api')
    app.register_blueprint(control_bp, url_prefix='/api')

def register_socketio_events(socketio: SocketIO):
    """Register WebSocket event handlers"""
    from api.websocket.events import register_events
    register_events(socketio)

def create_directories():
    """Create necessary directories if they don't exist"""
    directories = [
        'data',
        'logs', 
        'models',
        config.model_path
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
