"""
ESP8266 & FX5U PLC Device Simulator
Comprehensive fake device simulator for AI Motor Monitoring System

Simulates:
- ESP8266 sensor data with realistic variations
- FX5U PLC motor parameters 
- Various operational scenarios (normal, warning, fault conditions)
- Real-time data streaming to API endpoints
"""

import time
import threading
import random
import requests
import json
import logging
from datetime import datetime
from typing import Dict, Any
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeviceSimulator:
    """Base class for device simulation"""
    
    def __init__(self, device_name: str, api_endpoint: str, interval: float = 5.0):
        self.device_name = device_name
        self.api_endpoint = api_endpoint
        self.interval = interval
        self.running = False
        self.thread = None
        
        # Simulation parameters
        self.simulation_mode = "normal"  # normal, warning, fault
        self.noise_factor = 0.1
        
        # Track last values for realistic trends
        self.last_values = {}
        
    def start(self):
        """Start the device simulation"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_simulation, daemon=True)
            self.thread.start()
            logger.info(f"✅ {self.device_name} simulator started")
    
    def stop(self):
        """Stop the device simulation"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info(f"🛑 {self.device_name} simulator stopped")
    
    def set_simulation_mode(self, mode: str):
        """Change simulation mode: normal, warning, fault"""
        self.simulation_mode = mode
        logger.info(f"🔧 {self.device_name} mode changed to: {mode}")
    
    def _run_simulation(self):
        """Main simulation loop"""
        while self.running:
            try:
                data = self.generate_data()
                self.send_data(data)
                time.sleep(self.interval)
            except Exception as e:
                logger.error(f"❌ {self.device_name} simulation error: {e}")
                time.sleep(self.interval)
    
    def generate_data(self) -> Dict[str, Any]:
        """Override this method in subclasses"""
        raise NotImplementedError
    
    def send_data(self, data: Dict[str, Any]):
        """Send data to API endpoint"""
        try:
            response = requests.post(
                self.api_endpoint,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"📡 {self.device_name} data sent successfully")
            else:
                logger.warning(f"⚠️ {self.device_name} API returned: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ {self.device_name} connection failed - server not running?")
        except requests.exceptions.Timeout:
            logger.error(f"⏰ {self.device_name} request timeout")
        except Exception as e:
            logger.error(f"❌ {self.device_name} send error: {e}")
    
    def add_realistic_noise(self, base_value: float, noise_factor: float = None) -> float:
        """Add realistic noise to sensor readings"""
        if noise_factor is None:
            noise_factor = self.noise_factor
            
        noise = random.uniform(-noise_factor, noise_factor) * base_value
        return base_value + noise
    
    def get_trending_value(self, key: str, base_value: float, max_change: float = 0.1):
        """Generate realistic trending values that don't jump dramatically"""
        if key not in self.last_values:
            self.last_values[key] = base_value
        
        # Add small random change
        change = random.uniform(-max_change, max_change)
        new_value = self.last_values[key] + change
        
        # Keep within reasonable bounds
        min_val = base_value * 0.8
        max_val = base_value * 1.2
        new_value = max(min_val, min(max_val, new_value))
        
        self.last_values[key] = new_value
        return new_value

