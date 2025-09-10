"""
Batch Data Generator
Generates historical data for training AI models and testing analytics
"""

import json
import random
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

def generate_historical_data(days: int = 30, records_per_hour: int = 12):
    """Generate historical sensor data for training"""
    
    print(f"📊 Generating {days} days of historical data...")
    
    data_records = []
    start_date = datetime.now() - timedelta(days=days)
    
    # Time intervals (every 5 minutes)
    total_records = days * 24 * records_per_hour
    
    for i in range(total_records):
        timestamp = start_date + timedelta(minutes=i * (60 // records_per_hour))
        
        # Simulate different operational phases
        hour = timestamp.hour
        day_of_week = timestamp.weekday()
        
        # Working hours have higher load
        if 8 <= hour <= 17 and day_of_week < 5:
            load_factor = random.uniform(0.8, 1.2)
        elif 18 <= hour <= 22:
            load_factor = random.uniform(0.6, 0.9)
        else:
            load_factor = random.uniform(0.3, 0.7)
        
        # Occasional fault conditions (5% of time)
        fault_probability = 0.05
        is_fault = random.random() < fault_probability
        
        # Generate sensor values
        if is_fault:
            # Fault conditions
            current = random.uniform(8.0, 12.0)
            voltage = random.uniform(18.0, 22.0)
            rpm = random.randint(2000, 2500)
            motor_temp = random.uniform(60.0, 80.0)
            health_score = random.uniform(20.0, 50.0)
        else:
            # Normal conditions with load variation
            current = random.uniform(5.0, 7.5) * load_factor
            voltage = random.uniform(23.0, 25.0)
            rpm = random.randint(2650, 2850)
            motor_temp = random.uniform(35.0, 50.0) * load_factor
            health_score = random.uniform(75.0, 95.0)
        
        # Environmental conditions
        env_temp = random.uniform(20.0, 30.0)
        humidity = random.uniform(30.0, 70.0)
        
        # Create record
        record = {
            'timestamp': timestamp.isoformat(),
            'esp_current': round(current, 2),
            'esp_voltage': round(voltage, 1),
            'esp_rpm': int(rpm),
            'plc_motor_temp': round(motor_temp, 1),
            'env_temp_c': round(env_temp, 1),
            'env_humidity': round(humidity, 1),
            'overall_health_score': round(health_score, 1),
            'electrical_health': round(random.uniform(70, 95), 1),
            'thermal_health': round(random.uniform(65, 90), 1),
            'mechanical_health': round(random.uniform(75, 95), 1),
            'power_consumption': round((voltage * current) / 1000, 3),
            'relay1_status': 'ON' if current > 4.0 else 'OFF',
            'relay2_status': 'ON' if motor_temp > 45.0 else 'OFF',
            'relay3_status': 'ON' if is_fault else 'OFF',
            'is_fault': is_fault
        }
        
        data_records.append(record)
    
    # Save as JSON
    with open('historical_sensor_data.json', 'w') as f:
        json.dump(data_records, f, indent=2)
    
    # Save as CSV for analysis
    df = pd.DataFrame(data_records)
    df.to_csv('historical_sensor_data.csv', index=False)
    
    print(f"✅ Generated {len(data_records)} records")
    print(f"📁 Saved to: historical_sensor_data.json & historical_sensor_data.csv")
    
    # Print statistics
    fault_count = sum(1 for record in data_records if record['is_fault'])
    print(f"📈 Statistics:")
    print(f"  - Normal records: {len(data_records) - fault_count}")
    print(f"  - Fault records: {fault_count}")
    print(f"  - Fault rate: {fault_count/len(data_records)*100:.1f}%")
    
    return data_records

if __name__ == "__main__":
    generate_historical_data(days=30, records_per_hour=12)
