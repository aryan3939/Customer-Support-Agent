# `tests/` — Test Suite

Organized test directory following **pytest** conventions.
Tests are split by scope:

## Structure

```
tests/
├── conftest.py       # Shared pytest fixtures (DB sessions, test clients, mock data)
├── unit/             # Unit tests — individual functions in isolation
├── integration/      # Integration tests — multiple components working together
└── e2e/              # End-to-end tests — full request/response cycles
```

## Test Types

### Unit Tests (`unit/`)
Test individual functions with **mocked dependencies**:
- Agent node functions (does `classify_ticket` return the right schema?)
- Repository functions (does `create_ticket` insert correctly?)
- Service functions (does `compute_dashboard_metrics` calculate correctly?)
- Utility functions (does `get_logger` return a configured logger?)

### Integration Tests (`integration/`)
Test components **working together** with a real (test) database:
- Route → Repository → Database flow
- Agent graph → LLM → Tool calls
- Webhook → Ticket creation → Database persistence

### End-to-End Tests (`e2e/`)
Test the **full workflow** as a user would experience it:
- Create ticket via API → verify in database → check LangSmith trace
- Frontend → API → Agent → Database → Response

## How to Run

```bash
# Run all tests
pytest

# Run only unit tests
pytest tests/unit/

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/unit/test_classifier.py
```

## Key Fixtures (conftest.py)

| Fixture | What It Provides |
|---------|-----------------|
| `db_session` | Fresh async database session (rolled back after each test) |
| `test_client` | FastAPI TestClient with database dependency overridden |
| `sample_ticket` | Pre-built ticket data for testing |

## How to Explain This

> "Tests are organized by scope: unit tests verify individual functions with
> mocks, integration tests verify component interactions with a real database,
> and e2e tests verify the complete user workflow. This pyramid structure
> ensures fast feedback (hundreds of unit tests in seconds) while still
> catching integration issues."
