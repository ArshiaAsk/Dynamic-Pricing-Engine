"""Structured logging configuration for production."""
import logging
import json
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional
import traceback

# Default file-rotation threshold (10 MiB) and number of kept backups.
DEFAULT_MAX_BYTES = 10 * 1024 * 1024
DEFAULT_BACKUP_COUNT = 5


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        
        if hasattr(record, 'duration_ms'):
            log_data['duration_ms'] = record.duration_ms
        
        return json.dumps(log_data)


class TextFormatter(logging.Formatter):
    """Human-readable text formatter for development."""
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


def setup_logging(
    level: str = "INFO",
    log_format: str = "json",
    log_dir: Optional[str] = None,
    log_file: Optional[str] = None,
    rotation: str = "none",
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
) -> logging.Logger:
    """Setup application logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ('json' or 'text')
        log_dir: Directory for log files
        log_file: Log file name (default: app.log)
        rotation: File rotation mode — 'size' (RotatingFileHandler),
            'daily' (TimedRotatingFileHandler at midnight), or 'none'.
        max_bytes: Size threshold for 'size' rotation.
        backup_count: Number of rotated files kept.

    Returns:
        Configured logger instance
    """
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    logger.handlers.clear()

    # Choose formatter
    if log_format == "json":
        formatter = JSONFormatter()
    else:
        formatter = TextFormatter()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if log_dir specified)
    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        log_file = log_file or "app.log"
        log_target = log_path / log_file

        # Rotation is configured from the environment (ROADMAP R20). The
        # README claims log rotation, so this must be real, not a plain
        # FileHandler.
        mode = (rotation or "none").lower()
        if mode in ("size", "bytes"):
            file_handler: logging.Handler = RotatingFileHandler(
                log_target, maxBytes=max_bytes, backupCount=backup_count
            )
        elif mode in ("daily", "midnight", "time"):
            file_handler = TimedRotatingFileHandler(
                log_target, when="midnight", backupCount=backup_count
            )
        else:
            file_handler = logging.FileHandler(log_target)

        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def _as_int(value: Optional[str], default: int) -> int:
    """Parse an int from an env string, falling back to ``default``."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def setup_logging_from_env() -> logging.Logger:
    """Configure logging from environment variables (ROADMAP R19/R20).

    Reads ``LOG_LEVEL``, ``LOG_FORMAT``, ``LOG_DIR``, ``LOG_ROTATION``,
    ``LOG_MAX_BYTES`` and ``LOG_BACKUP_COUNT`` and delegates to
    :func:`setup_logging`.
    """
    return setup_logging(
        level=os.getenv("LOG_LEVEL", "INFO"),
        log_format=os.getenv("LOG_FORMAT", "json"),
        log_dir=os.getenv("LOG_DIR", "logs"),
        rotation=os.getenv("LOG_ROTATION", "none"),
        max_bytes=_as_int(os.getenv("LOG_MAX_BYTES"), DEFAULT_MAX_BYTES),
        backup_count=_as_int(os.getenv("LOG_BACKUP_COUNT"), DEFAULT_BACKUP_COUNT),
    )


def get_logger(name: str) -> logging.Logger:
    """Get logger instance for a module.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter):
    """Logger adapter with context information."""
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Process log message with context."""
        # Add context to extra
        extra = kwargs.get('extra', {})
        extra.update(self.extra)
        kwargs['extra'] = extra
        return msg, kwargs


def get_logger_with_context(name: str, **context) -> LoggerAdapter:
    """Get logger with context information.
    
    Args:
        name: Logger name
        **context: Context key-value pairs (e.g., request_id, user_id)
        
    Returns:
        Logger adapter with context
    """
    logger = logging.getLogger(name)
    return LoggerAdapter(logger, context)
