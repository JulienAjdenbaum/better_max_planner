import logging
from logging.handlers import RotatingFileHandler
import os

DEFAULT_LOG_FILE = '/var/log/tgvmax_app.log'

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

    # Ensure log directory exists
    log_dir = os.path.dirname(log_file) or '.'
    os.makedirs(log_dir, exist_ok=True)

    file_handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=5)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
