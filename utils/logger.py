"""
Logger - Centralized logging configuration
Tracks successes, failures, and skipped files
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional

# Global logger instance
_logger = None


def setup_logger(
    name: str = 'bpm-x',
    log_dir: Optional[str] = None,
    level: int = logging.INFO
) -> logging.Logger:
    """
    Configure and return logger instance.
    
    Args:
        name: Logger name
        log_dir: Directory for log files (creates .bpm-x/logs if None)
        level: Logging level
        
    Returns:
        Configured logger
    """
    global _logger
    
    if _logger is not None:
        return _logger
    
    _logger = logging.getLogger(name)
    _logger.setLevel(level)
    
    # Create formatters
    console_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(level)
    _logger.addHandler(console_handler)
    
    # File handler
    if log_dir is None:
        log_dir = Path.home() / '.bpm-x' / 'logs'
    else:
        log_dir = Path(log_dir)
    
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / 'bpm-x.log'
    file_handler = logging.handlers.RotatingFileHandler(
        str(log_file),
        maxBytes=10_000_000,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(level)
    _logger.addHandler(file_handler)
    
    _logger.info(f"Logging configured. Log file: {log_file}")
    
    return _logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get configured logger instance.
    
    Args:
        name: Logger name (use module name)
        
    Returns:
        Logger instance
    """
    if _logger is None:
        setup_logger()
    
    if name:
        return logging.getLogger(name)
    
    return _logger
