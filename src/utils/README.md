# `src/utils/` — Shared Utilities

Cross-cutting concerns used across every layer of the application.
These are "infrastructure" utilities — not specific to any feature,
but essential for the application to work properly.

## Files

### `logging.py` — Structured Logging (6KB)

Sets up the application's logging system using **structlog** — a library
for structured, machine-parsable logging.

**Why structured logging instead of `print()` or basic `logging`?**

```python
# ❌ BAD — unstructured, hard to search/filter
print(f"Created ticket {ticket_id} for {email}")
logging.info(f"Created ticket {ticket_id} for {email}")

# ✅ GOOD — structured, machine-parsable, searchable
logger.info(
    "ticket_created",
    ticket_id=str(ticket.id),
    customer=email,
    priority=classification.priority,
)
# Output in development (colorized):
# 2026-02-18 15:30:00 [info] ticket_created  ticket_id=abc-123 customer=user@example.com priority=high

# Output in production (JSON):
# {"event": "ticket_created", "ticket_id": "abc-123", "customer": "user@example.com", "priority": "high", "timestamp": "2026-02-18T15:30:00Z"}
```

**Key configuration:**
- **Development:** Colored console output with human-readable formatting
- **Production:** JSON output for ingestion by log aggregators (Datadog, ELK, etc.)
- **Log level:** Configurable via `LOG_LEVEL` environment variable

**Usage in any file:**
```python
from src.utils.logging import get_logger
logger = get_logger(__name__)  # Creates a logger named after the module

logger.info("something_happened", key="value")
logger.error("something_failed", error=str(e))
```

---

### `metrics.py` — Performance Tracking (1.7KB)

Simple performance counters and timing utilities for monitoring application health.

**What it tracks:**
- Request count per endpoint
- Average response time
- Error rate
- AI agent processing time

**Usage:**
```python
from src.utils.metrics import track_time

@track_time("ticket_processing")
async def process_ticket(...):
    # Execution time is automatically recorded
```

In production, these metrics would feed into monitoring dashboards (Grafana, Datadog).

---

### `__init__.py` — Package Init

Exports `get_logger` for convenience.
