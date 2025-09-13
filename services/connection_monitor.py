"""
Connection Monitor Service
Dedicated service for monitoring hardware connections and network status
"""

import logging
from datetime import datetime, timedelta
import eventlet
import ping3

from config.settings import config
from database.manager import DatabaseManager

logger = logging.getLogger(__name__)

class ConnectionMonitor:
    """Monitors hardware connections and network connectivity using eventlet for cooperative multitasking."""
    
    def __init__(self, socketio):
        self.name = "ConnectionMonitor"
        self.db_manager = DatabaseManager()
        self.socketio = socketio
        
        # Connection status
        self.connection_status = {
            'esp_connected': False,
            'plc_connected': False,
            'network_connected': False,
            'last_esp_seen': None,
            'last_plc_seen': None,
            'last_network_check': None,
        }
        
        logger.info("ConnectionMonitor initialized for eventlet.")

    def run(self):
        """Main monitoring loop, designed to be run as a green thread."""
        logger.info("Connection monitor loop started.")
        while True:
            try:
                current_time = datetime.now()
                
                self._check_esp_timeout(current_time)
                self._check_plc_timeout(current_time)
                
                # Test network connectivity (every 5 minutes)
                if (self.connection_status['last_network_check'] is None or 
                    (current_time - datetime.fromisoformat(self.connection_status['last_network_check'])).total_seconds() > 300):
                    self.test_network_connectivity()
                
                # Emit status update via WebSocket
                self.socketio.emit('connection_status_update', self.get_status())

                eventlet.sleep(30)  # Non-blocking sleep for 30 seconds
                
            except Exception as e:
                logger.error(f"Error in connection monitor loop: {e}", exc_info=True)
                eventlet.sleep(60)  # Wait longer on error

    def update_device_status(self, device_name, connected):
        """
        Update the connection status for a given device ('esp' or 'plc').
        """
        status_key = f'{device_name}_connected'
        last_seen_key = f'last_{device_name}_seen'
        
        previous_status = self.connection_status.get(status_key, False)
        self.connection_status[status_key] = connected

        if connected:
            self.connection_status[last_seen_key] = datetime.now().isoformat()
            if not previous_status:
                self._trigger_connection_event(f'{device_name}_connected')
        else:
            if previous_status:
                self._trigger_connection_event(f'{device_name}_disconnected')

    def get_status(self):
        """Get current connection status."""
        return self.connection_status.copy()

    def test_network_connectivity(self):
        """Test network connectivity."""
        self.connection_status['last_network_check'] = datetime.now().isoformat()
        try:
            # ping3 can be blocking, so it's better to run it in a separate thread pool if it becomes an issue.
            # For now, we assume it's fast enough.
            response = ping3.ping('google.com', timeout=5)
            self.connection_status['network_connected'] = response is not None
            return self.connection_status['network_connected']
        except Exception as e:
            logger.warning(f"Network connectivity test failed: {e}")
            self.connection_status['network_connected'] = False
            return False

    def _check_esp_timeout(self, current_time):
        """Check for ESP connection timeout."""
        if self.connection_status['esp_connected'] and self.connection_status['last_esp_seen']:
            last_seen = datetime.fromisoformat(self.connection_status['last_esp_seen'])
            timeout_seconds = (current_time - last_seen).total_seconds()

            if timeout_seconds > config.connection.esp_timeout:
                logger.warning(f"ESP connection timeout ({timeout_seconds:.0f}s).")
                self.update_device_status('esp', False)

    def _check_plc_timeout(self, current_time):
        """Check for PLC connection timeout."""
        if self.connection_status['plc_connected'] and self.connection_status['last_plc_seen']:
            last_seen = datetime.fromisoformat(self.connection_status['last_plc_seen'])
            timeout_seconds = (current_time - last_seen).total_seconds()

            if timeout_seconds > config.connection.plc_timeout:
                logger.warning(f"PLC connection timeout ({timeout_seconds:.0f}s).")
                self.update_device_status('plc', False)

    def _trigger_connection_event(self, event_type):
        """Log connection event and emit it via WebSocket."""
        try:
            logger.info(f"Connection event: {event_type}")

            # Emit WebSocket event
            self.socketio.emit('connection_event', {
                'event_type': event_type,
                'timestamp': datetime.now().isoformat(),
                'status': self.get_status()
            })
            
            # Log to database
            severity = 'INFO' if 'connected' in event_type else 'WARNING'
            component = 'ESP' if 'esp' in event_type else 'PLC'
            self.db_manager.log_system_event(
                event_type='Connection_Event',
                component=component,
                message=f'Connection event: {event_type}',
                severity=severity
            )
        except Exception as e:
            logger.error(f"Error triggering connection event: {e}", exc_info=True)
