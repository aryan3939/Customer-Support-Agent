# `tests/` — Test Suites

Test directory organized by test type. Currently scaffolded with the
directory structure in place for future test development.

## Structure

```
tests/
├── unit/          # Unit tests — test individual functions in isolation
├── integration/   # Integration tests — test multiple components together
└── e2e/           # End-to-end tests — test the full API workflow
```

## Test Types Explained

### `unit/` — Unit Tests

Test a **single function or class** in complete isolation. Dependencies
(database, LLM, external APIs) are mocked.

**Example unit test:**
```python
# Test the classifier node in isolation (mock the LLM)
async def test_classifier_returns_valid_intent():
    mock_llm = MockLLM(return_value={
        "intent": "password_reset",
        "priority": "high",
        "sentiment": "frustrated",
    })
    result = await classify_ticket(state, llm=mock_llm)
    assert result["intent"] == "password_reset"
```

### `integration/` — Integration Tests

Test multiple components working **together** — e.g., route handler +
database + repository. Uses a real test database (or in-memory SQLite).

**Example integration test:**
```python
# Test that creating a ticket actually saves to the database
async def test_create_ticket_saves_to_db():
    response = await client.post("/api/v1/tickets", json={...})
    assert response.status_code == 201
    # Verify it's in the database
    ticket = await get_ticket_by_id(db, response.json()["id"])
    assert ticket is not None
```

### `e2e/` — End-to-End Tests

Test the **complete user workflow** through the API — create a ticket,
send follow-ups, resolve, check analytics. Runs against the real API.

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run just unit tests
pytest tests/unit/

# Run with coverage report
pytest --cov=src --cov-report=html
```

## Test Configuration

- **pytest** is the test runner (configured in `pyproject.toml` or `pytest.ini`)
- **pytest-asyncio** handles async test functions
- **httpx** is used for async API client testing