class ESP8266Simulator(DeviceSimulator):
    """ESP8266/Arduino sensor simulator"""
    
    def __init__(self, api_endpoint: str = "http://localhost:5000/api/send-data", interval: float = 5.0):
        super().__init__("ESP8266", api_endpoint, interval)
        
        # ESP sensor baseline values
        self.baseline_values = {
            'current': 6.25,      # Amperes
            'voltage': 24.0,      # Volts
            'rpm': 2750,          # RPM
            'temp_c': 25.0,       # Celsius
            'humidity': 45.0,     # Percentage
            'temp_f': 77.0,       # Fahrenheit
            'heat_index_c': 26.0, # Heat index Celsius
            'heat_index_f': 78.8  # Heat index Fahrenheit
        }
    
    def generate_data(self) -> Dict[str, Any]:
        """Generate realistic ESP8266 sensor data"""
        
        # Adjust values based on simulation mode
        multipliers = self._get_mode_multipliers()
        
        # Generate sensor readings with realistic variations
        current = self.get_trending_value(
            'current', 
            self.baseline_values['current'] * multipliers['current'],
            0.2
        )
        
        voltage = self.get_trending_value(
            'voltage',
            self.baseline_values['voltage'] * multipliers['voltage'],
            0.5
        )
        
        rpm = self.get_trending_value(
            'rpm',
            self.baseline_values['rpm'] * multipliers['rpm'],
            50
        )
        
        temp_c = self.get_trending_value(
            'temp_c',
            self.baseline_values['temp_c'] * multipliers['temperature'],
            1.0
        )
        
        humidity = self.get_trending_value(
            'humidity',
            self.baseline_values['humidity'] * multipliers['humidity'],
            2.0
        )
        
        # Calculate derived values
        temp_f = (temp_c * 9/5) + 32
        heat_index_c = temp_c + (humidity / 100) * 2  # Simplified heat index
        heat_index_f = (heat_index_c * 9/5) + 32
        
        # Generate relay statuses based on conditions
        relay_statuses = self._generate_relay_statuses(current, voltage, temp_c)
        
        # Format data in ESP8266 protocol format
        esp_data = {
            'TYPE': 'ADU_TEXT',
            'VAL1': str(round(current, 2)),           # Current (A)
            'VAL2': str(round(voltage, 1)),           # Voltage (V)
            'VAL3': str(int(round(rpm))),             # RPM
            'VAL4': str(round(temp_c, 1)),            # Temperature (C)
            'VAL5': str(round(humidity, 1)),          # Humidity (%)
            'VAL6': str(round(temp_f, 1)),            # Temperature (F)
            'VAL7': str(round(heat_index_c, 1)),      # Heat Index (C)
            'VAL8': str(round(heat_index_f, 1)),      # Heat Index (F)
            'VAL9': relay_statuses[0],                # Relay 1
            'VAL10': relay_statuses[1],               # Relay 2
            'VAL11': relay_statuses[2],               # Relay 3
            'VAL12': 'NOR' if self.simulation_mode == 'normal' else 'ALM'  # Combined status
        }
        
        return esp_data
    
    def _get_mode_multipliers(self) -> Dict[str, float]:
        """Get multipliers based on simulation mode"""
        if self.simulation_mode == "normal":
            return {
                'current': random.uniform(0.95, 1.05),
                'voltage': random.uniform(0.98, 1.02),
                'rpm': random.uniform(0.98, 1.02),
                'temperature': random.uniform(0.9, 1.1),
                'humidity': random.uniform(0.9, 1.1)
            }
        elif self.simulation_mode == "warning":
            return {
                'current': random.uniform(1.1, 1.3),     # Higher current
                'voltage': random.uniform(0.9, 0.95),    # Lower voltage
                'rpm': random.uniform(0.95, 1.05),
                'temperature': random.uniform(1.2, 1.4), # Higher temperature
                'humidity': random.uniform(0.8, 1.2)
            }
        elif self.simulation_mode == "fault":
            return {
                'current': random.uniform(1.5, 2.0),     # Very high current
                'voltage': random.uniform(0.7, 0.9),     # Low voltage
                'rpm': random.uniform(0.8, 0.9),         # Low RPM
                'temperature': random.uniform(1.5, 2.0), # Very high temperature
                'humidity': random.uniform(0.7, 1.3)
            }
        else:
            return {key: 1.0 for key in ['current', 'voltage', 'rpm', 'temperature', 'humidity']}
    
    def _generate_relay_statuses(self, current: float, voltage: float, temp: float) -> list:
        """Generate realistic relay statuses based on conditions"""
        relays = ['OFF', 'OFF', 'OFF']
        
        # Relay 1: Main motor relay (ON if normal operation)
        if voltage > 22.0 and current < 10.0 and temp < 50.0:
            relays[0] = 'ON'
        
        # Relay 2: Cooling fan (ON if temperature high)
        if temp > 30.0:
            relays[1] = 'ON'
        
        # Relay 3: Alarm relay (ON if fault conditions)
        if current > 8.0 or voltage < 20.0 or temp > 60.0:
            relays[2] = 'ON'
        
        return relays

