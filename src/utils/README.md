# `utils/` — Shared Utilities

Cross-cutting utilities used by every part of the application.
These are **infrastructure concerns**, not business logic.

## Files

### `logging.py` — Structured Logging
Sets up **structlog** for consistent, parseable logs across the entire app.

Key functions:
- `setup_logging(log_level, json_format)` — called once at startup in `main.py`
- `get_logger(name)` — creates a per-module logger

**Two modes:**
- **Development**: Colored, human-readable console output
- **Production**: JSON-formatted logs (parseable by Datadog, CloudWatch, etc.)

Example output:
```
# Dev mode
2025-02-10 10:30:45 [info] ticket_created  ticket_id=abc-123  priority=high

# Production JSON mode
{"event": "ticket_created", "ticket_id": "abc-123", "priority": "high", "timestamp": "2025-02-10T10:30:45Z"}
```

### `metrics.py` — Simple Metrics Tracking
In-memory counters and latency tracking for basic observability.

Key functions:
- `increment(metric_name)` — bump a counter
- `track_latency(op_name)` — async context manager that records operation duration
- `get_metrics()` — returns all collected metrics

**Production upgrade**: Replace with Prometheus client or Datadog StatsD.

## How to Explain This

> "Structured logging with structlog gives me JSON-formatted, queryable logs
> in production while keeping human-readable output in development. Every log
> line includes context (ticket_id, customer_email, operation) so I can filter
> and search in log aggregation tools. The metrics module tracks request counts
> and latency for basic performance monitoring."
