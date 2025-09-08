"""
Alert Service
Manages alert creation, processing, and statistics
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import func, desc, and_

from database.manager import DatabaseManager
from database.models import MaintenanceLog, SystemEvents
from config.database import get_db_session

logger = logging.getLogger(__name__)

class AlertService:
    """Service for managing maintenance alerts and notifications"""
    
    def __init__(self):
        self.name = "AlertService"
        self.db_manager = DatabaseManager()
    
    def create_alert(self, alert_type: str, severity: str, category: str, 
                    description: str, recommended_action: str = None,
                    priority: str = 'MEDIUM', created_by: str = None) -> Optional[int]:
        """
        Create a new maintenance alert
        
        Args:
            alert_type: Type of alert
            severity: Severity level (LOW/MEDIUM/HIGH/CRITICAL)
            category: Alert category
            description: Alert description
            recommended_action: Recommended action
            priority: Priority level
            created_by: User who created the alert
            
        Returns:
            Alert ID if successful, None otherwise
        """
        session = get_db_session()
        try:
            alert = MaintenanceLog(
                alert_type=alert_type,
                severity=severity.upper(),
                category=category,
                priority=priority.upper(),
                description=description,
                recommended_action=recommended_action,
                prediction_confidence=1.0  # Manual alerts have full confidence
            )
            
            session.add(alert)
            session.commit()
            
            alert_id = alert.id
            
            # Log alert creation
            self.db_manager.log_system_event(
                event_type='Alert_Created',
                component='AlertService',
                message=f'Manual alert created: {alert_type}',
                details=f'Severity: {severity}, Category: {category}',
                user_id=created_by,
                session=session
            )
            
            logger.info(f"Alert created successfully: ID={alert_id}, Type={alert_type}")
            return alert_id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating alert: {e}")
            return None
        finally:
            session.close()
    
    def get_alert_statistics(self, days: int = 7) -> Dict:
        """
        Get alert statistics for specified period
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with alert statistics
        """
        session = get_db_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Total alerts in period
            total_alerts = session.query(func.count(MaintenanceLog.id)).filter(
                MaintenanceLog.timestamp >= cutoff_date
            ).scalar()
            
            # Alerts by severity
            severity_stats = {}
            for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                count = session.query(func.count(MaintenanceLog.id)).filter(
                    and_(
                        MaintenanceLog.timestamp >= cutoff_date,
                        MaintenanceLog.severity == severity
                    )
                ).scalar()
                severity_stats[severity.lower()] = count
            
            # Alerts by category
            category_query = session.query(
                MaintenanceLog.category,
                func.count(MaintenanceLog.id).label('count')
            ).filter(
                MaintenanceLog.timestamp >= cutoff_date
            ).group_by(MaintenanceLog.category).all()
            
            category_stats = {row.category: row.count for row in category_query}
            
            # Acknowledgment statistics
            acknowledged_count = session.query(func.count(MaintenanceLog.id)).filter(
                and_(
                    MaintenanceLog.timestamp >= cutoff_date,
                    MaintenanceLog.acknowledged == True
                )
            ).scalar()
            
            # Recent trends (daily counts for the period)
            daily_trends = []
            for i in range(days):
                day_start = datetime.utcnow() - timedelta(days=i+1)
                day_end = datetime.utcnow() - timedelta(days=i)
                
                daily_count = session.query(func.count(MaintenanceLog.id)).filter(
                    and_(
                        MaintenanceLog.timestamp >= day_start,
                        MaintenanceLog.timestamp < day_end
                    )
                ).scalar()
                
                daily_trends.append({
                    'date': day_start.strftime('%Y-%m-%d'),
                    'alert_count': daily_count
                })
            
            # Top alert types
            top_types = session.query(
                MaintenanceLog.alert_type,
                func.count(MaintenanceLog.id).label('count')
            ).filter(
                MaintenanceLog.timestamp >= cutoff_date
            ).group_by(MaintenanceLog.alert_type).order_by(
                desc(func.count(MaintenanceLog.id))
            ).limit(5).all()
            
            return {
                'total_alerts': total_alerts,
                'severity_breakdown': severity_stats,
                'category_breakdown': category_stats,
                'acknowledged_count': acknowledged_count,
                'acknowledgment_rate': round((acknowledged_count / total_alerts * 100), 1) if total_alerts > 0 else 0,
                'daily_trends': list(reversed(daily_trends)),  # Most recent first
                'top_alert_types': [{'type': row.alert_type, 'count': row.count} for row in top_types],
                'analysis_period_days': days,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting alert statistics: {e}")
            return {'error': str(e)}
        finally:
            session.close()
    
    def get_alert_trends(self, hours: int = 24) -> Dict:
        """
        Get alert trends over specified time period
        
        Args:
            hours: Hours to analyze
            
        Returns:
            Alert trend analysis
        """
        session = get_db_session()
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Get alerts in time period
            alerts = session.query(MaintenanceLog).filter(
                MaintenanceLog.timestamp >= cutoff_time
            ).order_by(MaintenanceLog.timestamp).all()
            
            if not alerts:
                return {
                    'trend_analysis': 'No alerts in specified period',
                    'alert_rate': 0,
                    'hourly_distribution': [],
                    'peak_hours': []
                }
            
            # Calculate hourly distribution
            hourly_counts = {}
            for alert in alerts:
                hour = alert.timestamp.hour
                hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
            
            # Find peak hours
            peak_hours = sorted(hourly_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            
            # Calculate alert rate (alerts per hour)
            alert_rate = len(alerts) / hours
            
            # Trend analysis
            if len(alerts) >= 2:
                # Simple trend calculation based on first half vs second half
                midpoint = len(alerts) // 2
                first_half_rate = midpoint / (hours / 2)
                second_half_rate = (len(alerts) - midpoint) / (hours / 2)
                
                if second_half_rate > first_half_rate * 1.2:
                    trend = 'increasing'
                elif second_half_rate < first_half_rate * 0.8:
                    trend = 'decreasing'
                else:
                    trend = 'stable'
            else:
                trend = 'insufficient_data'
            
            return {
                'trend_analysis': trend,
                'alert_rate': round(alert_rate, 2),
                'total_alerts': len(alerts),
                'hourly_distribution': [{'hour': h, 'count': c} for h, c in sorted(hourly_counts.items())],
                'peak_hours': [{'hour': h, 'count': c} for h, c in peak_hours],
                'analysis_period_hours': hours
            }
            
        except Exception as e:
            logger.error(f"Error getting alert trends: {e}")
            return {'error': str(e)}
        finally:
            session.close()
