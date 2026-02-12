"""
Edge Conditions — routing logic between nodes in the LangGraph.

WHY THIS FILE EXISTS:
---------------------
In LangGraph, EDGES connect nodes. Some edges are unconditional
("always go from A to B"), but some are CONDITIONAL ("go to B if X,
go to C if Y"). Those conditional edges need functions.

This file contains the routing functions that decide WHERE the graph
goes next based on the current state.

HOW CONDITIONAL EDGES WORK:
---------------------------
    [Classify] → should_escalate_after_classify() → returns "escalate" or "search_kb"
                     ↓                                  ↓
              [Escalate Node]                   [Search KB Node]

The function examines the state and returns a STRING that matches
one of the edge labels in the graph definition.
"""

from src.agents.state import TicketState
from src.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


def should_escalate_after_classify(state: TicketState) -> str:
    """
    After classification: escalate immediately or continue processing?
    
    ESCALATE if:
        - Priority is urgent AND sentiment is angry
        - AI confidence is below threshold (too uncertain)
    
    CONTINUE if:
        - Normal priority/sentiment
        - AI is confident in its classification
    
    Returns:
        "escalate" — route to escalator node
        "search_kb" — route to knowledge base search
    """
    priority = state.get("priority", "medium")
    sentiment = state.get("sentiment", "neutral")
    confidence = state.get("confidence", 1.0)
    
    # Rule 1: Urgent + angry → immediate human intervention
    if priority == "urgent" and sentiment == "angry":
        logger.info(
            "routing_to_escalation",
            reason="urgent_and_angry",
            ticket_id=state.get("ticket_id"),
        )
        return "escalate"
    
    # Rule 2: AI too uncertain → don't risk a bad response
    threshold = settings.ESCALATION_CONFIDENCE_THRESHOLD
    if confidence < threshold:
        logger.info(
            "routing_to_escalation",
            reason="low_confidence",
            confidence=confidence,
            threshold=threshold,
            ticket_id=state.get("ticket_id"),
        )
        return "escalate"
    
    return "search_kb"


def should_escalate_after_validate(state: TicketState) -> str:
    """
    After validation: escalate, retry resolution, or send response?
    
    Returns:
        "escalate" — validation failed too many times, escalate
        "resolve" — retry resolution (draft was rejected)
        "respond" — validation passed, send the response
    """
    # If escalation flag is set, go to escalation
    if state.get("needs_escalation", False):
        return "escalate"
    
    # If there's a final response, validation passed
    if state.get("final_response"):
        return "respond"
    
    # Otherwise, retry resolution
    return "resolve"
