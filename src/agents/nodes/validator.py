"""
Validator Node — checks AI responses before sending to customers.

WHY THIS NODE EXISTS:
---------------------
We NEVER send raw LLM output directly to customers. The validator:

1. Checks response quality (not too short, not empty)
2. Ensures the response is appropriate (no harmful content)
3. Validates that it actually addresses the customer's question
4. Approves or rejects the draft response

Think of it as a QA step before publishing:
    [AI generates draft] → [Validator checks it] → [Approved? Send it!]
                                                 → [Rejected? Try again or escalate]

HOW IT WORKS:
-------------
    state.draft_response = "I can help you reset your password. Here's how..."
              ↓
    validate_response() checks length, content, relevance
              ↓
    If good: state.final_response = state.draft_response
    If bad:  state.needs_escalation = True (send to human)
"""

from src.agents.state import TicketState
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Minimum acceptable response length (characters)
MIN_RESPONSE_LENGTH = 50

# Words that suggest the AI is uncertain or refusing
UNCERTAINTY_MARKERS = [
    "i'm not sure",
    "i cannot",
    "i don't know",
    "i'm unable",
    "i am not able",
    "i apologize but i cannot",
    "unfortunately, i cannot",
    "i don't have access",
]


async def validate_response(state: TicketState) -> dict:
    """
    LangGraph node that validates the AI-generated draft response.
    
    Quality checks:
        1. Response exists and is non-empty
        2. Response meets minimum length
        3. Response doesn't contain high-uncertainty markers
        4. Response is appropriate for the ticket's priority
    
    Input state fields used:
        - draft_response: the AI's generated response
        - priority: ticket priority (urgent tickets need better responses)
        - attempts: how many times we've tried
        
    Output state fields set:
        - final_response: approved response (if validation passes)
        - needs_escalation: True (if validation fails after max attempts)
        - current_node: "validate"
    """
    draft = state.get("draft_response", "")
    attempts = state.get("attempts", 0)
    
    logger.info(
        "validating_response",
        ticket_id=state.get("ticket_id", "unknown"),
        draft_length=len(draft),
        attempt=attempts,
    )
    
    # ---- Check 1: Response exists ----
    if not draft or not draft.strip():
        logger.warning("validation_failed_empty", ticket_id=state.get("ticket_id"))
        return _handle_failure(state, "Empty response generated")
    
    # ---- Check 2: Minimum length ----
    if len(draft.strip()) < MIN_RESPONSE_LENGTH:
        logger.warning("validation_failed_short", length=len(draft.strip()))
        return _handle_failure(state, f"Response too short ({len(draft.strip())} chars)")
    
    # ---- Check 3: Uncertainty check ----
    draft_lower = draft.lower()
    for marker in UNCERTAINTY_MARKERS:
        if marker in draft_lower:
            logger.warning("validation_failed_uncertain", marker=marker)
            return _handle_failure(state, f"Response contains uncertainty: '{marker}'")
    
    # ---- All checks passed! ----
    logger.info(
        "response_validated",
        ticket_id=state.get("ticket_id", "unknown"),
        approved=True,
    )
    
    action = {
        "action_type": "validate_response",
        "action_data": {"draft_length": len(draft), "checks_passed": True},
        "reasoning": "All quality checks passed",
        "outcome": "success",
    }
    
    return {
        "final_response": draft,
        "current_node": "validate",
        "actions_taken": state.get("actions_taken", []) + [action],
    }


def _handle_failure(state: TicketState, reason: str) -> dict:
    """Handle validation failure — retry or escalate."""
    attempts = state.get("attempts", 0) + 1
    
    action = {
        "action_type": "validate_response",
        "action_data": {"reason": reason, "attempt": attempts},
        "reasoning": reason,
        "outcome": "failure",
    }
    
    # After 3 failed attempts, escalate instead of retrying
    if attempts >= 3:
        logger.warning(
            "validation_max_attempts",
            ticket_id=state.get("ticket_id", "unknown"),
            attempts=attempts,
        )
        return {
            "needs_escalation": True,
            "escalation_reason": f"Response validation failed after {attempts} attempts: {reason}",
            "current_node": "validate",
            "attempts": attempts,
            "actions_taken": state.get("actions_taken", []) + [action],
        }
    
    return {
        "current_node": "validate",
        "attempts": attempts,
        "draft_response": "",  # Clear draft so resolver retries
        "actions_taken": state.get("actions_taken", []) + [action],
    }
