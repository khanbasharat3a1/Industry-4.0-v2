"""
Data Processing Service
Central service for processing sensor data and coordinating system operations
"""

import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
import time

from hardware.esp_handler import ESPHandler
from hardware.plc_manager import FX5UPLCManager
from database.manager import DatabaseManager
from ai.health_analyzer import MotorHealthAnalyzer
from ai.recommendations import RecommendationsEngine
from config.settings import config

logger = logging.getLogger(__name__)

class DataProcessor:
    """Central data processing and coordination service"""
    
    def __init__(self):
        self.name = "DataProcessor"
        
        # Initialize components
        self.esp_handler = ESPHandler()
        self.plc_manager = FX5UPLCManager()
        self.db_manager = DatabaseManager()
        self.health_analyzer = MotorHealthAnalyzer()
        self.rec_engine = RecommendationsEngine()
        
        # Data storage
        self.latest_data = {}
        self.latest_health_data = {}
        self.system_status = {
            'esp_connected': False,
            'plc_connected': False,
            'ai_model_status': 'Initializing',
            'last_update': None,
            'esp_last_seen': None,
            'plc_last_seen': None
        }
        
        # Threading control
        self._stop_event = threading.Event()
        self._socketio = None
        
        # Start background data collection
        self._start_background_tasks()
    
    def set_socketio(self, socketio):
        """Set SocketIO instance for real-time updates"""
        self._socketio = socketio
    
    def process_sensor_data(self, esp_data: Dict) -> bool:
        """
        Process incoming sensor data from ESP
        
        Args:
            esp_data: Processed ESP sensor data
            
        Returns:
            True if processing successful, False otherwise
        """
        try:
            # Update latest data with ESP readings
            self.latest_data.update(esp_data)
            
            # Update ESP connection status
            self.system_status['esp_connected'] = True
            self.system_status['esp_last_seen'] = datetime.now().isoformat()
            self.system_status['last_update'] = datetime.now().isoformat()
            
            # Get PLC data if available
            plc_data = self.plc_manager.get_last_data()
            if plc_data:
                self.latest_data.update(plc_data)
            
            # Save to database with health analysis
            success = self.db_manager.save_sensor_data(self.latest_data, self.system_status)
            
            if success:
                # Trigger real-time updates
                self._emit_real_time_updates()
                
                logger.debug("Sensor data processed and saved successfully")
                return True
            else:
                logger.error("Failed to save sensor data")
                return False
                
        except Exception as e:
            logger.error(f"Error processing sensor data: {e}")
            return False
    
    def get_latest_data(self) -> Dict:
        """Get the latest sensor data"""
        return self.latest_data.copy()
    
    def get_latest_health_data(self) -> Dict:
        """Get the latest health analysis data"""
        return self.latest_health_data.copy()
    
    def get_system_status(self) -> Dict:
        """Get current system status"""
        return self.system_status.copy()
    
    def restart_connections(self) -> bool:
        """Restart hardware connections"""
        try:
            logger.info("Restarting hardware connections...")
            
            # Restart PLC connection
            self.plc_manager.disconnect()
            time.sleep(1)
            plc_success = self.plc_manager.connect()
            
            # ESP doesn't need restart as it's HTTP-based
            esp_success = True
            
            if plc_success:
                logger.info("Hardware connections restarted successfully")
            else:
                logger.warning("Some hardware connections failed to restart")
            
            return plc_success and esp_success
            
        except Exception as e:
            logger.error(f"Error restarting connections: {e}")
            return False
    
    def recalculate_health_scores(self, hours: int = 1) -> Dict:
        """
        Recalculate health scores for recent data
        
        Args:
            hours: Hours of data to recalculate
            
        Returns:
            Recalculation result dictionary
        """
        try:
            logger.info(f"Recalculating health scores for last {hours} hours")
            
            # Get recent data
            recent_data = self.db_manager.get_recent_data_df(hours=hours)
            
            if recent_data.empty:
                return {'status': 'warning', 'message': 'No data to recalculate'}
            
            # Recalculate health for current data if available
            if self.latest_data:
                self.latest_health_data = self.health_analyzer.calculate_comprehensive_health(
                    self.latest_data, recent_data
                )
                
                # Emit updated health data
                if self._socketio:
                    self._socketio.emit('health_update', self.latest_health_data)
            
            return {
                'status': 'success',
                'records_processed': len(recent_data),
                'time_range_hours': hours,
                'message': 'Health scores recalculated successfully'
            }
            
        except Exception as e:
            logger.error(f"Error recalculating health scores: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def _start_background_tasks(self):
        """Start background data collection tasks"""
        try:
            # Start PLC data collection thread
            plc_thread = threading.Thread(target=self._plc_data_collector, daemon=True)
            plc_thread.start()
            
            # Start health analysis thread
            health_thread = threading.Thread(target=self._health_analysis_task, daemon=True)
            health_thread.start()
            
            # Start connection monitor thread
            monitor_thread = threading.Thread(target=self._connection_monitor, daemon=True)
            monitor_thread.start()
            
            logger.info("Background tasks started successfully")
            
        except Exception as e:
            logger.error(f"Error starting background tasks: {e}")
    
    def _plc_data_collector(self):
        """Background task to collect PLC data"""
        while not self._stop_event.is_set():
            try:
                plc_data = self.plc_manager.read_data()
                current_time = datetime.now()
                
                if plc_data and plc_data.get('plc_connected', False):
                    self.latest_data.update(plc_data)
                    self.system_status['plc_connected'] = True
                    self.system_status['plc_last_seen'] = current_time.isoformat()
                else:
                    if self.system_status['plc_connected']:
                        logger.warning("PLC connection lost")
                    self.system_status['plc_connected'] = False
                    # Clear PLC data
                    self.latest_data['plc_motor_temp'] = None
                    self.latest_data['plc_motor_voltage'] = None
                    self.latest_data['plc_connected'] = False
                
            except Exception as e:
                logger.error(f"Error in PLC data collection: {e}")
                self.system_status['plc_connected'] = False
            
            self._stop_event.wait(5)  # Wait 5 seconds between reads
    
    def _health_analysis_task(self):
        """Background task for health analysis and recommendations"""
        while not self._stop_event.is_set():
            try:
                if len(self.latest_data) > 0:
                    # Get recent data for analysis
                    recent_data = self.db_manager.get_recent_data_df(hours=2)
                    
                    # Calculate health scores
                    self.latest_health_data = self.health_analyzer.calculate_comprehensive_health(
                        self.latest_data, recent_data
                    )
                    
                    # Generate recommendations
                    recommendations = self.rec_engine.generate_recommendations(
                        self.latest_health_data, self.system_status
                    )
                    
                    # Emit updates via WebSocket
                    if self._socketio:
                        self._socketio.emit('health_update', self.latest_health_data)
                        self._socketio.emit('recommendations_update', recommendations)
                    
                    self.system_status['ai_model_status'] = 'Active'
                else:
                    self.system_status['ai_model_status'] = 'Waiting for data'
                
            except Exception as e:
                logger.error(f"Error in health analysis task: {e}")
                self.system_status['ai_model_status'] = 'Error'
            
            self._stop_event.wait(15)  # Run every 15 seconds
    
    def _connection_monitor(self):
        """Background task to monitor connection timeouts"""
        while not self._stop_event.is_set():
            try:
                current_time = datetime.now()
                
                # Check ESP timeout
                if self.system_status['esp_last_seen']:
                    esp_last_seen = datetime.fromisoformat(self.system_status['esp_last_seen'])
                    esp_timeout = (current_time - esp_last_seen).total_seconds()
                    
                    if esp_timeout > config.connection.esp_timeout:
                        if self.system_status['esp_connected']:
                            logger.warning(f"ESP connection timeout ({esp_timeout:.0f}s)")
                            self.system_status['esp_connected'] = False
                            
                            # Clear ESP data
                            esp_keys = ['esp_current', 'esp_voltage', 'esp_rpm', 'env_temp_c', 
                                      'env_humidity', 'env_temp_f', 'heat_index_c', 'heat_index_f',
                                      'relay1_status', 'relay2_status', 'relay3_status', 'combined_status']
                            
                            for key in esp_keys:
                                if key in self.latest_data:
                                    self.latest_data[key] = None
                            
                            # Emit connection lost event
                            if self._socketio:
                                self._socketio.emit('connection_lost', {
                                    'component': 'ESP',
                                    'message': 'ESP connection timeout',
                                    'timeout': esp_timeout
                                })
                
                # Check PLC timeout
                if self.system_status['plc_last_seen']:
                    plc_last_seen = datetime.fromisoformat(self.system_status['plc_last_seen'])
                    plc_timeout = (current_time - plc_last_seen).total_seconds()
                    
                    if plc_timeout > config.connection.plc_timeout:
                        if self.system_status['plc_connected']:
                            logger.warning(f"PLC connection timeout ({plc_timeout:.0f}s)")
                            self.system_status['plc_connected'] = False
                            
                            # Clear PLC data
                            self.latest_data['plc_motor_temp'] = None
                            self.latest_data['plc_motor_voltage'] = None
                            self.latest_data['plc_connected'] = False
                            
                            # Emit connection lost event
                            if self._socketio:
                                self._socketio.emit('connection_lost', {
                                    'component': 'PLC',
                                    'message': 'PLC connection timeout',
                                    'timeout': plc_timeout
                                })
                
                # Emit status update
                if self._socketio:
                    self._socketio.emit('status_update', self.system_status)
                
            except Exception as e:
                logger.error(f"Error in connection monitor: {e}")
            
            self._stop_event.wait(config.connection.data_cleanup_interval)
    
    def _emit_real_time_updates(self):
        """Emit real-time updates via WebSocket"""
        if self._socketio:
            try:
                self._socketio.emit('sensor_update', self.latest_data)
                self._socketio.emit('status_update', self.system_status)
            except Exception as e:
                logger.error(f"Error emitting real-time updates: {e}")
    
    def stop(self):
        """Stop background tasks"""
        logger.info("Stopping data processor...")
        self._stop_event.set()
        
        # Disconnect hardware
        self.plc_manager.disconnect()
