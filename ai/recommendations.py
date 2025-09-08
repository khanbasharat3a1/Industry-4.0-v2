"""
AI Recommendations Engine
Generates smart recommendations based on health analysis and system status
"""

from typing import Dict, List
import logging
from datetime import datetime
from config.settings import config

logger = logging.getLogger(__name__)

class RecommendationsEngine:
    """Generates intelligent recommendations for motor maintenance and operation"""
    
    def __init__(self):
        self.name = "RecommendationsEngine"
    
    def generate_recommendations(self, health_data: Dict, connection_status: Dict) -> List[Dict]:
        """
        Generate comprehensive recommendations based on system analysis
        
        Args:
            health_data: Complete health analysis results
            connection_status: System connection status
            
        Returns:
            List of prioritized recommendations
        """
        recommendations = []
        
        # Connection status recommendations
        recommendations.extend(self._check_connection_issues(connection_status))
        
        # Health-based recommendations
        recommendations.extend(self._analyze_health_issues(health_data))
        
        # Performance optimization recommendations
        recommendations.extend(self._suggest_optimizations(health_data))
        
        # Preventive maintenance recommendations
        recommendations.extend(self._suggest_preventive_maintenance(health_data))
        
        # Sort recommendations by priority and return top results
        return self._prioritize_recommendations(recommendations)
    
    def _check_connection_issues(self, connection_status: Dict) -> List[Dict]:
        """Check for connection-related issues and generate alerts"""
        recommendations = []
        
        if not connection_status.get('esp_connected', False):
            recommendations.append({
                'type': 'Connection Alert',
                'category': 'System',
                'severity': 'HIGH',
                'priority': 'HIGH',
                'title': 'ESP/Arduino Disconnected',
                'description': 'ESP sensor module is not sending data. Sensor monitoring unavailable.',
                'action': 'Check ESP power supply, network connectivity, and sensor wiring connections.',
                'confidence': 1.0,
                'urgency': 'immediate',
                'estimated_downtime': '5-15 minutes'
            })
        
        if not connection_status.get('plc_connected', False):
            recommendations.append({
                'type': 'Connection Alert', 
                'category': 'System',
                'severity': 'HIGH',
                'priority': 'HIGH',
                'title': 'FX5U PLC Communication Lost',
                'description': 'FX5U PLC is not responding. Motor temperature and voltage monitoring unavailable.',
                'action': 'Verify FX5U network settings, check MC protocol configuration on port 5007, and ensure PLC is powered.',
                'confidence': 1.0,
                'urgency': 'immediate',
                'estimated_downtime': '10-30 minutes'
            })
        
        return recommendations
    
    def _analyze_health_issues(self, health_data: Dict) -> List[Dict]:
        """Analyze health data and generate specific recommendations"""
        recommendations = []
        
        overall_score = health_data.get('overall_health_score', 0)
        
        # Critical overall health
        if overall_score < 60:
            recommendations.append({
                'type': 'Critical Health Alert',
                'category': 'Health',
                'severity': 'CRITICAL',
                'priority': 'CRITICAL',
                'title': 'Motor Health Critical',
                'description': f'Overall motor health is {overall_score}%. Multiple systems showing degradation.',
                'action': 'IMMEDIATE ACTION REQUIRED: Stop motor operation and perform comprehensive inspection.',
                'confidence': 0.95,
                'urgency': 'immediate',
                'estimated_downtime': '2-8 hours'
            })
        elif overall_score < 75:
            recommendations.append({
                'type': 'Health Warning',
                'category': 'Health',
                'severity': 'MEDIUM',
                'priority': 'HIGH',
                'title': 'Motor Health Degraded',
                'description': f'Overall motor health is {overall_score}%. Preventive action recommended.',
                'action': 'Schedule maintenance inspection within 24-48 hours to prevent further degradation.',
                'confidence': 0.8,
                'urgency': 'within_24h',
                'estimated_downtime': '1-4 hours'
            })
        
        # Electrical system issues
        if health_data.get('electrical_health', 0) < 70:
            electrical_issues = health_data.get('issues', {}).get('electrical', [])
            recommendations.append({
                'type': 'Electrical System Warning',
                'category': 'Electrical',
                'severity': 'MEDIUM',
                'priority': 'MEDIUM',
                'title': 'Electrical System Issues Detected',
                'description': f"Electrical health: {health_data.get('electrical_health', 0)}%. " + '; '.join(electrical_issues[:2]),
                'action': 'Check 24V motor power connections, measure voltage/current with multimeter, inspect contactors and wiring.',
                'confidence': 0.8,
                'urgency': 'within_week',
                'estimated_downtime': '30 minutes - 2 hours'
            })
        
        # Thermal system issues
        if health_data.get('thermal_health', 0) < 70:
            thermal_issues = health_data.get('issues', {}).get('thermal', [])
            recommendations.append({
                'type': 'Thermal Management Warning',
                'category': 'Thermal',
                'severity': 'MEDIUM',
                'priority': 'MEDIUM',
                'title': 'Thermal Management Issues',
                'description': f"Thermal health: {health_data.get('thermal_health', 0)}%. " + '; '.join(thermal_issues[:2]),
                'action': 'Improve ventilation, clean cooling vents, check fan operation, verify ambient temperature control.',
                'confidence': 0.85,
                'urgency': 'within_24h',
                'estimated_downtime': '1-3 hours'
            })
        
        # Mechanical system issues
        if health_data.get('mechanical_health', 0) < 70:
            mechanical_issues = health_data.get('issues', {}).get('mechanical', [])
            recommendations.append({
                'type': 'Mechanical System Warning',
                'category': 'Mechanical',
                'severity': 'MEDIUM',
                'priority': 'MEDIUM',
                'title': 'Mechanical Performance Issues',
                'description': f"Mechanical health: {health_data.get('mechanical_health', 0)}%. " + '; '.join(mechanical_issues[:2]),
                'action': 'Inspect motor bearings, check shaft coupling alignment, verify load conditions, lubricate if needed.',
                'confidence': 0.8,
                'urgency': 'within_week',
                'estimated_downtime': '2-6 hours'
            })
        
        return recommendations
    
    def _suggest_optimizations(self, health_data: Dict) -> List[Dict]:
        """Suggest performance optimizations"""
        recommendations = []
        
        # Efficiency optimization
        efficiency = health_data.get('efficiency_score', 0)
        if efficiency < 75:
            recommendations.append({
                'type': 'Efficiency Optimization',
                'category': 'Performance',
                'severity': 'LOW',
                'priority': 'MEDIUM',
                'title': 'Motor Efficiency Below Optimal',
                'description': f'Current efficiency: {efficiency}%. Motor operating below optimal performance levels.',
                'action': 'Consider load optimization, check for mechanical wear, verify operating speed settings, review duty cycle.',
                'confidence': 0.7,
                'urgency': 'within_month',
                'estimated_downtime': '2-4 hours',
                'potential_savings': 'Energy cost reduction: 5-15%'
            })
        
        # Load balancing recommendation
        mechanical_health = health_data.get('mechanical_health', 100)
        if mechanical_health < 85 and 'imbalance' in str(health_data.get('issues', {}).get('mechanical', [])):
            recommendations.append({
                'type': 'Load Balancing',
                'category': 'Performance',
                'severity': 'LOW',
                'priority': 'MEDIUM',
                'title': 'Load Imbalance Detected',
                'description': 'Current and RPM correlation indicates potential load imbalance.',
                'action': 'Review load distribution, check for binding in driven equipment, verify belt tension if applicable.',
                'confidence': 0.75,
                'urgency': 'within_month',
                'estimated_downtime': '1-3 hours'
            })
        
        return recommendations
    
    def _suggest_preventive_maintenance(self, health_data: Dict) -> List[Dict]:
        """Suggest preventive maintenance actions"""
        recommendations = []
        
        # Predictive maintenance based on trends
        predictive_health = health_data.get('predictive_health', 100)
        if predictive_health < 60:
            predictive_issues = health_data.get('issues', {}).get('predictive', [])
            recommendations.append({
                'type': 'Predictive Maintenance',
                'category': 'Predictive',
                'severity': 'MEDIUM',
                'priority': 'MEDIUM',
                'title': 'Maintenance Required Soon',
                'description': f"Predictive analysis indicates declining performance. " + '; '.join(predictive_issues[:2]),
                'action': 'Schedule comprehensive preventive maintenance within next 7 days to prevent unexpected failures.',
                'confidence': 0.75,
                'urgency': 'within_week',
                'estimated_downtime': '4-8 hours',
                'maintenance_type': 'comprehensive'
            })
        
        # General preventive maintenance reminder
        overall_score = health_data.get('overall_health_score', 100)
        if 75 <= overall_score < 90:
            recommendations.append({
                'type': 'Routine Maintenance',
                'category': 'Preventive',
                'severity': 'LOW',
                'priority': 'LOW',
                'title': 'Routine Maintenance Recommended',
                'description': 'System performing well but routine maintenance will ensure continued reliability.',
                'action': 'Schedule routine maintenance: lubrication, cleaning, connection tightening, and general inspection.',
                'confidence': 0.6,
                'urgency': 'within_month',
                'estimated_downtime': '2-4 hours',
                'maintenance_type': 'routine'
            })
        
        return recommendations
    
    def _prioritize_recommendations(self, recommendations: List[Dict]) -> List[Dict]:
        """Sort and prioritize recommendations"""
        
        # Priority scoring
        priority_weights = {
            'CRITICAL': 4,
            'HIGH': 3,
            'MEDIUM': 2,
            'LOW': 1
        }
        
        severity_weights = {
            'CRITICAL': 4,
            'HIGH': 3,
            'MEDIUM': 2,
            'LOW': 1
        }
        
        urgency_weights = {
            'immediate': 4,
            'within_24h': 3,
            'within_week': 2,
            'within_month': 1
        }
        
        # Calculate composite priority score for each recommendation
        for rec in recommendations:
            priority_score = priority_weights.get(rec.get('priority', 'LOW'), 1)
            severity_score = severity_weights.get(rec.get('severity', 'LOW'), 1)
            urgency_score = urgency_weights.get(rec.get('urgency', 'within_month'), 1)
            confidence = rec.get('confidence', 0.5)
            
            # Composite score with weights
            rec['composite_score'] = (
                priority_score * 0.4 +
                severity_score * 0.3 +
                urgency_score * 0.2 +
                confidence * 0.1
            )
            
            # Add timestamp
            rec['generated_at'] = datetime.now().isoformat()
        
        # Sort by composite score (highest first) and return top 10
        sorted_recommendations = sorted(recommendations, key=lambda x: x['composite_score'], reverse=True)
        
        return sorted_recommendations[:10]
    
    def get_recommendation_summary(self, recommendations: List[Dict]) -> Dict:
        """Generate a summary of recommendations"""
        if not recommendations:
            return {
                'total_count': 0,
                'critical_count': 0,
                'high_priority_count': 0,
                'immediate_action_required': False,
                'estimated_total_downtime': '0 hours',
                'summary_message': 'No recommendations at this time. System operating normally.'
            }
        
        # Count by severity and priority
        critical_count = len([r for r in recommendations if r.get('severity') == 'CRITICAL'])
        high_priority_count = len([r for r in recommendations if r.get('priority') == 'HIGH'])
        immediate_count = len([r for r in recommendations if r.get('urgency') == 'immediate'])
        
        # Generate summary message
        if critical_count > 0:
            summary_message = f"CRITICAL: {critical_count} critical issues require immediate attention."
        elif high_priority_count > 0:
            summary_message = f"WARNING: {high_priority_count} high priority issues detected."
        else:
            summary_message = f"NOTICE: {len(recommendations)} optimization opportunities available."
        
        return {
            'total_count': len(recommendations),
            'critical_count': critical_count,
            'high_priority_count': high_priority_count,
            'immediate_action_required': immediate_count > 0,
            'categories': list(set([r.get('category', 'Unknown') for r in recommendations])),
            'top_priority': recommendations[0] if recommendations else None,
            'summary_message': summary_message
        }