class FX5UPLCSimulator(DeviceSimulator):
    """FX5U PLC motor controller simulator"""
    
    def __init__(self, api_endpoint: str = "http://localhost:5000/api/plc-data", interval: float = 3.0):
        super().__init__("FX5U_PLC", api_endpoint, interval)
        
        # PLC baseline values
        self.baseline_values = {
            'motor_temp': 40.0,      # Motor temperature (°C)
            'motor_voltage': 24.0,   # Motor voltage (V)
            'motor_current': 6.25,   # Motor current (A)
            'motor_rpm': 2750,       # Motor RPM
            'power_consumption': 0.15 # Power consumption (kW)
        }
        
        # Raw ADC simulation values
        self.raw_d100_base = 2048  # D100 raw voltage reading
        self.raw_d102_base = 800   # D102 raw temperature reading
    
    def generate_data(self) -> Dict[str, Any]:
        """Generate realistic FX5U PLC data"""
        
        # Adjust values based on simulation mode
        multipliers = self._get_mode_multipliers()
        
        # Generate motor parameters
        motor_temp = self.get_trending_value(
            'motor_temp',
            self.baseline_values['motor_temp'] * multipliers['temperature'],
            1.5
        )
        
        motor_voltage = self.get_trending_value(
            'motor_voltage',
            self.baseline_values['motor_voltage'] * multipliers['voltage'],
            0.5
        )
        
        motor_current = self.get_trending_value(
            'motor_current',
            self.baseline_values['motor_current'] * multipliers['current'],
            0.3
        )
        
        motor_rpm = self.get_trending_value(
            'motor_rpm',
            self.baseline_values['motor_rpm'] * multipliers['rpm'],
            30
        )
        
        # Calculate power consumption
        power_consumption = (motor_voltage * motor_current) / 1000  # Convert to kW
        
        # Generate raw ADC values (simulate D100, D102 registers)
        raw_d100 = int(self.raw_d100_base * (motor_voltage / 24.0))
        raw_d102 = int(motor_temp / 0.05175)  # Temperature conversion formula
        
        # PLC status
        plc_status = self._get_plc_status(motor_temp, motor_voltage, motor_current)
        
        plc_data = {
            'device_type': 'FX5U_PLC',
            'timestamp': datetime.now().isoformat(),
            'connection_status': 'CONNECTED',
            'motor_temp': round(motor_temp, 1),
            'motor_voltage': round(motor_voltage, 2),
            'motor_current': round(motor_current, 2),
            'motor_rpm': int(round(motor_rpm)),
            'power_consumption': round(power_consumption, 3),
            'raw_d100': raw_d100,  # Raw voltage register
            'raw_d102': raw_d102,  # Raw temperature register
            'plc_status': plc_status,
            'error_code': 0 if self.simulation_mode == 'normal' else random.randint(1, 99),
            'operating_hours': random.randint(1000, 9999),
            'maintenance_due': self.simulation_mode == 'fault'
        }
        
        return plc_data
    
    def _get_mode_multipliers(self) -> Dict[str, float]:
        """Get multipliers based on simulation mode"""
        if self.simulation_mode == "normal":
            return {
                'temperature': random.uniform(0.95, 1.05),
                'voltage': random.uniform(0.98, 1.02),
                'current': random.uniform(0.95, 1.05),
                'rpm': random.uniform(0.98, 1.02)
            }
        elif self.simulation_mode == "warning":
            return {
                'temperature': random.uniform(1.15, 1.35),  # Higher temperature
                'voltage': random.uniform(0.92, 0.98),      # Lower voltage
                'current': random.uniform(1.1, 1.25),      # Higher current
                'rpm': random.uniform(0.95, 1.02)
            }
        elif self.simulation_mode == "fault":
            return {
                'temperature': random.uniform(1.4, 1.8),   # Very high temperature
                'voltage': random.uniform(0.8, 0.9),       # Low voltage
                'current': random.uniform(1.3, 1.8),      # Very high current
                'rpm': random.uniform(0.7, 0.85)          # Low RPM
            }
        else:
            return {key: 1.0 for key in ['temperature', 'voltage', 'current', 'rpm']}
    
    def _get_plc_status(self, temp: float, voltage: float, current: float) -> str:
        """Determine PLC status based on operating conditions"""
        if temp > 70.0 or voltage < 18.0 or current > 12.0:
            return 'FAULT'
        elif temp > 55.0 or voltage < 22.0 or current > 9.0:
            return 'WARNING'
        else:
            return 'NORMAL'

