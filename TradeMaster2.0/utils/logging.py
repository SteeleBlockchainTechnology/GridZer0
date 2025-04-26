"""
Logging configuration for the TradeMaster 2.0 bot.
Sets up console and file logging with appropriate formatting.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Configure the logging system for the TradeMaster bot."""
    # Ensure the logs directory exists
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # Create formatters
    console_formatter = logging.Formatter('%(levelname)s - %(name)s - %(message)s')
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create console handler with proper encoding
    import sys
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Set encoding for console output to handle Unicode characters
    if sys.platform == 'win32':
        # On Windows, ensure we can handle Unicode properly
        import codecs
        # Try to use utf-8 if possible
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            # For older Python versions
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    
    # Create file handler with rotation
    log_file = os.path.join(log_dir, "trademaster.log")
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=5*1024*1024,  # 5 MB
        backupCount=3
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add our handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger('discord').setLevel(logging.WARNING)
    logging.getLogger('discord.http').setLevel(logging.WARNING)
    
    # Create a logger for our bot
    bot_logger = logging.getLogger("TradeMaster")
    bot_logger.setLevel(logging.DEBUG)
    
    return bot_logger