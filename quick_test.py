"""
Quick Device Test Script
Sends a few test data packets to verify API endpoints are working
"""

import requests
import json
from datetime import datetime

def test_esp_endpoint():
    """Test ESP data endpoint"""
    print("📡 Testing ESP8266 endpoint...")
    
    esp_data = {
        'TYPE': 'ADU_TEXT',
        'VAL1': '6.25',     # Current
        'VAL2': '24.1',     # Voltage
        'VAL3': '2750',     # RPM
        'VAL4': '42.5',     # Temperature
        'VAL5': '45.8',     # Humidity
        'VAL6': '108.5',    # Temp F
        'VAL7': '43.2',     # Heat Index C
        'VAL8': '109.8',    # Heat Index F
        'VAL9': 'ON',       # Relay 1
        'VAL10': 'OFF',     # Relay 2
        'VAL11': 'ON'       # Relay 3
    }
    
    try:
        response = requests.post('http://localhost:5000/api/send-data', 
                               json=esp_data, timeout=10)
        print(f"✅ ESP Response: {response.status_code}")
        if response.status_code == 200:
            print(f"📄 Response: {response.json()}")
    except Exception as e:
        print(f"❌ ESP Test failed: {e}")

def test_plc_endpoint():
    """Test PLC data endpoint"""
    print("🏭 Testing PLC endpoint...")
    
    plc_data = {
        'device_type': 'FX5U_PLC',
        'timestamp': datetime.now().isoformat(),
        'motor_temp': 42.5,
        'motor_voltage': 24.1,
        'motor_current': 6.25,
        'motor_rpm': 2750,
        'raw_d100': 2048,
        'raw_d102': 821,
        'plc_status': 'NORMAL'
    }
    
    try:
        response = requests.post('http://localhost:5000/api/plc-data', 
                               json=plc_data, timeout=10)
        print(f"✅ PLC Response: {response.status_code}")
        if response.status_code == 200:
            print(f"📄 Response: {response.json()}")
    except Exception as e:
        print(f"❌ PLC Test failed: {e}")

def test_health_endpoint():
    """Test health endpoint"""
    print("🏥 Testing health endpoint...")
    
    try:
        response = requests.get('http://localhost:5000/health', timeout=10)
        print(f"✅ Health Response: {response.status_code}")
        if response.status_code == 200:
            print(f"📄 Health: {response.json()}")
    except Exception as e:
        print(f"❌ Health test failed: {e}")

if __name__ == "__main__":
    print("🧪 Quick API Endpoint Test\n")
    
    test_health_endpoint()
    print()
    test_esp_endpoint()
    print()
    test_plc_endpoint()
    
    print("\n✅ Quick test completed!")
