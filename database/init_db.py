"""
Database initialization and management
"""

import sqlite3
import os
from datetime import datetime, timedelta
import logging

def create_database():
    """Create database with proper schema"""
    db_path = os.path.join('database', 'sensor_history.db')
    os.makedirs('database', exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create sensor data table with all required fields
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            esp_current REAL DEFAULT 0,
            esp_voltage REAL DEFAULT 0,
            esp_rpm INTEGER DEFAULT 0,
            env_temp_c REAL DEFAULT 0,
            env_humidity REAL DEFAULT 0,
            esp_connected BOOLEAN DEFAULT 0,
            plc_motor_temp REAL DEFAULT 0,
            plc_motor_voltage REAL DEFAULT 0,
            plc_motor_current REAL DEFAULT 0,
            plc_motor_rpm INTEGER DEFAULT 0,
            plc_connected BOOLEAN DEFAULT 0,
            overall_health_score REAL DEFAULT 0,
            electrical_health REAL DEFAULT 0,
            thermal_health REAL DEFAULT 0,
            mechanical_health REAL DEFAULT 0,
            data_source TEXT DEFAULT 'unknown'
        )
    ''')
    
    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON sensor_data(timestamp DESC)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_health ON sensor_data(overall_health_score)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_connected ON sensor_data(esp_connected, plc_connected)')
    
    conn.commit()
    conn.close()
    
    logging.info("Database schema created successfully")

def seed_sample_data():
    """Seed database with sample historical data"""
    db_path = os.path.join('database', 'sensor_history.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Generate 24 hours of sample data
    base_time = datetime.now() - timedelta(hours=24)
    
    for i in range(288):  # Every 5 minutes for 24 hours
        timestamp = base_time + timedelta(minutes=i * 5)
        
        # Generate realistic sample data
        cursor.execute('''
            INSERT INTO sensor_data (
                timestamp, esp_current, esp_voltage, esp_rpm, env_temp_c, env_humidity,
                esp_connected, plc_motor_temp, plc_motor_voltage, plc_motor_current,
                plc_motor_rpm, plc_connected, overall_health_score, electrical_health,
                thermal_health, mechanical_health, data_source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timestamp.isoformat(),
            6.0 + (i % 20) * 0.1,  # Varying current
            24.0 + (i % 10) * 0.1,  # Varying voltage
            2750 + (i % 30),        # Varying RPM
            25.0 + (i % 15),        # Varying temp
            45.0 + (i % 20),        # Varying humidity
            1,  # Connected
            40.0 + (i % 12),        # Motor temp
            24.0 + (i % 8) * 0.1,   # Motor voltage
            6.0 + (i % 15) * 0.1,   # Motor current
            2750 + (i % 25),        # Motor RPM
            1,  # Connected
            85.0 + (i % 20),        # Overall health
            88.0 + (i % 15),        # Electrical health
            84.0 + (i % 18),        # Thermal health
            87.0 + (i % 16),        # Mechanical health
            'historical_sample'
        ))
    
    conn.commit()
    conn.close()
    
    logging.info("Sample historical data seeded successfully")

if __name__ == "__main__":
    create_database()
    seed_sample_data()
    print("✅ Database initialized with sample data")