class ScenarioManager:
    """Manages different simulation scenarios"""
    
    def __init__(self):
        self.esp_sim = None
        self.plc_sim = None
        self.scenario_thread = None
        self.running_scenario = False
    
    def start_simulators(self):
        """Start both ESP and PLC simulators"""
        logger.info("🚀 Starting device simulators...")
        
        self.esp_sim = ESP8266Simulator()
        self.plc_sim = FX5UPLCSimulator()
        
        self.esp_sim.start()
        self.plc_sim.start()
        
        logger.info("✅ All simulators started successfully")
    
    def stop_simulators(self):
        """Stop all simulators"""
        logger.info("🛑 Stopping device simulators...")
        
        if self.esp_sim:
            self.esp_sim.stop()
        if self.plc_sim:
            self.plc_sim.stop()
            
        self.running_scenario = False
        
        logger.info("✅ All simulators stopped")
    
    def run_normal_operation(self, duration: int = 300):
        """Simulate normal operation for specified duration (seconds)"""
        logger.info(f"🔄 Running normal operation scenario for {duration} seconds")
        
        if self.esp_sim:
            self.esp_sim.set_simulation_mode("normal")
        if self.plc_sim:
            self.plc_sim.set_simulation_mode("normal")
    
    def run_warning_scenario(self, duration: int = 180):
        """Simulate warning conditions"""
        logger.info(f"⚠️ Running warning scenario for {duration} seconds")
        
        if self.esp_sim:
            self.esp_sim.set_simulation_mode("warning")
        if self.plc_sim:
            self.plc_sim.set_simulation_mode("warning")
        
        # Return to normal after duration
        def reset_to_normal():
            time.sleep(duration)
            if self.esp_sim:
                self.esp_sim.set_simulation_mode("normal")
            if self.plc_sim:
                self.plc_sim.set_simulation_mode("normal")
            logger.info("✅ Warning scenario completed - returned to normal")
        
        threading.Thread(target=reset_to_normal, daemon=True).start()
    
    def run_fault_scenario(self, duration: int = 60):
        """Simulate fault conditions"""
        logger.info(f"🚨 Running fault scenario for {duration} seconds")
        
        if self.esp_sim:
            self.esp_sim.set_simulation_mode("fault")
        if self.plc_sim:
            self.plc_sim.set_simulation_mode("fault")
        
        # Return to normal after duration
        def reset_to_normal():
            time.sleep(duration)
            if self.esp_sim:
                self.esp_sim.set_simulation_mode("normal")
            if self.plc_sim:
                self.plc_sim.set_simulation_mode("normal")
            logger.info("✅ Fault scenario completed - returned to normal")
        
        threading.Thread(target=reset_to_normal, daemon=True).start()
    
    def run_mixed_scenario(self):
        """Run a sequence of different scenarios"""
        logger.info("🎭 Running mixed scenario sequence...")
        
        def scenario_sequence():
            try:
                # Normal operation (5 minutes)
                self.run_normal_operation(300)
                time.sleep(300)
                
                # Warning condition (3 minutes)
                self.run_warning_scenario(180)
                time.sleep(180)
                
                # Normal operation (2 minutes)
                self.run_normal_operation(120)
                time.sleep(120)
                
                # Fault condition (1 minute)
                self.run_fault_scenario(60)
                time.sleep(60)
                
                # Return to normal
                self.run_normal_operation(300)
                
                logger.info("🎉 Mixed scenario sequence completed")
                
            except Exception as e:
                logger.error(f"❌ Scenario sequence error: {e}")
        
        self.scenario_thread = threading.Thread(target=scenario_sequence, daemon=True)
        self.scenario_thread.start()

def main():
    """Main simulator entry point"""
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║            🤖 ESP8266 & FX5U PLC Device Simulator 🤖                        ║
║                                                                              ║
║                     AI Motor Monitoring System Testing                      ║
║                                                                              ║
║  📡 ESP8266 Sensor Data     🏭 FX5U PLC Motor Data                         ║
║  ⚡ Real-time Streaming     🔧 Multiple Scenarios                           ║
║  📊 Realistic Variations    🚨 Fault Simulation                            ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    scenario_manager = ScenarioManager()
    
    try:
        # Start simulators
        scenario_manager.start_simulators()
        
        print("\n🎮 Available Commands:")
        print("  1 - Normal Operation")
        print("  2 - Warning Scenario")
        print("  3 - Fault Scenario")
        print("  4 - Mixed Scenario Sequence")
        print("  q - Quit")
        
        while True:
            try:
                command = input("\n🎯 Enter command (1-4 or q): ").strip().lower()
                
                if command == 'q' or command == 'quit':
                    break
                elif command == '1':
                    scenario_manager.run_normal_operation()
                elif command == '2':
                    scenario_manager.run_warning_scenario()
                elif command == '3':
                    scenario_manager.run_fault_scenario()
                elif command == '4':
                    scenario_manager.run_mixed_scenario()
                else:
                    print("❓ Invalid command. Use 1-4 or 'q' to quit.")
                    
            except KeyboardInterrupt:
                break
    
    except KeyboardInterrupt:
        print("\n🛑 Simulation interrupted by user")
    
    finally:
        scenario_manager.stop_simulators()
        print("👋 Device simulation ended")

if __name__ == "__main__":
    main()
