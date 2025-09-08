"""
Base Hardware Interface
Abstract base class for all hardware communication modules
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class BaseHardware(ABC):
    """Abstract base class for hardware communication"""
    
    def __init__(self, name: str):
        self.name = name
        self.connected = False
        self.last_data = {}
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    @abstractmethod
    def connect(self) -> bool:
        """Connect to hardware device"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """Disconnect from hardware device"""
        pass
    
    @abstractmethod
    def read_data(self) -> Dict:
        """Read data from hardware device"""
        pass
    
    def is_connected(self) -> bool:
        """Check if device is connected"""
        return self.connected
    
    def get_last_data(self) -> Dict:
        """Get last received data"""
        return self.last_data.copy()
    
    def log_info(self, message: str):
        """Log info message"""
        self.logger.info(f"[{self.name}] {message}")
    
    def log_error(self, message: str):
        """Log error message"""
        self.logger.error(f"[{self.name}] {message}")
    
    def log_warning(self, message: str):
        """Log warning message"""
        self.logger.warning(f"[{self.name}] {message}")
