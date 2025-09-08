"""
Motor Control API Routes
Handles motor control commands and system operations
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

from database.manager import DatabaseManager
from services.data_processor import DataProcessor
from hardware.plc_manager import FX5UPLCManager

logger = logging.getLogger(__name__)

# Create blueprint
control_bp = Blueprint('control', __name__)

# Initialize components
db_manager = DatabaseManager()
data_processor = DataProcessor()
plc_manager = FX5UPLCManager()

@control_bp.route('/motor-control', methods=['POST'])
def motor_control():
    """Execute motor control commands"""
    try:
        data = request.get_json()
        
        if not data or not data.get('command'):
            return jsonify({
                'status': 'error',
                'message': 'No command specified'
            }), 400
        
        command = data['command'].lower()
        user_id = data.get('user_id', 'Web User')
        
        # Validate command
        valid_commands = ['start', 'stop', 'emergency_stop', 'reset', 'cooling_on', 'cooling_off']
        if command not in valid_commands:
            return jsonify({
                'status': 'error',
                'message': f'Invalid command. Valid commands: {", ".join(valid_commands)}'
            }), 400
        
        # Log the control command
        db_manager.log_system_event(
            event_type='Motor_Control',
            component='Control',
            message=f'Motor control command: {command}',
            details=f'Executed by: {user_id}',
            user_id=user_id
        )
        
        # Execute command based on type
        result = {'status': 'success', 'message': f'Command "{command}" logged successfully'}
        
        # For emergency stop, add additional logging
        if command == 'emergency_stop':
            db_manager.log_system_event(
                event_type='Emergency_Stop',
                component='Safety',
                message='EMERGENCY STOP activated via web interface',
                severity='CRITICAL',
                user_id=user_id
            )
            result['warning'] = 'Emergency stop command logged - verify motor has stopped'
        
        # For start command, check system health
        elif command == 'start':
            health_data = data_processor.get_latest_health_data()
            if health_data and health_data.get('overall_health_score', 0) < 60:
                result['warning'] = f'Motor health is {health_data.get("overall_health_score")}% - consider inspection before starting'
        
        result.update({
            'command': command,
            'executed_by': user_id,
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error in motor control: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@control_bp.route('/system-control', methods=['POST'])
def system_control():
    """Execute system-level control commands"""
    try:
        data = request.get_json()
        
        if not data or not data.get('action'):
            return jsonify({
                'status': 'error',
                'message': 'No action specified'
            }), 400
        
        action = data['action'].lower()
        user_id = data.get('user_id', 'Web User')
        
        result = {'status': 'success'}
        
        if action == 'restart_connections':
            # Restart hardware connections
            success = data_processor.restart_connections()
            result['message'] = 'Connection restart initiated' if success else 'Failed to restart connections'
            
        elif action == 'cleanup_data':
            # Clean up old data
            cleanup_result = db_manager.cleanup_old_data()
            result['message'] = 'Data cleanup completed'
            result['cleanup_details'] = cleanup_result
            
        elif action == 'recalculate_health':
            # Recalculate health scores
            hours = data.get('hours', 1)
            calc_result = data_processor.recalculate_health_scores(hours=hours)
            result['message'] = f'Health scores recalculated for {hours} hours'
            result['calculation_details'] = calc_result
            
        elif action == 'export_data':
            # Export data to CSV
            export_path = db_manager.export_data_to_csv()
            result['message'] = 'Data exported successfully'
            result['export_path'] = export_path
            
        else:
            return jsonify({
                'status': 'error',
                'message': f'Unknown action: {action}'
            }), 400
        
        # Log the system control action
        db_manager.log_system_event(
            event_type='System_Control',
            component='System',
            message=f'System control action: {action}',
            details=str(result),
            user_id=user_id
        )
        
        result.update({
            'action': action,
            'executed_by': user_id,
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error in system control: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@control_bp.route('/plc-test', methods=['POST'])
def test_plc_connection():
    """Test PLC connection and functionality"""
    try:
        user_id = request.get_json().get('user_id', 'Web User') if request.get_json() else 'Web User'
        
        # Run PLC connection test
        test_result = plc_manager.test_connection()
        
        # Log the test
        db_manager.log_system_event(
            event_type='PLC_Test',
            component='PLC',
            message='PLC connection test executed',
            details=str(test_result),
            user_id=user_id
        )
        
        return jsonify({
            'status': 'success',
            'test_result': test_result,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error testing PLC connection: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@control_bp.route('/system-status', methods=['GET'])
def get_system_status():
    """Get comprehensive system status"""
    try:
        # Get status from data processor
        system_status = data_processor.get_system_status()
        
        # Get hardware connection status
        esp_status = data_processor.esp_handler.get_connection_status()
        plc_status = plc_manager.get_connection_status()
        
        # Combine all status information
        comprehensive_status = {
            'system': system_status,
            'esp': esp_status,
            'plc': plc_status,
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify({
            'status': 'success',
            'system_status': comprehensive_status
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
