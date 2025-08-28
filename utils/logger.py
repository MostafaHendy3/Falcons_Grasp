"""
Logging utilities for Cage Game
Provides consistent logging across the application with file logging support
"""

import logging
import logging.handlers
import sys
import os
from datetime import datetime
from typing import Optional


def get_logger(name: str, level: str = "INFO", enable_file_logging: bool = True, game_prefix: str = "falcongrasp") -> logging.Logger:
    """
    Get a configured logger instance with automatic file logging
    
    Args:
        name: Logger name (usually __name__)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_file_logging: Whether to enable file logging (default: True)
        game_prefix: Prefix for the log file (default: "falcongrasp")
    
    Returns:
        Configured logger instance
    """
    
    # Create logger
    logger = logging.getLogger(name)
    
    # Don't add handlers if they already exist
    if logger.handlers:
        return logger
    
    # Set level
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Create formatter for console (with short timestamp)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    # Add console handler to logger
    logger.addHandler(console_handler)
    
    # Add file handler if enabled
    if enable_file_logging:
        try:
            file_handler = create_file_handler(log_level, game_prefix)
            if file_handler:
                logger.addHandler(file_handler)
        except Exception as e:
            # If file logging fails, continue with console only
            print(f"Warning: Could not create file logger: {e}")
    
    # Prevent propagation to avoid duplicate messages
    logger.propagate = False
    
    return logger


def create_file_handler(log_level: int, game_prefix: str = "falcongrasp") -> Optional[logging.FileHandler]:
    """
    Create a file handler for logging with automatic timestamped filename
    
    Args:
        log_level: Logging level for the file handler
        game_prefix: Prefix for the log file (default: "falcongrasp")
        
    Returns:
        FileHandler instance or None if creation fails
    """
    try:
        # Create logs directory if it doesn't exist
        logs_dir = "logs"
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
            
        # Generate timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create filename in the format: {game_prefix}_YYYYMMDD_HHMMSS.log
        log_filename = f"{game_prefix}_{timestamp}.log"
        log_filepath = os.path.join(logs_dir, log_filename)
        
        # Create file handler
        file_handler = logging.FileHandler(log_filepath, mode='w', encoding='utf-8')
        file_handler.setLevel(log_level)
        
        # Create formatter for file (with full timestamp)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        print(f"📁 Log file created: {log_filepath}")
        return file_handler
        
    except Exception as e:
        print(f"❌ Failed to create file handler: {e}")
        return None


def setup_root_logger(level: str = "INFO", log_file: Optional[str] = None):
    """
    Setup root logger for the entire application
    
    Args:
        level: Logging level
        log_file: Optional file to write logs to
    """
    
    # Get root logger
    root_logger = logging.getLogger()
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set level
    log_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(log_level)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        try:
            # Ensure logs directory exists
            logs_dir = os.path.dirname(log_file)
            if logs_dir and not os.path.exists(logs_dir):
                os.makedirs(logs_dir)
            
            file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
            file_handler.setLevel(log_level)
            
            # Use full timestamp format for file logging
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
            
            print(f"📁 Root log file created: {log_file}")
            
        except Exception as e:
            print(f"❌ Failed to create root log file {log_file}: {e}")
    
    return root_logger


# Configure basic logging for the application
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
