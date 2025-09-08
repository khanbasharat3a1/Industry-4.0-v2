"""
SQLAlchemy Database Models
All database table definitions for the motor monitoring system
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class SensorData(Base):
    """Sensor readings and calculated health metrics"""
    __tablename__ = 'sensor_data'
    
    # Primary key
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # ESP/Arduino Sensor Data
    esp_current = Column(Float, nullable=True, comment="Motor current in Amperes")
    esp_voltage = Column(Float, nullable=True, comment="Motor voltage in Volts")
    esp_rpm = Column(Float, nullable=True, comment="Motor RPM")
    env_temp_c = Column(Float, nullable=True, comment="Ambient temperature in Celsius")
    env_humidity = Column(Float, nullable=True, comment="Ambient humidity percentage")
    env_temp_f = Column(Float, nullable=True, comment="Ambient temperature in Fahrenheit")
    heat_index_c = Column(Float, nullable=True, comment="Heat index in Celsius")
    heat_index_f = Column(Float, nullable=True, comment="Heat index in Fahrenheit")
    
    # Relay Status
    relay1_status = Column(String(10), nullable=True, comment="Relay 1 status (ON/OFF)")
    relay2_status = Column(String(10), nullable=True, comment="Relay 2 status (ON/OFF)")
    relay3_status = Column(String(10), nullable=True, comment="Relay 3 status (ON/OFF)")
    combined_status = Column(String(10), nullable=True, comment="Combined relay status")
    
    # FX5U PLC Data
    plc_motor_temp = Column(Float, nullable=True, comment="Motor temperature from PLC in Celsius")
    plc_motor_voltage = Column(Float, nullable=True, comment="Motor voltage from PLC in Volts")
    
    # Connection Status
    esp_connected = Column(Boolean, default=False, comment="ESP connection status")
    plc_connected = Column(Boolean, default=False, comment="PLC connection status")
    
    # Calculated Health Metrics
    overall_health_score = Column(Float, nullable=True, comment="Overall health score (0-100)")
    electrical_health = Column(Float, nullable=True, comment="Electrical system health (0-100)")
    thermal_health = Column(Float, nullable=True, comment="Thermal system health (0-100)")
    mechanical_health = Column(Float, nullable=True, comment="Mechanical system health (0-100)")
    predictive_health = Column(Float, nullable=True, comment="Predictive health score (0-100)")
    efficiency_score = Column(Float, nullable=True, comment="Motor efficiency score (0-100)")
    power_consumption = Column(Float, nullable=True, comment="Calculated power consumption in kW")
    
    def __repr__(self):
        return f"<SensorData(id={self.id}, timestamp={self.timestamp}, health={self.overall_health_score})>"

class MaintenanceLog(Base):
    """Maintenance alerts and recommendations log"""
    __tablename__ = 'maintenance_log'
    
    # Primary key
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Alert Classification
    alert_type = Column(String(50), nullable=False, comment="Type of alert/recommendation")
    severity = Column(String(20), nullable=False, comment="Severity level (LOW/MEDIUM/HIGH/CRITICAL)")
    category = Column(String(30), nullable=False, comment="Category (System/Electrical/Thermal/Mechanical/etc)")
    priority = Column(String(20), nullable=False, comment="Priority level (LOW/MEDIUM/HIGH/CRITICAL)")
    
    # Alert Content
    description = Column(Text, nullable=False, comment="Detailed description of the issue")
    recommended_action = Column(Text, nullable=True, comment="Recommended corrective action")
    prediction_confidence = Column(Float, nullable=True, comment="AI confidence level (0-1)")
    
    # Status
    acknowledged = Column(Boolean, default=False, comment="Whether alert has been acknowledged")
    resolved = Column(Boolean, default=False, comment="Whether issue has been resolved")
    acknowledged_by = Column(String(100), nullable=True, comment="User who acknowledged the alert")
    resolved_by = Column(String(100), nullable=True, comment="User who resolved the issue")
    
    def __repr__(self):
        return f"<MaintenanceLog(id={self.id}, type={self.alert_type}, severity={self.severity})>"

class SystemEvents(Base):
    """System events and operational log"""
    __tablename__ = 'system_events'
    
    # Primary key
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Event Classification
    event_type = Column(String(50), nullable=False, comment="Type of event (Connection/Control/Error/Info)")
    component = Column(String(50), nullable=False, comment="System component (ESP/PLC/AI/Web)")
    severity = Column(String(20), default='INFO', comment="Event severity (INFO/WARNING/ERROR/CRITICAL)")
    
    # Event Content
    message = Column(Text, nullable=False, comment="Event description")
    details = Column(Text, nullable=True, comment="Additional event details")
    
    # Context Information
    user_id = Column(String(100), nullable=True, comment="User associated with event")
    session_id = Column(String(100), nullable=True, comment="Session identifier")
    ip_address = Column(String(45), nullable=True, comment="IP address (IPv4 or IPv6)")
    
    def __repr__(self):
        return f"<SystemEvents(id={self.id}, type={self.event_type}, component={self.component})>"

class SystemConfiguration(Base):
    """System configuration settings (stored in database)"""
    __tablename__ = 'system_configuration'
    
    # Primary key
    id = Column(Integer, primary_key=True)
    config_key = Column(String(100), nullable=False, unique=True, comment="Configuration key")
    config_value = Column(Text, nullable=False, comment="Configuration value")
    config_type = Column(String(20), default='string', comment="Value type (string/integer/float/boolean)")
    description = Column(Text, nullable=True, comment="Configuration description")
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String(100), nullable=True, comment="User who last updated")
    
    def __repr__(self):
        return f"<SystemConfiguration(key={self.config_key}, value={self.config_value})>"
