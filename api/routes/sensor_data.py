"""
Sensor Data API Routes
Handles sensor data reception from all hardware sources and data retrieval endpoints.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

from database.manager import DatabaseManager
from services.data_processor import DataProcessor

logger = logging.getLogger(__name__)

# --- Blueprint Setup ---
sensor_bp = Blueprint('sensor', __name__)

# --- Service Initialization ---
# In a larger app, these would be managed via a service container or Flask's app context
# to avoid creating new instances on each import. For now, this is acceptable.
db_manager = DatabaseManager()
# We need to pass socketio to the data processor. This is a bit tricky here.
# A better approach would be to initialize this in the app factory and pass it down.
# For now, we'll leave it without socketio, meaning no real-time updates from this path.
data_processor = DataProcessor()

# --- API Endpoints ---

@sensor_bp.route('/send-data', methods=['POST'])
def receive_esp_data():
    """
    Receive sensor data from ESP devices. This is the primary endpoint for IoT sensor nodes.
    """
    raw_data = request.get_json()
    if not raw_data:
        logger.warning("Received request to /send-data with no JSON payload.")
        return jsonify({'status': 'error', 'message': 'No JSON data received'}), 400

    logger.info(f"Received ESP data: {raw_data}")
    
    # Delegate to the data processor
    success = data_processor.process_and_store_data(raw_data, source='esp')

    if success:
        return jsonify({'status': 'success', 'message': 'ESP data processed and stored.'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Failed to process ESP data.'}), 500

@sensor_bp.route('/plc-data', methods=['POST'])
def receive_plc_data():
    """
    Receive sensor data from the PLC. This endpoint is for industrial hardware integration.
    """
    raw_data = request.get_json()
    if not raw_data:
        logger.warning("Received request to /plc-data with no JSON payload.")
        return jsonify({'status': 'error', 'message': 'No JSON data received'}), 400
        
    logger.info(f"Received PLC data: {raw_data}")

    # Delegate to the data processor
    success = data_processor.process_and_store_data(raw_data, source='plc')

    if success:
        return jsonify({'status': 'success', 'message': 'PLC data processed and stored.'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Failed to process PLC data.'}), 500

@sensor_bp.route('/current-data', methods=['GET'])
def get_current_data():
    """Get latest combined sensor readings and system health."""
    try:
        latest_data = data_processor.get_latest_combined_data()
        health_data = data_processor.get_latest_health_data()
        
        return jsonify({
            'status': 'success',
            'data': latest_data,
            'health': health_data,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Error in get_current_data: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Server error retrieving current data.'}), 500

@sensor_bp.route('/historical-data', methods=['GET'])
def get_historical_data():
    """Get historical sensor data for charts and analysis."""
    try:
        hours = request.args.get('hours', 24, type=int)
        limit = request.args.get('limit', 1000, type=int)

        # Use the DatabaseManager to fetch data as a DataFrame
        df = db_manager.get_recent_data_df(hours=hours, limit=limit)
        
        if df.empty:
            return jsonify({'status': 'success', 'data': [], 'message': 'No historical data found.'}), 200
        
        # Convert DataFrame to list of dicts for JSON response
        chart_data = df.to_dict('records')
        
        return jsonify({
            'status': 'success',
            'data': chart_data,
            'metadata': {
                'records_count': len(chart_data),
                'time_range_hours': hours
            }
        }), 200
    except Exception as e:
        logger.error(f"Error in get_historical_data: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Server error retrieving historical data.'}), 500

@sensor_bp.route('/statistics', methods=['GET'])
def get_sensor_statistics():
    """Get comprehensive system statistics."""
    try:
        stats = db_manager.get_system_statistics()
        return jsonify({'status': 'success', 'statistics': stats}), 200
    except Exception as e:
        logger.error(f"Error in get_sensor_statistics: {e}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Server error retrieving statistics.'}), 500
