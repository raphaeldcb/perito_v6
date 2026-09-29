"""
Structured logging with JSON format and correlation ID support.
Task 17: Monitoring & Logs (Wave 2)
Produces machine-parseable logs with timestamp, level, correlation_id, module, message, and trace.
"""
import json
import logging
import traceback
from typing import Any, Dict, Optional
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs.

    Each log record includes:
    - timestamp: ISO format
    - level: log level (INFO, ERROR, etc.)
    - correlation_id: from request context or logger
    - module: source module name
    - message: log message
    - extra fields: any additional context
    - traceback: if exception (exc_info=True)
    """

    def format(self, record: logging.LogRecord) -> str:
        """Convert log record to JSON."""
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }

        # Add correlation ID if available
        if hasattr(record, "correlation_id"):
            log_obj["correlation_id"] = record.correlation_id
        elif hasattr(record, "request_id"):  # Alternative name
            log_obj["correlation_id"] = record.request_id

        # Add exception info if present
        if record.exc_info:
            log_obj["traceback"] = traceback.format_exception(
                *record.exc_info
            ).__str__()

        # Add any extra attributes from the record (those added via extra= kwarg)
        # Skip internal attributes (those starting with _)
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if not key.startswith("_") and key not in (
                    "name",
                    "msg",
                    "args",
                    "created",
                    "filename",
                    "funcName",
                    "levelname",
                    "levelno",
                    "lineno",
                    "module",
                    "msecs",
                    "message",
                    "pathname",
                    "process",
                    "processName",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                    "correlation_id",
                    "request_id",
                ):
                    log_obj[key] = value

        return json.dumps(log_obj)


class StructuredLogger:
    """
    Wrapper around Python logger that provides structured logging with context.

    Usage:
        logger = StructuredLogger(
            logging.getLogger("mymodule"),
            correlation_id="request-123"
        )
        logger.info("User logged in", extra={"user_id": 42})
    """

    def __init__(self, logger: logging.Logger, correlation_id: Optional[str] = None):
        """
        Initialize structured logger.

        Args:
            logger: Python logger instance
            correlation_id: Correlation ID for this logger context
        """
        self.logger = logger
        self.correlation_id = correlation_id

    def _add_correlation_id(self, extra: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Add correlation ID to extra context."""
        if extra is None:
            extra = {}
        if self.correlation_id:
            extra["correlation_id"] = self.correlation_id
        return extra

    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log debug message."""
        extra = self._add_correlation_id(extra)
        self.logger.debug(message, extra=extra)

    def info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log info message."""
        extra = self._add_correlation_id(extra)
        self.logger.info(message, extra=extra)

    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log warning message."""
        extra = self._add_correlation_id(extra)
        self.logger.warning(message, extra=extra)

    def error(self, message: str, extra: Optional[Dict[str, Any]] = None, exc_info: bool = False):
        """Log error message."""
        extra = self._add_correlation_id(extra)
        self.logger.error(message, extra=extra, exc_info=exc_info)

    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None, exc_info: bool = False):
        """Log critical message."""
        extra = self._add_correlation_id(extra)
        self.logger.critical(message, extra=extra, exc_info=exc_info)


def setup_structured_logging(log_level: str = "INFO"):
    """
    Configure application-wide structured logging with JSON format.

    Usage:
        setup_structured_logging("DEBUG")
    """
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add console handler with JSON formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(console_handler)

    return root_logger
