"""
Database Manager
Handles all database operations and data management for the motor monitoring system
"""

import pandas as pd
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import desc, func, and_

from config.database import get_db_session, init_database
from config.settings import config
from database.models import SensorData, MaintenanceLog, SystemEvents, SystemConfiguration
from ai.health_analyzer import MotorHealthAnalyzer

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Comprehensive database management for motor monitoring system"""
    
    def __init__(self):
        self.name = "DatabaseManager"
        self.health_analyzer = MotorHealthAnalyzer()
        
        # Initialize database
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database tables and default configuration"""
        try:
            init_database()
            self._create_default_configuration()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def _create_default_configuration(self):
        """Create default system configuration entries"""
        default_configs = [
            ('system_name', 'AI Motor Monitoring System', 'string', 'System display name'),
            ('data_retention_days', str(config.data_retention_days), 'integer', 'Data retention period in days'),
            ('alert_email_enabled', 'false', 'boolean', 'Enable email alerts'),
            ('maintenance_reminder_interval', '168', 'integer', 'Maintenance reminder interval in hours'),
            ('auto_health_calculation', 'true', 'boolean', 'Enable automatic health score calculation')
        ]
        
        session = get_db_session()
        try:
            for key, value, type_name, description in default_configs:
                existing = session.query(SystemConfiguration).filter_by(config_key=key).first()
                if not existing:
                    config_entry = SystemConfiguration(
                        config_key=key,
                        config_value=value,
                        config_type=type_name,
                        description=description
                    )
                    session.add(config_entry)
            
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating default configuration: {e}")
        finally:
            session.close()
    
    def save_sensor_data(self, data: Dict, connection_status: Dict = None) -> bool:
        """
        Save sensor data with health analysis
        
        Args:
            data: Sensor data dictionary
            connection_status: System connection status
            
        Returns:
            True if successful, False otherwise
        """
        session = get_db_session()
        try:
            # Get recent data for predictive analysis
            recent_data = self.get_recent_data_df(hours=2, session=session)
            
            # Calculate comprehensive health scores
            health_data = self.health_analyzer.calculate_comprehensive_health(data, recent_data)
            
            # Calculate power consumption
            current = data.get('esp_current', 0) or 0
            voltage = data.get('esp_voltage', 0) or data.get('plc_motor_voltage', 0) or 0
            power_consumption = (current * voltage) / 1000 if current and voltage else None
            
            # Create sensor data record
            sensor_reading = SensorData(
                esp_current=data.get('esp_current'),
                esp_voltage=data.get('esp_voltage'),
                esp_rpm=data.get('esp_rpm'),
                env_temp_c=data.get('env_temp_c'),
                env_humidity=data.get('env_humidity'),
                env_temp_f=data.get('env_temp_f'),
                heat_index_c=data.get('heat_index_c'),
                heat_index_f=data.get('heat_index_f'),
                relay1_status=data.get('relay1_status'),
                relay2_status=data.get('relay2_status'),
                relay3_status=data.get('relay3_status'),
                combined_status=data.get('combined_status'),
                plc_motor_temp=data.get('plc_motor_temp'),
                plc_motor_voltage=data.get('plc_motor_voltage'),
                esp_connected=data.get('esp_connected', False),
                plc_connected=data.get('plc_connected', False),
                overall_health_score=health_data['overall_health_score'],
                electrical_health=health_data['electrical_health'],
                thermal_health=health_data['thermal_health'],
                mechanical_health=health_data['mechanical_health'],
                predictive_health=health_data['predictive_health'],
                efficiency_score=health_data['efficiency_score'],
                power_consumption=power_consumption
            )
            
            session.add(sensor_reading)
            
            # Generate and save critical alerts
            if connection_status:
                from ai.recommendations import RecommendationsEngine
                rec_engine = RecommendationsEngine()
                recommendations = rec_engine.generate_recommendations(health_data, connection_status)
                
                for rec in recommendations:
                    if rec['severity'] in ['HIGH', 'CRITICAL'] and rec['confidence'] > 0.8:
                        # Check for duplicate alerts (within last 30 minutes)
                        duplicate_check = session.query(MaintenanceLog).filter(
                            MaintenanceLog.alert_type == rec['type'],
                            MaintenanceLog.acknowledged == False,
                            MaintenanceLog.timestamp > datetime.utcnow() - timedelta(minutes=30)
                        ).first()
                        
                        if not duplicate_check:
                            alert = MaintenanceLog(
                                alert_type=rec['type'],
                                category=rec['category'],
                                severity=rec['severity'],
                                priority=rec['priority'],
                                description=rec['description'],
                                prediction_confidence=rec['confidence'],
                                recommended_action=rec['action']
                            )
                            session.add(alert)
            
            session.commit()
            logger.debug("Sensor data and health analysis saved successfully")
            return True
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error saving sensor data: {e}")
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving sensor data: {e}")
            return False
        finally:
            session.close()
    
    def get_recent_data_df(self, hours: int = 24, limit: int = None, session: Session = None) -> pd.DataFrame:
        """
        Get recent sensor data as DataFrame
        
        Args:
            hours: Hours of data to retrieve
            limit: Maximum number of records
            session: Database session (optional)
            
        Returns:
            DataFrame with sensor data
        """
        should_close_session = session is None
        if session is None:
            session = get_db_session()
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            query = session.query(SensorData).filter(
                SensorData.timestamp >= cutoff_time
            ).order_by(desc(SensorData.timestamp))
            
            if limit:
                query = query.limit(limit)
            
            # Convert to DataFrame
            data = pd.read_sql(query.statement, session.bind)
            return data
            
        except Exception as e:
            logger.error(f"Error retrieving recent data: {e}")
            return pd.DataFrame()
        finally:
            if should_close_session:
                session.close()
    
    def get_maintenance_alerts(self, acknowledged: bool = False, limit: int = 50) -> List[Dict]:
        """
        Get maintenance alerts
        
        Args:
            acknowledged: Include acknowledged alerts
            limit: Maximum number of alerts
            
        Returns:
            List of alert dictionaries
        """
        session = get_db_session()
        try:
            query = session.query(MaintenanceLog)
            
            if not acknowledged:
                query = query.filter(MaintenanceLog.acknowledged == False)
            
            alerts = query.order_by(desc(MaintenanceLog.timestamp)).limit(limit).all()
            
            result = []
            for alert in alerts:
                result.append({
                    'id': alert.id,
                    'timestamp': alert.timestamp.isoformat(),
                    'type': alert.alert_type,
                    'category': alert.category,
                    'severity': alert.severity,
                    'priority': alert.priority,
                    'description': alert.description,
                    'confidence': alert.prediction_confidence,
                    'action': alert.recommended_action,
                    'acknowledged': alert.acknowledged,
                    'acknowledged_by': alert.acknowledged_by
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error retrieving maintenance alerts: {e}")
            return []
        finally:
            session.close()
    
    def acknowledge_alert(self, alert_id: int, acknowledged_by: str = None) -> bool:
        """
        Acknowledge a maintenance alert
        
        Args:
            alert_id: Alert ID to acknowledge
            acknowledged_by: User acknowledging the alert
            
        Returns:
            True if successful, False otherwise
        """
        session = get_db_session()
        try:
            alert = session.query(MaintenanceLog).filter_by(id=alert_id).first()
            if alert:
                alert.acknowledged = True
                alert.acknowledged_by = acknowledged_by
                session.commit()
                
                # Log the acknowledgment
                self.log_system_event(
                    event_type='Alert_Acknowledged',
                    component='Web',
                    message=f'Alert {alert_id} acknowledged: {alert.alert_type}',
                    user_id=acknowledged_by,
                    session=session
                )
                
                return True
            return False
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error acknowledging alert {alert_id}: {e}")
            return False
        finally:
            session.close()
    
    def log_system_event(self, event_type: str, component: str, message: str, 
                        severity: str = 'INFO', details: str = None, 
                        user_id: str = None, session: Session = None) -> bool:
        """
        Log system event
        
        Args:
            event_type: Type of event
            component: System component
            message: Event message
            severity: Event severity
            details: Additional details
            user_id: Associated user ID
            session: Database session (optional)
            
        Returns:
            True if successful, False otherwise
        """
        should_close_session = session is None
        if session is None:
            session = get_db_session()
        
        try:
            event = SystemEvents(
                event_type=event_type,
                component=component,
                message=message,
                severity=severity,
                details=details,
                user_id=user_id
            )
            
            session.add(event)
            
            if should_close_session:
                session.commit()
            
            return True
            
        except Exception as e:
            if should_close_session:
                session.rollback()
            logger.error(f"Error logging system event: {e}")
            return False
        finally:
            if should_close_session:
                session.close()
    
    def get_system_statistics(self) -> Dict:
        """Get comprehensive system statistics"""
        session = get_db_session()
        try:
            # Get current counts
            total_readings = session.query(func.count(SensorData.id)).scalar()
            active_alerts = session.query(func.count(MaintenanceLog.id)).filter(
                MaintenanceLog.acknowledged == False
            ).scalar()
            
            # Get latest health score
            latest_reading = session.query(SensorData).order_by(desc(SensorData.timestamp)).first()
            current_health = latest_reading.overall_health_score if latest_reading else 0
            
            # Get recent performance metrics (last 24 hours)
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)
            recent_readings = session.query(SensorData).filter(
                SensorData.timestamp >= recent_cutoff
            ).all()
            
            # Calculate averages
            if recent_readings:
                avg_health = sum(r.overall_health_score for r in recent_readings if r.overall_health_score) / len(recent_readings)
                avg_efficiency = sum(r.efficiency_score for r in recent_readings if r.efficiency_score) / len(recent_readings)
                uptime_percentage = (sum(1 for r in recent_readings if r.esp_connected and r.plc_connected) / len(recent_readings)) * 100
            else:
                avg_health = avg_efficiency = uptime_percentage = 0
            
            return {
                'total_sensor_readings': total_readings,
                'active_alerts': active_alerts,
                'current_health_score': current_health,
                'average_health_24h': round(avg_health, 1),
                'average_efficiency_24h': round(avg_efficiency, 1),
                'system_uptime_24h': round(uptime_percentage, 1),
                'data_points_24h': len(recent_readings),
                'last_reading_time': latest_reading.timestamp.isoformat() if latest_reading else None
            }
            
        except Exception as e:
            logger.error(f"Error getting system statistics: {e}")
            return {}
        finally:
            session.close()
    
    def cleanup_old_data(self, days: int = None) -> Dict:
        """
        Clean up old data based on retention policy
        
        Args:
            days: Days of data to retain (uses config default if None)
            
        Returns:
            Cleanup statistics
        """
        if days is None:
            days = config.data_retention_days
        
        session = get_db_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Count records to be deleted
            old_sensor_data = session.query(SensorData).filter(SensorData.timestamp < cutoff_date).count()
            old_events = session.query(SystemEvents).filter(SystemEvents.timestamp < cutoff_date).count()
            old_alerts = session.query(MaintenanceLog).filter(
                and_(MaintenanceLog.timestamp < cutoff_date, MaintenanceLog.acknowledged == True)
            ).count()
            
            # Delete old records
            session.query(SensorData).filter(SensorData.timestamp < cutoff_date).delete()
            session.query(SystemEvents).filter(SystemEvents.timestamp < cutoff_date).delete()
            session.query(MaintenanceLog).filter(
                and_(MaintenanceLog.timestamp < cutoff_date, MaintenanceLog.acknowledged == True)
            ).delete()
            
            session.commit()
            
            cleanup_stats = {
                'sensor_data_deleted': old_sensor_data,
                'events_deleted': old_events,
                'alerts_deleted': old_alerts,
                'cutoff_date': cutoff_date.isoformat(),
                'retention_days': days
            }
            
            # Log cleanup event
            self.log_system_event(
                event_type='Data_Cleanup',
                component='Database',
                message=f'Data cleanup completed: {old_sensor_data + old_events + old_alerts} records removed',
                details=str(cleanup_stats),
                session=session
            )
            
            logger.info(f"Data cleanup completed: {cleanup_stats}")
            return cleanup_stats
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error during data cleanup: {e}")
            return {'error': str(e)}
        finally:
            session.close()
    
    def export_data_to_csv(self, start_date: datetime = None, end_date: datetime = None, 
                          output_path: str = None) -> str:
        """
        Export sensor data to CSV file
        
        Args:
            start_date: Start date for export
            end_date: End date for export  
            output_path: Output file path
            
        Returns:
            Path to exported file
        """
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"data/sensor_export_{timestamp}.csv"
        
        session = get_db_session()
        try:
            query = session.query(SensorData)
            
            if start_date:
                query = query.filter(SensorData.timestamp >= start_date)
            if end_date:
                query = query.filter(SensorData.timestamp <= end_date)
            
            query = query.order_by(SensorData.timestamp)
            
            # Export to DataFrame and then CSV
            df = pd.read_sql(query.statement, session.bind)
            df.to_csv(output_path, index=False)
            
            logger.info(f"Data exported to {output_path} ({len(df)} records)")
            return output_path
            
        except Exception as e:
            logger.error(f"Error exporting data to CSV: {e}")
            raise
        finally:
            session.close()
