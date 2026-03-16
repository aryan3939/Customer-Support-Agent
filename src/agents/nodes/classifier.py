"""
Classifier Node — analyzes and classifies incoming tickets.

WHY THIS NODE EXISTS:
---------------------
Every ticket that enters the system needs to be CLASSIFIED before 
anything else can happen. Classification determines:

1. INTENT — What does the customer want? (password reset, refund, etc.)
2. CATEGORY — Which department handles this? (billing, technical, etc.)
3. PRIORITY — How urgent is this? (low → urgent)
4. SENTIMENT — How is the customer feeling? (angry customers get escalated)

This is the FIRST node in the LangGraph workflow. Its output drives
ALL downstream decisions:

    priority=urgent + sentiment=angry → ESCALATE immediately
    intent=password_reset → search KB for "password reset" articles
    category=billing → route to billing-specific tools

HOW IT WORKS:
-------------
    1. Takes the ticket subject + message
    2. Sends it to the LLM with structured output (Pydantic model)
    3. LLM returns a validated ClassificationResult — no manual JSON parsing
    4. Returns the classification as state updates
"""

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.llm import get_llm
from src.agents.models import ClassificationResult
from src.agents.state import TicketState
from src.utils.logging import get_logger

logger = get_logger(__name__)

# =============================================================================
# Classification Prompt
# =============================================================================

CLASSIFIER_SYSTEM_PROMPT = """You are a customer support ticket classifier.
Analyze the ticket and classify it accurately.

Priority guidelines:
- low: general questions, feature requests
- medium: standard issues, billing inquiries
- high: account locked, payment failed, data loss risk
- urgent: security breach, system down, legal threat, repeated failures

Sentiment guidelines:
- positive: polite, thankful, patient
- neutral: matter-of-fact, no strong emotion
- negative: frustrated, disappointed, impatient
- angry: hostile, threatening, ALL CAPS, excessive punctuation"""


# =============================================================================
# Classifier Node Function
# =============================================================================

async def classify_ticket(state: TicketState) -> dict:
    """
    LangGraph node that classifies a support ticket.
    
    This is the FIRST node in the workflow graph.
    
    Uses LangChain's `with_structured_output()` to bind a Pydantic model
    to the LLM call, guaranteeing a validated ClassificationResult object
    instead of fragile manual JSON parsing.
    
    Input state fields used:
        - subject: ticket subject line
        - message: customer's message
        
    Output state fields set:
        - intent, category, priority, sentiment, confidence
        - actions_taken: appended with classification action
        - current_node: updated to "classify"
    
    Returns:
        Partial state update dict (LangGraph merges it into full state)
    """
    logger.info(
        "classifying_ticket",
        ticket_id=state.get("ticket_id", "unknown"),
        subject=state.get("subject", ""),
    )
    
    # Build the user message from ticket data
    user_message = f"""Ticket Subject: {state.get("subject", "")}
        Customer Message: {state.get("message", "")}
        Channel: {state.get("channel", "web")}"""
    
    try:
        llm = get_llm()
        
        # Bind the Pydantic model to the LLM — it will return a validated
        # ClassificationResult object directly, no manual JSON parsing needed.
        structured_llm = llm.with_structured_output(ClassificationResult)
        
        # Call the LLM — response is a ClassificationResult, not raw text
        classification = await structured_llm.ainvoke([
            SystemMessage(content=CLASSIFIER_SYSTEM_PROMPT),
            HumanMessage(content=user_message),
        ])
        
        logger.info(
            "ticket_classified",
            ticket_id=state.get("ticket_id", "unknown"),
            intent=classification.intent,
            category=classification.category,
            priority=classification.priority,
            sentiment=classification.sentiment,
            confidence=classification.confidence,
        )
        
        # Build the action record for the audit trail
        action = {
            "action_type": "classify_ticket",
            "action_data": classification.model_dump(),
            "reasoning": f"Classified based on subject '{state.get('subject', '')}' and message content",
            "outcome": "success",
        }
        
        # Return partial state update
        return {
            "intent": classification.intent,
            "category": classification.category,
            "priority": classification.priority,
            "sentiment": classification.sentiment,
            "confidence": classification.confidence,
            "current_node": "classify",
            "actions_taken": state.get("actions_taken", []) + [action],
        }
        
    except Exception as e:
        logger.error("classification_failed", error=str(e))
        return {
            "intent": "other",
            "category": "general",
            "priority": "medium",
            "sentiment": "neutral",
            "confidence": 0.0,
            "current_node": "classify",
            "error": f"Classification error: {e}",
            "actions_taken": state.get("actions_taken", []) + [{
                "action_type": "classify_ticket",
                "action_data": {},
                "reasoning": str(e),
                "outcome": "failure",
            }],
        }
