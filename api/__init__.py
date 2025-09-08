"""
API package for motor monitoring system
RESTful API endpoints and WebSocket handlers
"""

from flask import Blueprint

# Import all blueprints for easy registration
from .routes.sensor_data import sensor_bp
from .routes.health import health_bp
from .routes.alerts import alerts_bp
from .routes.control import control_bp

__all__ = ['sensor_bp', 'health_bp', 'alerts_bp', 'control_bp']
