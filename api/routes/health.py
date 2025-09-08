"""
Health Monitoring API Routes
Handles health analysis and monitoring endpoints
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

from database.manager import DatabaseManager
from ai.health_analyzer import MotorHealthAnalyzer
from services.data_processor import DataProcessor

logger = logging.getLogger(__name__)

# Create blueprint
health_bp = Blueprint('health', __name__)

# Initialize components
db_manager = DatabaseManager()
health_analyzer = MotorHealthAnalyzer()
data_processor = DataProcessor()

@health_bp.route('/health-details', methods=['GET'])
def get_health_details():
    """Get detailed health breakdown and analysis"""
    try:
        # Get latest health data
        health_data = data_processor.get_latest_health_data()
        
        if not health_data:
            return jsonify({
                'status': 'warning',
                'message': 'No health data available',
                'health_data': {
                    'overall_health_score': 0,
                    'electrical_health': 0,
                    'thermal_health': 0,
                    'mechanical_health': 0,
                    'predictive_health': 0,
                    'efficiency_score': 0,
                    'status': 'No Data',
                    'issues': {}
                }
            }), 200
        
        return jsonify({
            'status': 'success',
            'health_data': health_data,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting health details: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@health_bp.route('/health-trends', methods=['GET'])
def get_health_trends():
    """Get health trends over time"""
    try:
        hours = request.args.get('hours', 24, type=int)
        
        # Get historical data
        df = db_manager.get_recent_data_df(hours=hours)
        
        if df.empty:
            return jsonify({
                'status': 'success',
                'trends': [],
                'message': 'No trend data available'
            }), 200
        
        # Extract health trends
        health_columns = [
            'overall_health_score', 'electrical_health', 'thermal_health',
            'mechanical_health', 'predictive_health', 'efficiency_score'
        ]
        
        trends = []
        for _, row in df.iterrows():
            trend_point = {
                'timestamp': row['timestamp'].isoformat() if row['timestamp'] else None
            }
            
            for col in health_columns:
                trend_point[col] = float(row[col]) if row[col] is not None else None
            
            trends.append(trend_point)
        
        # Calculate trend statistics
        stats = {}
        for col in health_columns:
            values = [t[col] for t in trends if t[col] is not None]
            if values:
                stats[col] = {
                    'current': values[0] if values else None,
                    'average': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'trend': 'improving' if len(values) > 1 and values[0] > values[-1] else 'declining' if len(values) > 1 and values[0] < values[-1] else 'stable'
                }
        
        return jsonify({
            'status': 'success',
            'trends': trends,
            'statistics': stats,
            'time_range_hours': hours
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting health trends: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@health_bp.route('/recalculate-health', methods=['POST'])
def recalculate_health():
    """Manually trigger health recalculation"""
    try:
        data = request.get_json() or {}
        hours = data.get('hours', 1)  # Recalculate for last N hours
        
        # Get recent data for recalculation
        recent_data = db_manager.get_recent_data_df(hours=hours)
        
        if recent_data.empty:
            return jsonify({
                'status': 'warning',
                'message': 'No data available for recalculation'
            }), 200
        
        # Trigger recalculation through data processor
        result = data_processor.recalculate_health_scores(hours=hours)
        
        return jsonify({
            'status': 'success',
            'message': f'Health scores recalculated for {hours} hours',
            'result': result,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error recalculating health: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@health_bp.route('/health-summary', methods=['GET'])
def get_health_summary():
    """Get summarized health information"""
    try:
        # Get current health data
        health_data = data_processor.get_latest_health_data()
        
        # Get system statistics
        stats = db_manager.get_system_statistics()
        
        # Generate summary
        summary = {
            'overall_status': health_data.get('status', 'Unknown') if health_data else 'No Data',
            'overall_score': health_data.get('overall_health_score', 0) if health_data else 0,
            'critical_issues': 0,
            'warning_issues': 0,
            'system_uptime': stats.get('system_uptime_24h', 0),
            'active_alerts': stats.get('active_alerts', 0),
            'efficiency': health_data.get('efficiency_score', 0) if health_data else 0,
            'last_update': stats.get('last_reading_time')
        }
        
        # Count issues by severity
        if health_data and health_data.get('issues'):
            all_issues = []
            for category_issues in health_data['issues'].values():
                all_issues.extend(category_issues)
            
            summary['critical_issues'] = len([i for i in all_issues if 'Critical' in i or 'critical' in i])
            summary['warning_issues'] = len([i for i in all_issues if 'warning' in i.lower() or 'Warning' in i])
        
        # Determine overall health status
        score = summary['overall_score']
        if score >= 90:
            summary['health_status'] = 'excellent'
        elif score >= 75:
            summary['health_status'] = 'good'
        elif score >= 60:
            summary['health_status'] = 'warning'
        else:
            summary['health_status'] = 'critical'
        
        return jsonify({
            'status': 'success',
            'summary': summary,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting health summary: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
