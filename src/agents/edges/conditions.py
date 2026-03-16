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
    [Classify] → should_escalate_after_classify() → returns "escalate" or "continue"
                     ↓                                  ↓
              [Escalate Node]                   [Tool Agent Node]
    
    [Tool Agent] → should_continue_tools() → returns "tools" or "done"
                     ↓                           ↓
              [ToolNode executor]          [Validate Node]
"""

from src.agents.state import TicketState
from src.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


def should_escalate_after_classify(state: TicketState) -> str:
    """
    After classification: escalate immediately or continue to tool agent?
    
    ESCALATE if:
        - Priority is urgent AND sentiment is angry
        - AI confidence is below threshold (too uncertain)
    
    CONTINUE if:
        - Normal priority/sentiment
        - AI is confident in its classification
    
    Returns:
        "escalate" — route to escalator node
        "continue" — route to agentic tool agent
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
    
    return "continue"


def should_continue_tools(state: TicketState) -> str:
    """
    After the tool agent: did the LLM call tools, or is it done?
    
    This is the CORE AGENTIC ROUTING:
    - If the LLM's last message has tool_calls → execute those tools
    - If the LLM responded with text (no tool_calls) → it's done, validate
    
    Returns:
        "tools" — execute the tool calls the LLM requested
        "done"  — LLM is done, proceed to validation
    """
    messages = state.get("messages", [])
    
    if not messages:
        return "done"
    
    last_message = messages[-1]
    
    # Check if the last message has tool calls
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        logger.info(
            "tool_agent_calling_tools",
            num_tools=len(last_message.tool_calls),
            tools=[tc["name"] for tc in last_message.tool_calls],
            ticket_id=state.get("ticket_id"),
        )
        return "tools"
    
    return "done"


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
