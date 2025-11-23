"""Logging utility for the multi-agent system."""
from loguru import logger
import sys
from pathlib import Path

def setup_logger(log_level: str = "INFO"):
    """Configure the logger for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Remove default logger
    logger.remove()

    # Add console handler with custom format
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True
    )

    # Ensure log directory exists
    Path("data/logs").mkdir(parents=True, exist_ok=True)

    # Add file handler
    logger.add(
        "data/logs/job_agent_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}"
    )

    return logger

# Create a global logger instance
log = setup_logger()
