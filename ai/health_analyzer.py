"""
Motor Health Analyzer
Advanced AI-powered health analysis with categorized scoring
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging
from config.settings import config

logger = logging.getLogger(__name__)

class MotorHealthAnalyzer:
    """Comprehensive motor health analysis with AI capabilities"""
    
    def __init__(self):
        self.name = "HealthAnalyzer"
        
    def calculate_electrical_health(self, data: Dict) -> Tuple[float, List[str]]:
        """
        Calculate electrical system health score (0-100)
        
        Args:
            data: Current sensor data dictionary
            
        Returns:
            Tuple of (health_score, issues_list)
        """
        score = 100.0
        issues = []
        
        # Get electrical parameters
        voltage = data.get('esp_voltage') or data.get('plc_motor_voltage')
        current = data.get('esp_current')
        
        if voltage is None and current is None:
            return 0.0, ["No electrical data available"]
        
        # Voltage health assessment
        if voltage is not None:
            if voltage < config.thresholds.voltage_min_critical:
                score -= 40
                issues.append(f"Critical undervoltage: {voltage:.1f}V (min: {config.thresholds.voltage_min_critical}V)")
            elif voltage < config.thresholds.voltage_min_warning:
                score -= 20
                issues.append(f"Low voltage warning: {voltage:.1f}V (optimal: {config.optimal.voltage}V)")
            elif voltage > config.thresholds.voltage_max_critical:
                score -= 40
                issues.append(f"Critical overvoltage: {voltage:.1f}V (max: {config.thresholds.voltage_max_critical}V)")
            elif voltage > config.thresholds.voltage_max_warning:
                score -= 20
                issues.append(f"High voltage warning: {voltage:.1f}V (optimal: {config.optimal.voltage}V)")
        
        # Current health assessment
        if current is not None:
            if current < config.thresholds.current_min_warning:
                score -= 30
                issues.append(f"Motor underloaded: {current:.1f}A (min normal: {config.thresholds.current_min_warning}A)")
            elif current > config.thresholds.current_max_critical:
                score -= 50
                issues.append(f"Critical overcurrent: {current:.1f}A (max: {config.thresholds.current_max_critical}A)")
            elif current > config.thresholds.current_max_warning:
                score -= 25
                issues.append(f"Motor overloaded: {current:.1f}A (optimal: {config.optimal.current}A)")
        
        return max(0.0, min(100.0, score)), issues
    
    def calculate_thermal_health(self, data: Dict) -> Tuple[float, List[str]]:
        """
        Calculate thermal system health score (0-100)
        
        Args:
            data: Current sensor data dictionary
            
        Returns:
            Tuple of (health_score, issues_list)
        """
        score = 100.0
        issues = []
        
        # Get thermal parameters
        motor_temp = data.get('plc_motor_temp')
        env_temp = data.get('env_temp_c')
        humidity = data.get('env_humidity')
        
        if motor_temp is None and env_temp is None:
            return 0.0, ["No thermal data available"]
        
        # Motor temperature assessment
        if motor_temp is not None:
            if motor_temp > config.thresholds.motor_temp_critical:
                score -= 50
                issues.append(f"Critical motor temperature: {motor_temp:.1f}°C (max: {config.thresholds.motor_temp_critical}°C)")
            elif motor_temp > config.thresholds.motor_temp_warning:
                score -= 30
                issues.append(f"High motor temperature: {motor_temp:.1f}°C (optimal: <{config.thresholds.motor_temp_good}°C)")
            elif motor_temp > config.thresholds.motor_temp_good:
                score -= 15
                issues.append(f"Elevated motor temperature: {motor_temp:.1f}°C")
        
        # Environmental temperature assessment
        if env_temp is not None:
            if env_temp > config.thresholds.dht_temp_max_critical:
                score -= 25
                issues.append(f"Critical ambient temperature: {env_temp:.1f}°C")
            elif env_temp > config.thresholds.dht_temp_max_warning:
                score -= 15
                issues.append(f"High ambient temperature: {env_temp:.1f}°C (optimal: {config.optimal.dht_temp}°C)")
        
        # Humidity assessment
        if humidity is not None:
            if humidity > config.thresholds.dht_humidity_max_critical:
                score -= 20
                issues.append(f"Critical humidity level: {humidity:.1f}% (risk of condensation)")
            elif humidity > config.thresholds.dht_humidity_max_warning:
                score -= 10
                issues.append(f"High humidity: {humidity:.1f}% (optimal: {config.optimal.dht_humidity}%)")
            elif humidity < config.thresholds.dht_humidity_min_warning:
                score -= 5
                issues.append(f"Low humidity: {humidity:.1f}% (may cause static)")
        
        return max(0.0, min(100.0, score)), issues
    
    def calculate_mechanical_health(self, data: Dict) -> Tuple[float, List[str]]:
        """
        Calculate mechanical system health score (0-100)
        
        Args:
            data: Current sensor data dictionary
            
        Returns:
            Tuple of (health_score, issues_list)
        """
        score = 100.0
        issues = []
        
        # Get mechanical parameters
        rpm = data.get('esp_rpm')
        current = data.get('esp_current')
        
        if rpm is None:
            return 0.0, ["No RPM data available"]
        
        # RPM assessment
        if rpm < config.thresholds.rpm_min_critical:
            score -= 50
            issues.append(f"Critical low RPM: {rpm:.0f} (min: {config.thresholds.rpm_min_critical})")
        elif rpm < config.thresholds.rpm_min_warning:
            score -= 30
            issues.append(f"Low RPM warning: {rpm:.0f} (optimal: {config.optimal.rpm})")
        elif rpm > config.thresholds.rpm_max_critical:
            score -= 50
            issues.append(f"Critical high RPM: {rpm:.0f} (max: {config.thresholds.rpm_max_critical})")
        elif rpm > config.thresholds.rpm_max_warning:
            score -= 30
            issues.append(f"High RPM warning: {rpm:.0f} (optimal: {config.optimal.rpm})")
        
        # Current vs RPM correlation check (load balance)
        if current is not None and rpm > 0:
            expected_current = (rpm / config.optimal.rpm) * config.optimal.current
            if expected_current > 0:
                current_deviation = abs(current - expected_current) / expected_current
                
                if current_deviation > 0.5:  # >50% deviation indicates imbalance
                    score -= 20
                    issues.append(f"Current/RPM imbalance detected (Current: {current:.1f}A, RPM: {rpm:.0f})")
        
        return max(0.0, min(100.0, score)), issues
    
    def calculate_predictive_health(self, recent_data: pd.DataFrame) -> Tuple[float, List[str]]:
        """
        Calculate predictive health based on trends and patterns
        
        Args:
            recent_data: DataFrame with recent sensor readings
            
        Returns:
            Tuple of (health_score, issues_list)
        """
        score = 100.0
        issues = []
        
        if len(recent_data) < 5:
            return 50.0, ["Insufficient historical data for prediction"]
        
        try:
            # Temperature trend analysis
            if 'plc_motor_temp' in recent_data.columns:
                temp_data = recent_data['plc_motor_temp'].dropna().tail(10)
                if len(temp_data) >= 5:
                    # Calculate temperature slope
                    x = np.arange(len(temp_data))
                    temp_slope = np.polyfit(x, temp_data, 1)[0]
                    
                    if temp_slope > 1.0:  # Temperature rising >1°C per reading
                        score -= 30
                        issues.append(f"Rising temperature trend: +{temp_slope:.1f}°C/reading")
                    elif temp_slope > 0.5:  # Moderate temperature rise
                        score -= 15
                        issues.append(f"Moderate temperature rise: +{temp_slope:.1f}°C/reading")
            
            # Current stability analysis
            if 'esp_current' in recent_data.columns:
                current_data = recent_data['esp_current'].dropna().tail(10)
                if len(current_data) >= 5:
                    # Calculate current variation
                    current_std = current_data.std()
                    current_mean = current_data.mean()
                    
                    if current_mean > 0:
                        variation_coefficient = current_std / current_mean
                        
                        if variation_coefficient > 0.3:  # High variation
                            score -= 25
                            issues.append(f"High current instability: {variation_coefficient:.2f} coefficient")
                        elif variation_coefficient > 0.2:  # Moderate variation
                            score -= 10
                            issues.append(f"Moderate current variation: {variation_coefficient:.2f} coefficient")
            
            # Health degradation trend
            if 'overall_health_score' in recent_data.columns:
                health_data = recent_data['overall_health_score'].dropna().tail(20)
                if len(health_data) >= 10:
                    x = np.arange(len(health_data))
                    health_slope = np.polyfit(x, health_data, 1)[0]
                    
                    if health_slope < -1.0:  # Health declining >1 point per reading
                        score -= 35
                        issues.append(f"Health degradation trend: {health_slope:.1f} points/reading")
                    elif health_slope < -0.5:  # Moderate health decline
                        score -= 15
                        issues.append(f"Moderate health decline: {health_slope:.1f} points/reading")
            
            # Anomaly pattern detection
            anomaly_score = self._detect_anomaly_patterns(recent_data)
            if anomaly_score > 0:
                score -= anomaly_score
                issues.append(f"Anomaly patterns detected in recent data")
        
        except Exception as e:
            logger.error(f"Error in predictive analysis: {e}")
            issues.append("Predictive analysis error")
        
        return max(0.0, min(100.0, score)), issues
    
    def _detect_anomaly_patterns(self, data: pd.DataFrame) -> float:
        """
        Detect anomaly patterns in recent data
        
        Args:
            data: Recent sensor data
            
        Returns:
            Anomaly penalty score (0-40)
        """
        penalty = 0.0
        
        try:
            # Check for data gaps
            if len(data) < 10:
                penalty += 10  # Insufficient data is itself an anomaly
            
            # Check for sensor reading anomalies
            numeric_columns = ['esp_current', 'esp_voltage', 'esp_rpm', 'plc_motor_temp']
            
            for col in numeric_columns:
                if col in data.columns:
                    col_data = data[col].dropna()
                    if len(col_data) >= 5:
                        # Check for outliers using IQR method
                        Q1 = col_data.quantile(0.25)
                        Q3 = col_data.quantile(0.75)
                        IQR = Q3 - Q1
                        
                        lower_bound = Q1 - 1.5 * IQR
                        upper_bound = Q3 + 1.5 * IQR
                        
                        outliers = col_data[(col_data < lower_bound) | (col_data > upper_bound)]
                        outlier_ratio = len(outliers) / len(col_data)
                        
                        if outlier_ratio > 0.3:  # >30% outliers
                            penalty += 10
                        elif outlier_ratio > 0.15:  # >15% outliers
                            penalty += 5
        
        except Exception as e:
            logger.error(f"Error in anomaly detection: {e}")
        
        return min(penalty, 40.0)  # Cap penalty at 40 points
    
    def calculate_comprehensive_health(self, current_data: Dict, recent_data: Optional[pd.DataFrame] = None) -> Dict:
        """
        Calculate comprehensive health scores with detailed breakdown
        
        Args:
            current_data: Current sensor readings
            recent_data: Historical data for trend analysis
            
        Returns:
            Complete health analysis dictionary
        """
        
        # Calculate individual health components
        electrical_score, electrical_issues = self.calculate_electrical_health(current_data)
        thermal_score, thermal_issues = self.calculate_thermal_health(current_data)
        mechanical_score, mechanical_issues = self.calculate_mechanical_health(current_data)
        
        if recent_data is not None and len(recent_data) > 0:
            predictive_score, predictive_issues = self.calculate_predictive_health(recent_data)
        else:
            predictive_score, predictive_issues = 50.0, ["Limited historical data"]
        
        # Calculate weighted overall health score
        overall_score = (
            electrical_score * 0.30 +    # 30% weight - power system critical
            thermal_score * 0.35 +       # 35% weight - thermal most critical for motors  
            mechanical_score * 0.25 +    # 25% weight - mechanical performance
            predictive_score * 0.10      # 10% weight - predictive trends
        )
        
        # Calculate efficiency score
        efficiency_score = self.calculate_efficiency_score(current_data)
        
        # Determine overall status and classification
        if overall_score >= 90:
            status = "Excellent"
            status_class = "success"
        elif overall_score >= 75:
            status = "Good"
            status_class = "info"
        elif overall_score >= 60:
            status = "Warning"
            status_class = "warning"
        else:
            status = "Critical"
            status_class = "danger"
        
        return {
            'overall_health_score': round(overall_score, 1),
            'electrical_health': round(electrical_score, 1),
            'thermal_health': round(thermal_score, 1),
            'mechanical_health': round(mechanical_score, 1),
            'predictive_health': round(predictive_score, 1),
            'efficiency_score': round(efficiency_score, 1),
            'status': status,
            'status_class': status_class,
            'timestamp': current_data.get('timestamp', ''),
            'issues': {
                'electrical': electrical_issues,
                'thermal': thermal_issues,
                'mechanical': mechanical_issues,
                'predictive': predictive_issues
            },
            'summary': {
                'total_issues': len(electrical_issues) + len(thermal_issues) + len(mechanical_issues) + len(predictive_issues),
                'critical_issues': len([i for i in electrical_issues + thermal_issues + mechanical_issues if 'Critical' in i]),
                'warning_issues': len([i for i in electrical_issues + thermal_issues + mechanical_issues if 'warning' in i.lower()])
            }
        }
    
    def calculate_efficiency_score(self, data: Dict) -> float:
        """
        Calculate motor efficiency score based on power consumption and performance
        
        Args:
            data: Current sensor data
            
        Returns:
            Efficiency score (0-100)
        """
        voltage = data.get('esp_voltage') or data.get('plc_motor_voltage', 0)
        current = data.get('esp_current', 0)
        rpm = data.get('esp_rpm', 0)
        
        if not all([voltage, current, rpm]):
            return 0.0
        
        try:
            # Calculate actual vs theoretical efficiency
            actual_power = voltage * current / 1000  # kW
            theoretical_power = config.optimal.voltage * config.optimal.current / 1000
            
            # RPM efficiency (how close to optimal RPM)
            rpm_efficiency = min(100, (rpm / config.optimal.rpm) * 100) if config.optimal.rpm > 0 else 0
            
            # Power efficiency (theoretical vs actual)
            if actual_power > 0:
                power_efficiency = min(100, (theoretical_power / actual_power) * 100)
            else:
                power_efficiency = 0
            
            # Combined efficiency score
            overall_efficiency = (rpm_efficiency * 0.6 + power_efficiency * 0.4)
            
            return max(0.0, min(100.0, overall_efficiency))
        
        except Exception as e:
            logger.error(f"Error calculating efficiency: {e}")
            return 0.0
