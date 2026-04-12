# `src/agents/edges/` — Conditional Routing (Graph Edges)

Edges in LangGraph define **which node runs next**. Regular edges are simple
connections (A → B), but **conditional edges** are functions that decide the
path based on the current state.

## How Conditional Edges Work

```
[classify] ──→ should_escalate_after_classify? ──┬──→ YES → [escalate]
                                                  └──→ NO  → [kb_search]
```

The function `should_escalate_after_classify(state)` looks at the classification
results and decides: should we continue processing, or immediately escalate?

## Files

### `conditions.py` — Routing Decision Functions

Contains two main routing functions:

#### `should_escalate_after_classify(state: TicketState) → str`

Called after the classifier node. Returns either `"escalate"` or `"continue"`.

**Escalation rules:**
```python
# Escalate if ANY of these are true:
if state["priority"] == "urgent":           return "escalate"
if state["sentiment"] == "angry":           return "escalate"
if state["confidence"] < THRESHOLD:         return "escalate"  # default 0.7
if state.get("needs_escalation"):           return "escalate"
```

**Why these rules:** Urgent tickets need human expertise. Angry customers respond
better to human empathy. Low-confidence classifications mean the AI isn't sure
what the customer wants — better to hand off than guess wrong.

#### `should_escalate_after_validate(state: TicketState) → str`

Called after the validator node. Returns either `"escalate"` or `"finalize"`.

If the validator determines the response is poor quality, it sets
`needs_escalation = True`, and this function routes to the escalation node
instead of finalizing.

### `__init__.py` — Package Init

Exports the routing functions for use in `graph.py`.

## How Edges Are Registered in the Graph

```python
# In graph.py — this is how conditional edges are added:
graph.add_conditional_edges(
    "classify",                           # After this node...
    should_escalate_after_classify,       # ...run this function...
    {
        "escalate": "escalate",           # If it returns "escalate" → go to escalate node
        "continue": "kb_search",          # If it returns "continue" → go to kb_search node
    },
)
```
