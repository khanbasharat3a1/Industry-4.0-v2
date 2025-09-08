"""
Sensor Data API Routes
Handles sensor data reception and retrieval endpoints
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

from hardware.esp_handler import ESPHandler
from database.manager import DatabaseManager
from utils.validators import validate_esp_data
from services.data_processor import DataProcessor

logger = logging.getLogger(__name__)

# Create blueprint
sensor_bp = Blueprint('sensor', __name__)

# Initialize handlers
esp_handler = ESPHandler()
db_manager = DatabaseManager()
data_processor = DataProcessor()

@sensor_bp.route('/send-data', methods=['POST'])
def receive_sensor_data():
    """
    Receive sensor data from ESP/Arduino
    
    Expected JSON format:
    {
        "TYPE": "ADU_TEXT",
        "VAL1": "current_value",
        "VAL2": "voltage_value",
        ...
    }
    """
    try:
        # Get JSON data from request
        raw_data = request.get_json()
        if not raw_data:
            return jsonify({
                'status': 'error',
                'message': 'No JSON data received'
            }), 400
        
        # Validate data format
        if not validate_esp_data(raw_data):
            return jsonify({
                'status': 'error',
                'message': 'Invalid data format'
            }), 400
        
        # Process ESP data
        processed_data = esp_handler.process_esp_data(raw_data)
        if not processed_data:
            return jsonify({
                'status': 'error',
                'message': 'Failed to process sensor data'
            }), 422
        
        # Send to data processor for full processing
        success = data_processor.process_sensor_data(processed_data)
        
        if success:
            logger.info("Sensor data received and processed successfully")
            return jsonify({
                'status': 'success',
                'message': 'Data received and processed',
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to save sensor data'
            }), 500
        
    except Exception as e:
        logger.error(f"Error processing sensor data: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Server error: {str(e)}'
        }), 500

@sensor_bp.route('/current-data', methods=['GET'])
def get_current_data():
    """Get current sensor readings and system status"""
    try:
        # Get latest data from processor
        current_data = data_processor.get_latest_data()
        system_status = data_processor.get_system_status()
        health_data = data_processor.get_latest_health_data()
        
        return jsonify({
            'status': 'success',
            'data': current_data,
            'system_status': system_status,
            'health_data': health_data,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting current data: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@sensor_bp.route('/historical-data', methods=['GET'])
def get_historical_data():
    """Get historical sensor data for charts and analysis"""
    try:
        # Get query parameters
        hours = request.args.get('hours', 24, type=int)
        limit = request.args.get('limit', 1000, type=int)
        
        # Validate parameters
        if hours < 1 or hours > 8760:  # 1 hour to 1 year
            return jsonify({
                'status': 'error',
                'message': 'Hours parameter must be between 1 and 8760'
            }), 400
        
        if limit < 1 or limit > 10000:
            return jsonify({
                'status': 'error',
                'message': 'Limit parameter must be between 1 and 10000'
            }), 400
        
        # Get historical data
        df = db_manager.get_recent_data_df(hours=hours, limit=limit)
        
        if df.empty:
            return jsonify({
                'status': 'success',
                'data': [],
                'message': 'No historical data available',
                'parameters': {'hours': hours, 'limit': limit}
            }), 200
        
        # Convert to chart-friendly format
        chart_data = []
        for _, row in df.iterrows():
            chart_data.append({
                'timestamp': row['timestamp'].isoformat() if row['timestamp'] else None,
                'current': float(row['esp_current']) if row['esp_current'] else None,
                'voltage': float(row['esp_voltage']) if row['esp_voltage'] else None,
                'rpm': float(row['esp_rpm']) if row['esp_rpm'] else None,
                'motor_temp': float(row['plc_motor_temp']) if row['plc_motor_temp'] else None,
                'env_temp': float(row['env_temp_c']) if row['env_temp_c'] else None,
                'humidity': float(row['env_humidity']) if row['env_humidity'] else None,
                'overall_health_score': float(row['overall_health_score']) if row['overall_health_score'] else None,
                'electrical_health': float(row['electrical_health']) if row['electrical_health'] else None,
                'thermal_health': float(row['thermal_health']) if row['thermal_health'] else None,
                'mechanical_health': float(row['mechanical_health']) if row['mechanical_health'] else None,
                'predictive_health': float(row['predictive_health']) if row['predictive_health'] else None,
                'efficiency_score': float(row['efficiency_score']) if row['efficiency_score'] else None,
                'power': float(row['power_consumption']) if row['power_consumption'] else None
            })
        
        return jsonify({
            'status': 'success',
            'data': chart_data,
            'metadata': {
                'total_records': len(chart_data),
                'time_range_hours': hours,
                'oldest_record': chart_data[-1]['timestamp'] if chart_data else None,
                'newest_record': chart_data[0]['timestamp'] if chart_data else None
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving historical data: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@sensor_bp.route('/export-data', methods=['POST'])
def export_sensor_data():
    """Export sensor data to CSV file"""
    try:
        data = request.get_json() or {}
        
        # Parse date parameters
        start_date = None
        end_date = None
        
        if data.get('start_date'):
            start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))
        if data.get('end_date'):
            end_date = datetime.fromisoformat(data['end_date'].replace('Z', '+00:00'))
        
        # Export data
        export_path = db_manager.export_data_to_csv(start_date, end_date)
        
        return jsonify({
            'status': 'success',
            'message': 'Data exported successfully',
            'export_path': export_path,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error exporting sensor data: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@sensor_bp.route('/statistics', methods=['GET'])
def get_sensor_statistics():
    """Get sensor data statistics and metrics"""
    try:
        stats = db_manager.get_system_statistics()
        
        return jsonify({
            'status': 'success',
            'statistics': stats,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting sensor statistics: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
