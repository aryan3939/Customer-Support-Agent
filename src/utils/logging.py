"""
Structured logging setup for the Customer Support Agent.

WHY THIS FILE EXISTS:
---------------------
Standard Python logging produces messy, hard-to-parse output:
    2025-02-10 05:00:00 INFO ticket created for user@example.com

Structured logging produces machine-readable JSON:
    {"timestamp": "2025-02-10T05:00:00", "level": "info", 
     "event": "ticket_created", "email": "user@example.com", "ticket_id": "abc-123"}

Why is JSON better?
1. SEARCHABLE — Find all logs for a specific ticket_id instantly
2. FILTERABLE — Show only "error" level logs in production
3. PARSEABLE — Log aggregation tools (Grafana, CloudWatch) understand JSON
4. CONTEXTUAL — Each log entry carries structured metadata, not just a string

HOW IT WORKS:
-------------
structlog wraps Python's standard logging with a processing pipeline:

    logger.info("ticket_created", email="user@example.com")
            ↓
    [Add timestamp] → [Add log level] → [Format as JSON] → [Output]
            ↓
    {"timestamp": "...", "level": "info", "event": "ticket_created", "email": "..."}
"""

import logging
import sys
from typing import Literal

import structlog


def setup_logging(
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO",
    json_format: bool = False,
) -> None:
    """
    Configure structured logging for the entire application.
    
    This should be called ONCE at application startup (in main.py).
    After calling this, any module can use:
    
        import structlog
        logger = structlog.get_logger()
        logger.info("something_happened", key="value")
    
    Args:
        log_level: Minimum level to output. DEBUG shows everything,
                   ERROR shows only errors. During development, use DEBUG.
        json_format: If True, output JSON (for production/log aggregators).
                     If False, output colored human-readable text (for development).
    """
    
    # -------------------------------------------------------------------------
    # Shared processors — these run on EVERY log message
    # -------------------------------------------------------------------------
    shared_processors: list[structlog.types.Processor] = [
        # Adds timestamp to every log entry
        structlog.stdlib.add_log_level,
        # Adds logger name (which module is logging)
        structlog.stdlib.add_logger_name,
        # If an exception is being logged, format the traceback nicely
        structlog.processors.format_exc_info,
        # Add a timestamp in ISO 8601 format
        structlog.processors.TimeStamper(fmt="iso"),
        # Remove internal structlog keys the user doesn't need to see
        structlog.stdlib.ExtraAdder(),
    ]
    
    # -------------------------------------------------------------------------
    # Choose output format based on environment
    # -------------------------------------------------------------------------
    if json_format:
        # Production: machine-readable JSON, one object per line
        # {"timestamp": "...", "level": "info", "event": "...", ...}
        renderer = structlog.processors.JSONRenderer()
    else:
        # Development: colored, human-readable output
        # 2025-02-10 05:00:00 [info] ticket_created  email=user@example.com
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    
    # -------------------------------------------------------------------------
    # Configure structlog
    # -------------------------------------------------------------------------
    structlog.configure(
        processors=[
            # Filter out log levels below our threshold
            structlog.stdlib.filter_by_level,
            *shared_processors,
            # Prepare the event dict for the final renderer
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        # Use standard library logging as the backend
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Enable caching for performance
        cache_logger_on_first_use=True,
    )
    
    # -------------------------------------------------------------------------
    # Configure standard library logging (catches third-party logs too)
    # -------------------------------------------------------------------------
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            # Extract positional args from the event dict
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )
    
    # Create handler that outputs to console (stdout)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()        # Remove any existing handlers
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)
    
    # Quiet down noisy third-party loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.
    
    Usage:
        from src.utils.logging import get_logger
        
        logger = get_logger(__name__)
        logger.info("ticket_created", ticket_id="abc-123", priority="high")
        logger.error("tool_failed", tool="send_email", error="timeout")
    
    Args:
        name: Logger name, typically __name__ (the module's dotted path).
              If None, structlog will figure it out.
    
    Returns:
        A structured logger that outputs timestamped, leveled, contextual logs.
    """
    return structlog.get_logger(name)
