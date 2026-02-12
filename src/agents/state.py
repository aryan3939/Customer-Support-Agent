"""
LangGraph State Schema for the Customer Support Agent.

WHY THIS FILE EXISTS:
---------------------
LangGraph is a STATE MACHINE — it processes a ticket by passing STATE
through a series of NODES (functions). Each node reads the state,
does something, and returns an updated state.

Think of it like an assembly line:
    [Ticket] → [Classify] → [Search KB] → [Generate Response] → [Done]
               ↓ updates     ↓ updates     ↓ updates
               state.intent  state.kb_results  state.draft_response

This file defines the SHAPE of that state — what data flows through
the pipeline.

HOW LANGGRAPH STATE WORKS:
--------------------------
    1. A ticket comes in → we create a TicketState with initial data
    2. Each node function receives TicketState, returns partial updates
    3. LangGraph MERGES the updates into the state automatically
    4. The next node gets the merged state
    
    Example:
        classify_node returns: {"intent": "billing", "priority": "high"}
        LangGraph merges it into the full state → next node sees it
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Any, Literal

from langgraph.graph import add_messages


# =============================================================================
# Message Schema — individual messages in the ticket thread
# =============================================================================

@dataclass
class TicketMessage:
    """
    A single message in the conversation.
    
    Examples:
        TicketMessage(role="customer", content="I can't log in!")
        TicketMessage(role="ai_agent", content="Let me help you reset...")
        TicketMessage(role="system", content="Ticket escalated to human agent")
    """
    role: Literal["customer", "ai_agent", "human_agent", "system"]
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Classification Result — output of the classifier node
# =============================================================================

@dataclass
class ClassificationResult:
    """
    The AI's classification of a ticket.
    
    This is produced by the classifier node and used by downstream nodes
    to decide priority routing, KB search queries, and response tone.
    """
    intent: str = ""              # e.g., "password_reset", "billing_inquiry"
    category: str = ""            # e.g., "account", "billing", "technical"
    priority: str = "medium"      # low, medium, high, urgent
    sentiment: str = "neutral"    # positive, neutral, negative, angry
    confidence: float = 0.0       # 0.0 - 1.0, how sure the AI is


# =============================================================================
# KB Search Result — a relevant knowledge base article chunk
# =============================================================================

@dataclass
class KBSearchResult:
    """A knowledge base search result with relevance score."""
    article_title: str
    chunk_text: str
    relevance_score: float
    article_id: str = ""


# =============================================================================
# Action Record — tracks what the agent did (audit trail)
# =============================================================================

@dataclass
class ActionRecord:
    """
    Records a single action taken by the agent.
    
    This is the AUDIT TRAIL — proves what the AI did and why.
    Crucial for debugging, compliance, and trust in the AI.
    """
    action_type: str                # "classify", "search_kb", "generate_response", etc.
    action_data: dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""             # LLM's chain-of-thought
    outcome: str = ""               # "success", "failure", "escalated"


# =============================================================================
# Ticket State — the MAIN state that flows through the graph
# =============================================================================

from typing import TypedDict


class TicketState(TypedDict, total=False):
    """
    The complete state object that flows through every node in the LangGraph.
    
    total=False means ALL fields are optional — nodes only return the fields
    they update. LangGraph merges partial returns into the full state.
    
    SECTIONS:
    ---------
    1. Input — set when the ticket is first created
    2. Classification — filled by the classifier node
    3. Context — filled by enrichment nodes (KB search, customer history)
    4. Processing — internal tracking (attempts, current step)
    5. Response — the AI-generated response
    6. Audit — action log for transparency
    """
    
    # =========================================================================
    # 1. INPUT — provided when the ticket enters the graph
    # =========================================================================
    ticket_id: str
    customer_email: str
    subject: str
    message: str                    # The customer's latest message
    channel: str                    # "web", "email", "api"
    
    # =========================================================================
    # 2. CLASSIFICATION — set by the classifier node
    # =========================================================================
    intent: str                     # What the customer wants
    category: str                   # Which department handles this
    priority: str                   # How urgent
    sentiment: str                  # Customer's emotional state
    confidence: float               # AI's confidence in classification
    
    # =========================================================================
    # 3. CONTEXT — gathered by enrichment nodes
    # =========================================================================
    kb_results: list[dict]          # Relevant KB article chunks
    customer_history: dict          # Past tickets, account info
    tool_results: list[dict]        # Results from tool calls
    
    # =========================================================================
    # 4. PROCESSING — internal state tracking
    # =========================================================================
    current_node: str               # Where we are in the workflow
    attempts: int                   # How many resolution attempts
    needs_escalation: bool          # Should this go to a human?
    escalation_reason: str          # Why it's being escalated
    error: str                      # Any error message
    
    # =========================================================================
    # 5. RESPONSE — the generated answer
    # =========================================================================
    draft_response: str             # AI's draft before validation
    final_response: str             # Validated, approved response
    
    # =========================================================================
    # 6. AUDIT — action log
    # =========================================================================
    actions_taken: list[dict]       # List of ActionRecord dicts
