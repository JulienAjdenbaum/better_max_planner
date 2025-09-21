import logging
from logging.handlers import RotatingFileHandler
import os

# Use project's logs directory instead of /var/log
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(PROJECT_ROOT, 'logs')
DEFAULT_LOG_FILE = os.path.join(LOGS_DIR, 'tgvmax_app.log')

def setup_logging(log_file: str = DEFAULT_LOG_FILE) -> None:
    """Configure root logger with console and rotating file handlers."""
    logger = logging.getLogger()
    if logger.handlers:
        # Already configured
        return

    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    logger.setLevel(log_level)

    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    )
    
    # Create a more detailed formatter for request timing logs
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - [%(filename)s:%(lineno)d] - %(message)s'
    )

    # Ensure log directory exists
    log_dir = os.path.dirname(log_file) or '.'
    os.makedirs(log_dir, exist_ok=True)

    file_handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=5)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    
    # Create a separate logger for request timing
    request_logger = logging.getLogger('request_timing')
    request_logger.setLevel(logging.INFO)
    
    # Create a separate log file for request timing
    request_log_file = os.path.join(LOGS_DIR, 'tgvmax_requests.log')
    request_file_handler = RotatingFileHandler(request_log_file, maxBytes=1_000_000, backupCount=5)
    request_file_handler.setFormatter(detailed_formatter)
    request_logger.addHandler(request_file_handler)
    
    # Don't propagate to root logger to avoid duplicate logs
    request_logger.propagate = False
