from flask import Flask, request, jsonify
import logging
from datetime import datetime

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/')
def index():
    return "Device Data Test Server - Ready to receive fake device data!"

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'service': 'Test Server'})

@app.route('/api/send-data', methods=['POST'])
def receive_esp_data():
    """Receive ESP8266 data"""
    data = request.get_json(force=True)
    if not data:
        return jsonify({'status': 'error', 'message': 'No JSON data received'}), 400
    
    logging.info(f"📡 ESP Data: Current={data.get('VAL1')}A, Voltage={data.get('VAL2')}V, RPM={data.get('VAL3')}")
    return jsonify({'status': 'success', 'message': 'ESP data received successfully'}), 200

@app.route('/api/plc-data', methods=['POST'])
def receive_plc_data():
    """Receive PLC data"""
    data = request.get_json(force=True)
    if not data:
        return jsonify({'status': 'error', 'message': 'No JSON data received'}), 400
    
    logging.info(f"🏭 PLC Data: Temp={data.get('motor_temp')}°C, Voltage={data.get('motor_voltage')}V, Status={data.get('plc_status')}")
    return jsonify({'status': 'success', 'message': 'PLC data received successfully'}), 200

if __name__ == '__main__':
    print("🚀 Starting Device Data Test Server...")
    print("📡 Ready to receive ESP8266 data at /api/send-data")
    print("🏭 Ready to receive PLC data at /api/plc-data")
    print("🌐 Server running at http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
