"""
Application Runner
This is the main entry point for the AI Motor Monitoring System.
It creates the Flask app using the factory pattern and runs the server.
"""

# IMPORTANT: Eventlet must be monkey-patched before any other imports
import eventlet
eventlet.monkey_patch()

import os
import logging
from core.app_factory import create_app
from config.settings import config

if __name__ == '__main__':
    # The app factory will handle all initial setup, including logging.
    app, socketio = create_app()

    # Get a logger instance after the factory has configured logging.
    logger = logging.getLogger(__name__)

    # Get host, port, and debug settings from the centralized config.
    host = config.flask.host
    port = config.flask.port
    debug = config.flask.debug

    logger.info(f"Starting server on http://{host}:{port}")

    try:
        # Run the application using the SocketIO server.
        # use_reloader=False is recommended to avoid initializing background tasks twice.
        socketio.run(app, host=host, port=port, debug=debug, use_reloader=False, allow_unsafe_werkzeug=True)
    except Exception as e:
        logger.critical(f"Failed to start the application server: {e}", exc_info=True)
