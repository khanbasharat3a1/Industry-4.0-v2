"""
Logging Configuration
Centralized logging setup for the motor monitoring system
"""

import logging
import logging.handlers
import os
from datetime import datetime
from config.settings import config

def setup_logging():
    """Setup logging configuration for the entire application"""
    try:
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(config.logging.file)
        os.makedirs(log_dir, exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, config.logging.level.upper()))
        
        # Clear any existing handlers
        root_logger.handlers.clear()
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )
        
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            config.logging.file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)
        
        # Error file handler
        error_file = config.logging.file.replace('.log', '_error.log')
        error_handler = logging.handlers.RotatingFileHandler(
            error_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(error_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, config.logging.level.upper()))
        console_handler.setFormatter(simple_formatter)
        root_logger.addHandler(console_handler)
        
        # Set specific logger levels for third-party libraries
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('socketio').setLevel(logging.WARNING)
        logging.getLogger('engineio').setLevel(logging.WARNING)
        logging.getLogger('werkzeug').setLevel(logging.WARNING)
        
        # Log startup message
        root_logger.info("Logging system initialized successfully")
        root_logger.info(f"Log level: {config.logging.level.upper()}")
        root_logger.info(f"Log file: {config.logging.file}")
        
    except Exception as e:
        print(f"Error setting up logging: {e}")
        # Fallback to basic console logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)

def log_system_startup(component: str, version: str = None):
    """Log system component startup"""
    logger = get_logger('system.startup')
    
    startup_message = f"{component} starting up"
    if version:
        startup_message += f" (version {version})"
    
    logger.info("=" * 60)
    logger.info(startup_message)
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("=" * 60)

def log_system_shutdown(component: str):
    """Log system component shutdown"""
    logger = get_logger('system.shutdown')
    
    logger.info("=" * 60)
    logger.info(f"{component} shutting down")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("=" * 60)

class PerformanceTimer:
    """Context manager for performance timing"""
    
    def __init__(self, operation_name: str, logger_name: str = None):
        self.operation_name = operation_name
        self.logger = get_logger(logger_name or 'performance')
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.debug(f"Starting operation: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            
            if exc_type is None:
                self.logger.debug(f"Operation completed: {self.operation_name} ({duration:.3f}s)")
            else:
                self.logger.error(f"Operation failed: {self.operation_name} ({duration:.3f}s) - {exc_val}")

def setup_component_logger(component_name: str) -> logging.Logger:
    """
    Setup a dedicated logger for a component with specific formatting
    
    Args:
        component_name: Name of the component
        
    Returns:
        Configured logger instance
    """
    logger = get_logger(f'component.{component_name}')
    
    # Create component-specific log file if needed
    log_dir = os.path.dirname(config.logging.file)
    component_log_file = os.path.join(log_dir, f'{component_name.lower()}.log')
    
    # Add component-specific file handler if it doesn't exist
    has_component_handler = any(
        isinstance(handler, logging.FileHandler) and handler.baseFilename == component_log_file
        for handler in logger.handlers
    )
    
    if not has_component_handler:
        component_handler = logging.handlers.RotatingFileHandler(
            component_log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=2
        )
        component_handler.setLevel(logging.DEBUG)
        
        component_formatter = logging.Formatter(
            f'%(asctime)s - {component_name} - %(levelname)s - %(message)s'
        )
        component_handler.setFormatter(component_formatter)
        
        logger.addHandler(component_handler)
    
    return logger
