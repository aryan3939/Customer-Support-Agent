# `services/` — Business Logic Layer

Services contain **business logic** that doesn't belong in routes (HTTP concerns)
or repositories (database queries). They orchestrate multiple operations and
transform data.

## Files

### `analytics_service.py`
Computes dashboard metrics from a list of tickets:

```python
compute_dashboard_metrics(tickets: list[dict]) -> dict
```

Returns:
- `total_tickets`, `open_tickets`, `resolved_tickets`, `escalated_tickets`
- `resolution_rate`, `escalation_rate` (percentages)
- `priority_breakdown` — counts per priority level
- `category_breakdown` — counts per category
- `sentiment_breakdown` — counts per sentiment

**Design choice**: The function takes plain dicts (not ORM objects) so it can
be used with any data source — the route converts ORM objects to dicts before
calling this function.

## How to Explain This

> "The service layer exists for business logic that's **too complex for routes
> but not database-specific**. Analytics computation is a good example —
> it transforms raw ticket data into aggregate metrics. By keeping this in a
> service, the route stays thin (just query + return) and the computation
> is independently testable."
