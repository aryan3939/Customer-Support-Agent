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
    2. Sends it to the LLM with a structured prompt
    3. Parses the LLM's JSON response
    4. Returns the classification as state updates
"""

import json

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.llm import get_llm
from src.agents.state import TicketState
from src.utils.logging import get_logger

logger = get_logger(__name__)

# =============================================================================
# Classification Prompt
# =============================================================================

CLASSIFIER_SYSTEM_PROMPT = """You are a customer support ticket classifier.
Analyze the ticket and return a JSON object with these fields:

{
    "intent": "<one of: password_reset, billing_inquiry, refund_request, bug_report, feature_request, account_issue, order_status, general_question, complaint, other>",
    "category": "<one of: account, billing, technical, product, shipping, general, other>",
    "priority": "<one of: low, medium, high, urgent>",
    "sentiment": "<one of: positive, neutral, negative, angry>",
    "confidence": <float between 0.0 and 1.0>
}

Priority guidelines:
- low: general questions, feature requests
- medium: standard issues, billing inquiries
- high: account locked, payment failed, data loss risk
- urgent: security breach, system down, legal threat, repeated failures

Sentiment guidelines:
- positive: polite, thankful, patient
- neutral: matter-of-fact, no strong emotion
- negative: frustrated, disappointed, impatient
- angry: hostile, threatening, ALL CAPS, excessive punctuation

IMPORTANT: Return ONLY the JSON object, no markdown formatting, no extra text."""


# =============================================================================
# Classifier Node Function
# =============================================================================

async def classify_ticket(state: TicketState) -> dict:
    """
    LangGraph node that classifies a support ticket.
    
    This is the FIRST node in the workflow graph.
    
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
        
        # Call the LLM
        response = await llm.ainvoke([
            SystemMessage(content=CLASSIFIER_SYSTEM_PROMPT),
            HumanMessage(content=user_message),
        ])
        
        # Parse the JSON response
        response_text = response.content.strip()
        
        # Handle markdown code blocks (some models wrap JSON in ```json ... ```)
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        classification = json.loads(response_text)
        
        logger.info(
            "ticket_classified",
            ticket_id=state.get("ticket_id", "unknown"),
            intent=classification.get("intent"),
            category=classification.get("category"),
            priority=classification.get("priority"),
            sentiment=classification.get("sentiment"),
            confidence=classification.get("confidence"),
        )
        
        # Build the action record for the audit trail
        action = {
            "action_type": "classify_ticket",
            "action_data": classification,
            "reasoning": f"Classified based on subject '{state.get('subject', '')}' and message content",
            "outcome": "success",
        }
        
        # Return partial state update
        return {
            "intent": classification.get("intent", "other"),
            "category": classification.get("category", "general"),
            "priority": classification.get("priority", "medium"),
            "sentiment": classification.get("sentiment", "neutral"),
            "confidence": classification.get("confidence", 0.5),
            "current_node": "classify",
            "actions_taken": state.get("actions_taken", []) + [action],
        }
        
    except json.JSONDecodeError as e:
        logger.error("classification_parse_error", error=str(e))
        return {
            "intent": "other",
            "category": "general",
            "priority": "medium",
            "sentiment": "neutral",
            "confidence": 0.0,
            "current_node": "classify",
            "error": f"Failed to parse classification: {e}",
            "actions_taken": state.get("actions_taken", []) + [{
                "action_type": "classify_ticket",
                "action_data": {},
                "reasoning": "Classification failed — using defaults",
                "outcome": "failure",
            }],
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
