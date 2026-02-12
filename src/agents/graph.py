"""
LangGraph Workflow — the main agent graph.

WHY THIS FILE EXISTS:
---------------------
This is the BRAIN of the entire application. It defines the agent's
workflow as a state machine (graph):

    [Ticket arrives] → [Classify] → [Search KB] → [Resolve] → [Validate] → [Respond]
                            ↓                         ↑           ↓
                       [Escalate?]                  [Retry]    [Escalate]

Each box is a NODE (a function from the nodes/ folder).
Each arrow is an EDGE (a connection, possibly conditional).

LangGraph manages the flow:
1. State enters the graph
2. Each node processes it and returns updates
3. Conditional edges decide which node runs next
4. The graph terminates when it reaches the END node

HOW TO USE:
-----------
    from src.agents.graph import process_ticket
    
    result = await process_ticket(
        ticket_id="abc-123",
        customer_email="user@example.com",
        subject="Can't reset password",
        message="I've tried 3 times but no email arrives",
        channel="web",
    )
    
    print(result["final_response"])  # The AI's response
    print(result["actions_taken"])   # Audit trail
"""

from langgraph.graph import END, StateGraph

from src.agents.edges.conditions import (
    should_escalate_after_classify,
    should_escalate_after_validate,
)
from src.agents.nodes.classifier import classify_ticket
from src.agents.nodes.escalator import escalate_ticket
from src.agents.nodes.resolver import generate_response
from src.agents.nodes.validator import validate_response
from src.agents.state import TicketState
from src.tools.knowledge_base import search_knowledge_base
from src.utils.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Build the Graph
# =============================================================================

def build_graph() -> StateGraph:
    """
    Construct the LangGraph workflow for ticket processing.
    
    The graph looks like this:
    
        START
          │
          ▼
        [classify] ──→ should_escalate? ──→ [escalate] → END
          │                                     ↑
          ▼ (continue)                          │
        [search_kb]                             │
          │                                     │
          ▼                                     │
        [resolve]                               │
          │                                     │
          ▼                                     │
        [validate] ──→ should_escalate? ────────┘
          │
          ▼ (approved)
        [respond] → END
    
    Returns:
        Compiled StateGraph ready to invoke
    """
    
    # Create graph with our state schema
    graph = StateGraph(TicketState)
    
    # ---- Add Nodes ----
    # Each node is a function that takes state and returns partial updates
    graph.add_node("classify", classify_ticket)
    graph.add_node("search_kb", search_knowledge_base)
    graph.add_node("resolve", generate_response)
    graph.add_node("validate", validate_response)
    graph.add_node("escalate", escalate_ticket)
    graph.add_node("respond", _finalize_response)
    
    # ---- Set Entry Point ----
    # Every ticket starts at classification
    graph.set_entry_point("classify")
    
    # ---- Add Edges ----
    
    # After classification: escalate or continue?
    graph.add_conditional_edges(
        "classify",
        should_escalate_after_classify,
        {
            "escalate": "escalate",   # Urgent+angry → escalate
            "search_kb": "search_kb", # Normal → search KB
        },
    )
    
    # After KB search: always go to resolver
    graph.add_edge("search_kb", "resolve")
    
    # After resolver: always go to validator
    graph.add_edge("resolve", "validate")
    
    # After validation: escalate, retry, or respond?
    graph.add_conditional_edges(
        "validate",
        should_escalate_after_validate,
        {
            "escalate": "escalate",   # Validation failed too many times
            "resolve": "resolve",     # Retry resolution
            "respond": "respond",     # Approved! Send response
        },
    )
    
    # After escalation: done
    graph.add_edge("escalate", END)
    
    # After responding: done
    graph.add_edge("respond", END)
    
    return graph


# =============================================================================
# Finalize Response Node
# =============================================================================

async def _finalize_response(state: TicketState) -> dict:
    """
    Final node — marks the ticket as resolved.
    
    In a full implementation, this would:
    - Save the response to the database
    - Send the email/notification
    - Update ticket status to "resolved"
    
    For now, it just logs and records the action.
    """
    logger.info(
        "ticket_resolved",
        ticket_id=state.get("ticket_id", "unknown"),
        response_length=len(state.get("final_response", "")),
    )
    
    action = {
        "action_type": "send_response",
        "action_data": {
            "response_length": len(state.get("final_response", "")),
            "channel": state.get("channel", "web"),
        },
        "reasoning": "Response validated and sent to customer",
        "outcome": "success",
    }
    
    return {
        "current_node": "respond",
        "actions_taken": state.get("actions_taken", []) + [action],
    }


# =============================================================================
# Compiled Graph (singleton)
# =============================================================================

# Build and compile once at import time
_graph = build_graph()
compiled_graph = _graph.compile()


# =============================================================================
# Public API
# =============================================================================

async def process_ticket(
    ticket_id: str,
    customer_email: str,
    subject: str,
    message: str,
    channel: str = "web",
) -> TicketState:
    """
    Process a support ticket through the AI agent workflow.
    
    This is the MAIN ENTRY POINT for the agent system.
    
    Args:
        ticket_id: Unique ticket identifier
        customer_email: Customer's email address
        subject: Ticket subject line
        message: Customer's message
        channel: Source channel (web, email, api)
    
    Returns:
        Final TicketState with:
        - final_response: AI-generated response (or escalation message)
        - actions_taken: Complete audit trail
        - needs_escalation: Whether a human agent should take over
        - All classification data (intent, category, priority, sentiment)
    """
    logger.info(
        "processing_ticket",
        ticket_id=ticket_id,
        subject=subject,
        channel=channel,
    )
    
    # Create the initial state
    initial_state: TicketState = {
        "ticket_id": ticket_id,
        "customer_email": customer_email,
        "subject": subject,
        "message": message,
        "channel": channel,
        "attempts": 0,
        "needs_escalation": False,
        "actions_taken": [],
        "kb_results": [],
        "tool_results": [],
        "customer_history": {},
    }
    
    # ── LangSmith Tracing Config ──────────────────────────────────────────
    # This config makes every ticket fully traceable in LangSmith:
    #   - run_name:  Shows as "ticket-<id>" instead of generic "RunnableSequence"
    #   - tags:      Filterable labels (channel, app name)
    #   - metadata:  Searchable key-value pairs (ticket_id, email, subject)
    #   - thread_id: Groups all runs for the same ticket into one thread
    #                (so follow-up messages appear under the same conversation)
    config = {
        "run_name": f"ticket-{ticket_id[:8]}",
        "tags": ["customer-support", f"channel:{channel}"],
        "metadata": {
            "ticket_id": ticket_id,
            "customer_email": customer_email,
            "subject": subject,
            "channel": channel,
        },
        "configurable": {
            "thread_id": ticket_id,
        },
    }
    
    # Run the graph with tracing
    final_state = await compiled_graph.ainvoke(initial_state, config=config)
    
    logger.info(
        "ticket_processing_complete",
        ticket_id=ticket_id,
        escalated=final_state.get("needs_escalation", False),
        actions_count=len(final_state.get("actions_taken", [])),
    )
    
    return final_state
