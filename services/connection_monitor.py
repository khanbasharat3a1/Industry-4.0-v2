"""
Connection Monitor Service
Dedicated service for monitoring hardware connections and network status
"""

import threading
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional
import ping3

from config.settings import config
from database.manager import DatabaseManager

logger = logging.getLogger(__name__)

class ConnectionMonitor:
    """Monitors hardware connections and network connectivity"""
    
    def __init__(self):
        self.name = "ConnectionMonitor"
        self.db_manager = DatabaseManager()
        
        # Monitoring control
        self._stop_event = threading.Event()
        self._monitor_thread = None
        
        # Connection status
        self.connection_status = {
            'esp_connected': False,
            'plc_connected': False,
            'network_connected': False,
            'last_esp_seen': None,
            'last_plc_seen': None,
            'last_network_check': None,
            'connection_errors': []
        }
        
        # Callbacks for connection events
        self._connection_callbacks = []
    
    def start(self):
        """Start connection monitoring"""
        try:
            if self._monitor_thread and self._monitor_thread.is_alive():
                logger.warning("Connection monitor already running")
                return
            
            self._stop_event.clear()
            self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._monitor_thread.start()
            
            logger.info("Connection monitor started")
            
        except Exception as e:
            logger.error(f"Error starting connection monitor: {e}")
            raise
    
    def stop(self):
        """Stop connection monitoring"""
        if self._monitor_thread:
            logger.info("Stopping connection monitor...")
            self._stop_event.set()
            self._monitor_thread.join(timeout=10)
            logger.info("Connection monitor stopped")
    
    def register_callback(self, callback):
        """Register callback for connection events"""
        self._connection_callbacks.append(callback)
    
    def update_esp_status(self, connected: bool):
        """Update ESP connection status"""
        previous_status = self.connection_status['esp_connected']
        self.connection_status['esp_connected'] = connected
        
        if connected:
            self.connection_status['last_esp_seen'] = datetime.now().isoformat()
            if not previous_status:
                self._trigger_connection_event('esp_connected')
        else:
            if previous_status:
                self._trigger_connection_event('esp_disconnected')
    
    def update_plc_status(self, connected: bool):
        """Update PLC connection status"""
        previous_status = self.connection_status['plc_connected']
        self.connection_status['plc_connected'] = connected
        
        if connected:
            self.connection_status['last_plc_seen'] = datetime.now().isoformat()
            if not previous_status:
                self._trigger_connection_event('plc_connected')
        else:
            if previous_status:
                self._trigger_connection_event('plc_disconnected')
    
    def get_status(self) -> Dict:
        """Get current connection status"""
        return self.connection_status.copy()
    
    def test_network_connectivity(self) -> bool:
        """Test network connectivity"""
        try:
            # Test connectivity to common DNS servers
            test_hosts = ['8.8.8.8', '1.1.1.1', 'google.com']
            
            for host in test_hosts:
                try:
                    response = ping3.ping(host, timeout=5)
                    if response is not None:
                        self.connection_status['network_connected'] = True
                        self.connection_status['last_network_check'] = datetime.now().isoformat()
                        return True
                except Exception:
                    continue
            
            self.connection_status['network_connected'] = False
            return False
            
        except Exception as e:
            logger.error(f"Error testing network connectivity: {e}")
            self.connection_status['network_connected'] = False
            return False
    
    def test_plc_connectivity(self) -> Dict:
        """Test PLC connectivity specifically"""
        try:
            # Test ping to PLC IP
            plc_ip = config.plc.ip
            response = ping3.ping(plc_ip, timeout=5)
            
            if response is not None:
                ping_success = True
                ping_time = response * 1000  # Convert to milliseconds
            else:
                ping_success = False
                ping_time = None
            
            # Test port connectivity (basic socket test)
            import socket
            port_open = False
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((plc_ip, config.plc.port))
                port_open = result == 0
                sock.close()
            except Exception:
                port_open = False
            
            return {
                'ip': plc_ip,
                'port': config.plc.port,
                'ping_success': ping_success,
                'ping_time_ms': ping_time,
                'port_open': port_open,
                'overall_connectivity': ping_success and port_open,
                'tested_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error testing PLC connectivity: {e}")
            return {
                'error': str(e),
                'overall_connectivity': False,
                'tested_at': datetime.now().isoformat()
            }
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        logger.info("Connection monitor loop started")
        
        while not self._stop_event.is_set():
            try:
                current_time = datetime.now()
                
                # Check ESP timeout
                self._check_esp_timeout(current_time)
                
                # Check PLC timeout
                self._check_plc_timeout(current_time)
                
                # Test network connectivity (every 5 minutes)
                if (self.connection_status['last_network_check'] is None or 
                    (current_time - datetime.fromisoformat(self.connection_status['last_network_check'])).total_seconds() > 300):
                    self.test_network_connectivity()
                
                # Sleep before next check
                self._stop_event.wait(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in connection monitor loop: {e}")
                self._stop_event.wait(60)  # Wait longer on error
        
        logger.info("Connection monitor loop ended")
    
    def _check_esp_timeout(self, current_time: datetime):
        """Check for ESP connection timeout"""
        try:
            if (self.connection_status['last_esp_seen'] and 
                self.connection_status['esp_connected']):
                
                last_seen = datetime.fromisoformat(self.connection_status['last_esp_seen'])
                timeout_seconds = (current_time - last_seen).total_seconds()
                
                if timeout_seconds > config.connection.esp_timeout:
                    logger.warning(f"ESP connection timeout ({timeout_seconds:.0f}s)")
                    self.update_esp_status(False)
                    
                    # Log timeout event
                    self.db_manager.log_system_event(
                        event_type='Connection_Timeout',
                        component='ESP',
                        message=f'ESP connection timeout after {timeout_seconds:.0f} seconds',
                        severity='WARNING'
                    )
                    
        except Exception as e:
            logger.error(f"Error checking ESP timeout: {e}")
    
    def _check_plc_timeout(self, current_time: datetime):
        """Check for PLC connection timeout"""
        try:
            if (self.connection_status['last_plc_seen'] and 
                self.connection_status['plc_connected']):
                
                last_seen = datetime.fromisoformat(self.connection_status['last_plc_seen'])
                timeout_seconds = (current_time - last_seen).total_seconds()
                
                if timeout_seconds > config.connection.plc_timeout:
                    logger.warning(f"PLC connection timeout ({timeout_seconds:.0f}s)")
                    self.update_plc_status(False)
                    
                    # Log timeout event
                    self.db_manager.log_system_event(
                        event_type='Connection_Timeout',
                        component='PLC',
                        message=f'PLC connection timeout after {timeout_seconds:.0f} seconds',
                        severity='WARNING'
                    )
                    
        except Exception as e:
            logger.error(f"Error checking PLC timeout: {e}")
    
    def _trigger_connection_event(self, event_type: str):
        """Trigger connection event callbacks"""
        try:
            event_data = {
                'event_type': event_type,
                'timestamp': datetime.now().isoformat(),
                'connection_status': self.connection_status.copy()
            }
            
            # Call registered callbacks
            for callback in self._connection_callbacks:
                try:
                    callback(event_data)
                except Exception as e:
                    logger.error(f"Error in connection callback: {e}")
            
            # Log connection event
            severity = 'INFO' if 'connected' in event_type else 'WARNING'
            component = 'ESP' if 'esp' in event_type else 'PLC'
            
            self.db_manager.log_system_event(
                event_type='Connection_Event',
                component=component,
                message=f'Connection event: {event_type}',
                severity=severity
            )
            
        except Exception as e:
            logger.error(f"Error triggering connection event: {e}")
    
    def get_connection_report(self) -> Dict:
        """Generate comprehensive connection report"""
        try:
            current_time = datetime.now()
            
            # Calculate uptime percentages
            esp_uptime = 0
            plc_uptime = 0
            
            # Get connection events from last 24 hours
            day_ago = current_time - timedelta(hours=24)
            
            # This is a simplified calculation - in production you might want
            # to track actual connection/disconnection events
            if self.connection_status['esp_connected']:
                esp_uptime = 100  # Simplified
            
            if self.connection_status['plc_connected']:
                plc_uptime = 100  # Simplified
            
            # Test current connectivity
            network_test = self.test_network_connectivity()
            plc_test = self.test_plc_connectivity()
            
            return {
                'report_generated_at': current_time.isoformat(),
                'current_status': self.connection_status,
                'uptime_24h': {
                    'esp_uptime_percent': esp_uptime,
                    'plc_uptime_percent': plc_uptime,
                    'network_uptime_percent': 100 if network_test else 0
                },
                'connectivity_tests': {
                    'network_test': {'success': network_test},
                    'plc_test': plc_test
                },
                'recommendations': self._generate_connection_recommendations()
            }  # ✅ FIXED: Added missing closing brace here
            
        except Exception as e:
            logger.error(f"Error generating connection report: {e}")
            return {'error': str(e)}
    
    def _generate_connection_recommendations(self) -> list:
        """Generate connection improvement recommendations"""
        recommendations = []
        
        if not self.connection_status['network_connected']:
            recommendations.append("Check network connectivity - unable to reach external hosts")
        
        if not self.connection_status['esp_connected']:
            recommendations.append("ESP/Arduino not responding - check power and WiFi connection")
        
        if not self.connection_status['plc_connected']:
            recommendations.append("PLC connection issues - verify IP address and MC protocol settings")
        
        if len(self.connection_status.get('connection_errors', [])) > 5:
            recommendations.append("High number of connection errors - consider network infrastructure review")
        
        return recommendations
