"""
Alerts and Maintenance API Routes
Handles maintenance alerts and recommendations
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

from database.manager import DatabaseManager
from ai.recommendations import RecommendationsEngine
from services.data_processor import DataProcessor
from services.alert_service import AlertService

logger = logging.getLogger(__name__)

# Create blueprint
alerts_bp = Blueprint('alerts', __name__)

# Initialize components
db_manager = DatabaseManager()
rec_engine = RecommendationsEngine()
data_processor = DataProcessor()
alert_service = AlertService()

@alerts_bp.route('/maintenance-alerts', methods=['GET'])
def get_maintenance_alerts():
    """Get maintenance alerts with filtering options"""
    try:
        # Get query parameters
        acknowledged = request.args.get('acknowledged', 'false').lower() == 'true'
        severity = request.args.get('severity')  # Filter by severity
        category = request.args.get('category')  # Filter by category
        limit = request.args.get('limit', 50, type=int)
        
        # Get alerts from database
        alerts = db_manager.get_maintenance_alerts(acknowledged=acknowledged, limit=limit)
        
        # Apply additional filters
        if severity:
            alerts = [a for a in alerts if a.get('severity', '').upper() == severity.upper()]
        
        if category:
            alerts = [a for a in alerts if a.get('category', '').lower() == category.lower()]
        
        # Get alert summary
        alert_summary = {
            'total_alerts': len(alerts),
            'critical_count': len([a for a in alerts if a.get('severity') == 'CRITICAL']),
            'high_count': len([a for a in alerts if a.get('severity') == 'HIGH']),
            'medium_count': len([a for a in alerts if a.get('severity') == 'MEDIUM']),
            'low_count': len([a for a in alerts if a.get('severity') == 'LOW']),
            'categories': list(set([a.get('category') for a in alerts if a.get('category')]))
        }
        
        return jsonify({
            'status': 'success',
            'alerts': alerts,
            'summary': alert_summary,
            'filters_applied': {
                'acknowledged': acknowledged,
                'severity': severity,
                'category': category,
                'limit': limit
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting maintenance alerts: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@alerts_bp.route('/recommendations', methods=['GET'])
def get_recommendations():
    """Get current AI-powered recommendations"""
    try:
        # Get current health and system status
        health_data = data_processor.get_latest_health_data()
        system_status = data_processor.get_system_status()
        
        if not health_data:
            return jsonify({
                'status': 'warning',
                'message': 'No health data available for recommendations',
                'recommendations': []
            }), 200
        
        # Generate recommendations
        recommendations = rec_engine.generate_recommendations(health_data, system_status)
        
        # Get recommendation summary
        rec_summary = rec_engine.get_recommendation_summary(recommendations)
        
        return jsonify({
            'status': 'success',
            'recommendations': recommendations,
            'summary': rec_summary,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@alerts_bp.route('/acknowledge-alert/<int:alert_id>', methods=['POST'])
def acknowledge_alert(alert_id):
    """Acknowledge a maintenance alert"""
    try:
        data = request.get_json() or {}
        acknowledged_by = data.get('acknowledged_by', 'Web User')
        notes = data.get('notes', '')
        
        # Acknowledge the alert
        success = db_manager.acknowledge_alert(alert_id, acknowledged_by)
        
        if success:
            # Log the acknowledgment
            db_manager.log_system_event(
                event_type='Alert_Acknowledged',
                component='Web',
                message=f'Alert {alert_id} acknowledged by {acknowledged_by}',
                details=f'Notes: {notes}' if notes else None,
                user_id=acknowledged_by
            )
            
            return jsonify({
                'status': 'success',
                'message': 'Alert acknowledged successfully',
                'alert_id': alert_id,
                'acknowledged_by': acknowledged_by
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': 'Alert not found or already acknowledged'
            }), 404
        
    except Exception as e:
        logger.error(f"Error acknowledging alert {alert_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@alerts_bp.route('/create-alert', methods=['POST'])
def create_manual_alert():
    """Create a manual maintenance alert"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No alert data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['alert_type', 'severity', 'category', 'description']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Create alert using alert service
        alert_id = alert_service.create_alert(
            alert_type=data['alert_type'],
            severity=data['severity'],
            category=data['category'],
            description=data['description'],
            recommended_action=data.get('recommended_action'),
            priority=data.get('priority', 'MEDIUM'),
            created_by=data.get('created_by', 'Manual Entry')
        )
        
        if alert_id:
            return jsonify({
                'status': 'success',
                'message': 'Alert created successfully',
                'alert_id': alert_id
            }), 201
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to create alert'
            }), 500
        
    except Exception as e:
        logger.error(f"Error creating manual alert: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@alerts_bp.route('/alert-statistics', methods=['GET'])
def get_alert_statistics():
    """Get alert statistics and trends"""
    try:
        days = request.args.get('days', 7, type=int)
        
        # Get alert statistics from alert service
        stats = alert_service.get_alert_statistics(days=days)
        
        return jsonify({
            'status': 'success',
            'statistics': stats,
            'time_period_days': days,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting alert statistics: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
