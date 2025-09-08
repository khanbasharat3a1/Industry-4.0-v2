"""
WebSocket Event Handlers
Real-time communication between server and dashboard
"""

from flask_socketio import emit, disconnect
import logging
from datetime import datetime

from services.data_processor import DataProcessor
from database.manager import DatabaseManager

logger = logging.getLogger(__name__)

# Initialize components
data_processor = DataProcessor()
db_manager = DatabaseManager()

def register_events(socketio):
    """Register all WebSocket event handlers"""
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        try:
            logger.info('Client connected to WebSocket')
            
            # Send initial data to newly connected client
            emit('status_update', data_processor.get_system_status())
            emit('sensor_update', data_processor.get_latest_data())
            emit('health_update', data_processor.get_latest_health_data())
            
            # Send connection confirmation
            emit('connection_confirmed', {
                'status': 'connected',
                'timestamp': datetime.now().isoformat(),
                'message': 'WebSocket connection established'
            })
            
        except Exception as e:
            logger.error(f"Error handling WebSocket connect: {e}")
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        try:
            logger.info('Client disconnected from WebSocket')
        except Exception as e:
            logger.error(f"Error handling WebSocket disconnect: {e}")
    
    @socketio.on('request_update')
    def handle_update_request(data=None):
        """Handle manual update request from client"""
        try:
            logger.debug('Client requested data update')
            
            # Send current data
            emit('sensor_update', data_processor.get_latest_data())
            emit('status_update', data_processor.get_system_status())
            emit('health_update', data_processor.get_latest_health_data())
            
            # Send update confirmation
            emit('update_response', {
                'status': 'success',
                'timestamp': datetime.now().isoformat(),
                'message': 'Data update sent'
            })
            
        except Exception as e:
            logger.error(f"Error handling update request: {e}")
            emit('update_response', {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            })
    
    @socketio.on('subscribe_to_alerts')
    def handle_alert_subscription(data=None):
        """Handle client subscription to alert updates"""
        try:
            logger.info('Client subscribed to alert updates')
            
            # Send current alerts
            alerts = db_manager.get_maintenance_alerts(acknowledged=False, limit=10)
            emit('alerts_update', {
                'alerts': alerts,
                'timestamp': datetime.now().isoformat()
            })
            
            emit('subscription_response', {
                'status': 'success',
                'subscription': 'alerts',
                'message': 'Subscribed to alert updates'
            })
            
        except Exception as e:
            logger.error(f"Error handling alert subscription: {e}")
            emit('subscription_response', {
                'status': 'error',
                'message': str(e)
            })
    
    @socketio.on('request_health_details')
    def handle_health_details_request(data=None):
        """Handle request for detailed health information"""
        try:
            logger.debug('Client requested health details')
            
            health_data = data_processor.get_latest_health_data()
            
            emit('health_details_response', {
                'status': 'success',
                'health_data': health_data,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error handling health details request: {e}")
            emit('health_details_response', {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            })
    
    @socketio.on('request_recommendations')
    def handle_recommendations_request(data=None):
        """Handle request for AI recommendations"""
        try:
            logger.debug('Client requested recommendations')
            
            # Get current recommendations
            from ai.recommendations import RecommendationsEngine
            rec_engine = RecommendationsEngine()
            
            health_data = data_processor.get_latest_health_data()
            system_status = data_processor.get_system_status()
            
            recommendations = rec_engine.generate_recommendations(health_data, system_status)
            rec_summary = rec_engine.get_recommendation_summary(recommendations)
            
            emit('recommendations_response', {
                'status': 'success',
                'recommendations': recommendations,
                'summary': rec_summary,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error handling recommendations request: {e}")
            emit('recommendations_response', {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            })
    
    @socketio.on('motor_command')
    def handle_motor_command(data):
        """Handle motor control command via WebSocket"""
        try:
            if not data or not data.get('command'):
                emit('command_response', {
                    'status': 'error',
                    'message': 'No command specified'
                })
                return
            
            command = data['command']
            user_id = data.get('user_id', 'WebSocket User')
            
            logger.info(f'Motor command received via WebSocket: {command} from {user_id}')
            
            # Log the command
            db_manager.log_system_event(
                event_type='Motor_Control_WS',
                component='WebSocket',
                message=f'Motor command via WebSocket: {command}',
                user_id=user_id
            )
            
            emit('command_response', {
                'status': 'success',
                'command': command,
                'message': f'Command "{command}" executed successfully',
                'timestamp': datetime.now().isoformat()
            })
            
            # Broadcast command to all connected clients
            socketio.emit('motor_command_broadcast', {
                'command': command,
                'executed_by': user_id,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error handling motor command: {e}")
            emit('command_response', {
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            })
    
    @socketio.on('ping')
    def handle_ping(data=None):
        """Handle ping request for connection testing"""
        try:
            emit('pong', {
                'timestamp': datetime.now().isoformat(),
                'message': 'Connection active'
            })
        except Exception as e:
            logger.error(f"Error handling ping: {e}")

    # Store socketio instance for broadcasting from other modules
    data_processor.set_socketio(socketio)
    
    return socketio
