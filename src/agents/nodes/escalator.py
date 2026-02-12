"""
Escalator Node — handles tickets that need human intervention.

WHY THIS NODE EXISTS:
---------------------
Not every ticket can be resolved by AI. Some MUST be escalated:

1. URGENT + ANGRY — Customer is very upset about a critical issue
2. LOW CONFIDENCE — AI isn't sure about its classification/response
3. TOO MANY ATTEMPTS — Tried 3 times and still can't resolve
4. SENSITIVE TOPICS — Legal threats, security breaches, VIP accounts

This node prepares a HANDOFF SUMMARY for the human agent, so they
don't have to re-read the entire conversation. It includes:
- What the customer wants
- What the AI already tried
- Why it's being escalated
- Recommended next steps

HOW IT WORKS:
-------------
    State shows: priority=urgent, sentiment=angry, attempts=3
              ↓
    escalate_ticket() generates a handoff summary
              ↓
    Sets needs_escalation=True + escalation_reason
              ↓
    (In production: would notify human agent via Slack/email)
"""

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.llm import get_llm
from src.agents.state import TicketState
from src.utils.logging import get_logger

logger = get_logger(__name__)

# =============================================================================
# Escalation Prompt
# =============================================================================

ESCALATION_SYSTEM_PROMPT = """You are a support AI preparing a handoff summary for a human agent.
Create a clear, concise summary that helps the human agent take over immediately.

Include:
1. ONE-LINE SUMMARY of the issue
2. CUSTOMER SENTIMENT (and why)
3. WHAT WAS TRIED by the AI (if anything)
4. RECOMMENDED ACTION for the human agent
5. KEY DETAILS the human agent should know

Keep it under 200 words. Be factual, not verbose."""


# =============================================================================
# Escalator Node Function
# =============================================================================

async def escalate_ticket(state: TicketState) -> dict:
    """
    LangGraph node that prepares a ticket for human agent escalation.
    
    Input state fields used:
        - subject, message: the customer's ticket
        - intent, category, priority, sentiment: classification
        - actions_taken: what the AI already did
        - escalation_reason: why we're escalating (if set)
        
    Output state fields set:
        - needs_escalation: True
        - escalation_reason: detailed reason
        - final_response: acknowledgment message to customer
        - actions_taken: appended with escalation action
        - current_node: "escalate"
    """
    ticket_id = state.get("ticket_id", "unknown")
    
    # Determine the escalation reason
    reason = state.get("escalation_reason", "")
    if not reason:
        reason = _determine_reason(state)
    
    logger.warning(
        "escalating_ticket",
        ticket_id=ticket_id,
        reason=reason,
        priority=state.get("priority"),
        sentiment=state.get("sentiment"),
    )
    
    try:
        llm = get_llm()
        
        # Generate handoff summary for human agent
        user_message = f"""Ticket being escalated:
Subject: {state.get("subject", "")}
Message: {state.get("message", "")}
Intent: {state.get("intent", "unknown")}
Category: {state.get("category", "general")}
Priority: {state.get("priority", "medium")}
Sentiment: {state.get("sentiment", "neutral")}
Escalation Reason: {reason}
Previous Actions: {_format_actions(state.get("actions_taken", []))}"""

        response = await llm.ainvoke([
            SystemMessage(content=ESCALATION_SYSTEM_PROMPT),
            HumanMessage(content=user_message),
        ])
        
        handoff_summary = response.content.strip()
        
    except Exception as e:
        logger.error("handoff_summary_failed", error=str(e))
        handoff_summary = (
            f"Issue: {state.get('subject', 'Unknown')}\n"
            f"Reason: {reason}\n"
            f"Priority: {state.get('priority', 'medium')}\n"
            f"Sentiment: {state.get('sentiment', 'neutral')}"
        )
    
    # Customer-facing acknowledgment
    customer_response = (
        "I want to make sure you get the best possible help with this. "
        "I'm connecting you with a specialist from our support team who "
        "can assist you further. They'll have all the context from our "
        "conversation, so you won't need to repeat anything. "
        "Thank you for your patience!"
    )
    
    action = {
        "action_type": "escalate_ticket",
        "action_data": {
            "reason": reason,
            "handoff_summary": handoff_summary,
        },
        "reasoning": f"Escalated: {reason}",
        "outcome": "escalated",
    }
    
    return {
        "needs_escalation": True,
        "escalation_reason": reason,
        "final_response": customer_response,
        "current_node": "escalate",
        "actions_taken": state.get("actions_taken", []) + [action],
    }


# =============================================================================
# Helper Functions
# =============================================================================

def _determine_reason(state: TicketState) -> str:
    """Figure out WHY this ticket should be escalated."""
    reasons = []
    
    if state.get("priority") == "urgent":
        reasons.append("urgent priority")
    if state.get("sentiment") == "angry":
        reasons.append("angry customer")
    if state.get("attempts", 0) >= 3:
        reasons.append(f"exceeded max attempts ({state.get('attempts', 0)})")
    if state.get("confidence", 1.0) < 0.5:
        reasons.append(f"low AI confidence ({state.get('confidence', 0):.0%})")
    if state.get("error"):
        reasons.append(f"processing error: {state.get('error', '')}")
    
    return "; ".join(reasons) if reasons else "manual escalation requested"


def _format_actions(actions: list[dict]) -> str:
    """Format previous actions for the handoff summary."""
    if not actions:
        return "No actions taken yet"
    
    formatted = []
    for action in actions:
        formatted.append(
            f"- {action.get('action_type', '?')}: {action.get('outcome', '?')}"
        )
    return "\n".join(formatted)
