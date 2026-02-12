# `edges/` — LangGraph Edge Conditions

This folder contains **conditional routing functions** used by LangGraph
to decide which node to execute next.

In a LangGraph state machine, edges connect nodes. **Conditional edges**
look at the current state and choose between multiple possible next nodes.

## Files

### `conditions.py`
Contains two routing functions:

#### `should_escalate_after_classify(state) → str`
Called after the `classify_ticket` node. Returns:
- `"escalate"` → if priority is `urgent` AND sentiment is `angry` (skip straight to human)
- `"continue"` → proceed to knowledge base search

#### `should_escalate_after_validate(state) → str`
Called after the `validate_response` node. Returns:
- `"accept"` → response passed quality checks, proceed to finalize
- `"retry"` → response failed checks, retry generation (up to max attempts)
- `"escalate"` → max retries reached, escalate to human agent

## How to Explain This

> "Conditional edges are the **decision points** in the workflow. For example,
> after classification, if a customer is both angry and has an urgent issue,
> the system skips the AI response entirely and routes directly to a human agent.
> After validation, if the AI's response isn't good enough, it retries
> automatically — but only up to a limit, after which it escalates. This
> prevents the AI from sending low-quality responses while also avoiding
> infinite retry loops."
