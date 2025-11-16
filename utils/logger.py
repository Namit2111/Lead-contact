import logging
import sys
from config import settings


def setup_logger(name: str = "lead_contact_app") -> logging.Logger:
    """Setup logger with consistent formatting and level"""
    logger = logging.getLogger(name)

    # Don't add handlers if already configured
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(handler)

    return logger


# Global logger instance
logger = setup_logger()
