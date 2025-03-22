import logging
import os
from logging.handlers import RotatingFileHandler
import sys

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

def setup_logger(name='web3hackathon', log_level=logging.INFO):
    """
    Set up and configure logger with both file and console handlers
    
    Args:
        name: Logger name
        log_level: Logging level (default: INFO)
        
    Returns:
        Configured logger instance
    """
    # Create logger instance
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Clear existing handlers if any
    if logger.handlers:
        logger.handlers.clear()
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # File handler (rotating log files, max 5MB per file, keep 5 backup files)
    file_handler = RotatingFileHandler(
        os.path.join('logs', f'{name}.log'),
        maxBytes=5*1024*1024,
        backupCount=5
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(file_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Default application logger
app_logger = setup_logger() 