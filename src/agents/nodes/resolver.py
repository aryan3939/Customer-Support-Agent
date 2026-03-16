"""
Resolver Node — generates AI responses using context from KB and history.

WHY THIS NODE EXISTS:
---------------------
After classifying the ticket and searching the knowledge base, we need
to actually RESPOND to the customer. This node:

1. Gathers all available context (KB results, customer history, classification)
2. Constructs a detailed prompt for the LLM
3. Generates an empathetic, helpful response
4. Records the action in the audit trail

The response is a DRAFT — the validator node checks it before sending.

HOW IT WORKS:
-------------
    Context:
        - Classification: "intent=password_reset, priority=high"
        - KB Results: "Password Reset Guide: Step 1..."
        - Customer History: "3 previous tickets, premium plan"
              ↓
    LLM generates a personalized, context-aware response
              ↓
    state.draft_response = "I understand you're having trouble..."
"""

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.llm import get_llm
from src.agents.state import TicketState
from src.utils.logging import get_logger

logger = get_logger(__name__)

# =============================================================================
# Response Generation Prompt
# =============================================================================

RESOLVER_SYSTEM_PROMPT = """You are a friendly, professional customer support agent.
Your goal is to resolve the customer's issue completely in a single response.

GUIDELINES:
1. Be empathetic — acknowledge their frustration/situation first
2. Be specific — don't give vague advice, give exact steps
3. Be concise — respect their time, get to the solution quickly
4. Be proactive — anticipate follow-up questions and address them
5. Include step-by-step instructions when applicable
6. If you used knowledge base articles, cite the relevant information
7. End with a clear next step or confirmation question
8. RESOLUTION SUGGESTION: If you believe your response fully resolves the customer's
   issue (you provided a clear, complete answer or solution), end your response with:
   "If this resolves your issue, you can click the 'Mark as Resolved' button to close this ticket."
   Only suggest this when you are CONFIDENT the issue is addressed — never when asking
   clarifying questions, requesting more information, or when the issue is complex/ongoing.

TONE: Professional but warm. Never robotic. Match the customer's energy level.

FORMAT: Use plain text (no markdown headers or code blocks unless showing
technical steps). Keep paragraphs short (2-3 sentences max)."""


# =============================================================================
# Resolver Node Function
# =============================================================================

async def generate_response(state: TicketState) -> dict:
    """
    LangGraph node that generates an AI response to the customer.
    
    Input state fields used:
        - subject, message: the customer's ticket
        - intent, category, priority, sentiment: classification results
        - kb_results: relevant knowledge base articles
        - customer_history: past interactions
        
    Output state fields set:
        - draft_response: the generated response text
        - actions_taken: appended with generation action
        - current_node: "resolve"
    """
    logger.info(
        "generating_response",
        ticket_id=state.get("ticket_id", "unknown"),
        intent=state.get("intent", "unknown"),
    )
    
    # Build context string from KB results
    kb_context = _format_kb_results(state.get("kb_results", []))
    
    # Build customer history context
    history_context = _format_customer_history(state.get("customer_history", {}))
    
    # Build conversation history context (for follow-ups)
    conv_history = _format_conversation_history(state.get("conversation_history", []))
    
    # Construct the prompt with all available context
    user_message = f"""CUSTOMER TICKET:
Subject: {state.get("subject", "")}
Message: {state.get("message", "")}
Channel: {state.get("channel", "web")}

TICKET CLASSIFICATION:
- Intent: {state.get("intent", "unknown")}
- Category: {state.get("category", "general")}
- Priority: {state.get("priority", "medium")}
- Sentiment: {state.get("sentiment", "neutral")}

RELEVANT KNOWLEDGE BASE ARTICLES:
{kb_context if kb_context else "No relevant articles found."}

CUSTOMER HISTORY:
{history_context if history_context else "New customer, no previous history."}

PREVIOUS CONVERSATION:
{conv_history if conv_history else "No previous messages — this is a new ticket."}

Generate a helpful response that resolves the customer's issue.
If there is previous conversation, acknowledge what was discussed and build on it."""

    try:
        llm = get_llm()
        
        response = await llm.ainvoke([
            SystemMessage(content=RESOLVER_SYSTEM_PROMPT),
            HumanMessage(content=user_message),
        ])
        
        draft = response.content.strip()
        
        logger.info(
            "response_generated",
            ticket_id=state.get("ticket_id", "unknown"),
            response_length=len(draft),
        )
        
        action = {
            "action_type": "generate_response",
            "action_data": {
                "response_length": len(draft),
                "kb_articles_used": len(state.get("kb_results", [])),
            },
            "reasoning": f"Generated response using {len(state.get('kb_results', []))} KB articles",
            "outcome": "success",
        }
        
        return {
            "draft_response": draft,
            "current_node": "resolve",
            "actions_taken": state.get("actions_taken", []) + [action],
        }
        
    except Exception as e:
        logger.error("response_generation_failed", error=str(e))
        
        # Fallback response
        fallback = (
            "Thank you for reaching out. I've noted your issue and our team "
            "is looking into it. We'll get back to you shortly with a resolution. "
            "If you need immediate assistance, please don't hesitate to let us know."
        )
        
        return {
            "draft_response": fallback,
            "current_node": "resolve",
            "error": f"Response generation failed: {e}",
            "actions_taken": state.get("actions_taken", []) + [{
                "action_type": "generate_response",
                "action_data": {"fallback": True},
                "reasoning": str(e),
                "outcome": "failure",
            }],
        }


# =============================================================================
# Helper Functions
# =============================================================================

def _format_kb_results(kb_results: list[dict]) -> str:
    """Format KB search results into a readable context string."""
    if not kb_results:
        return ""
    
    formatted = []
    for i, result in enumerate(kb_results[:5], 1):  # Top 5 results
        title = result.get("article_title", "Untitled")
        text = result.get("chunk_text", "")
        score = result.get("relevance_score", 0.0)
        formatted.append(f"[Article {i}: {title} (relevance: {score:.2f})]\n{text}")
    
    return "\n\n".join(formatted)


def _format_customer_history(history: dict) -> str:
    """Format customer history into a readable context string."""
    if not history:
        return ""
    
    parts = []
    if "total_tickets" in history:
        parts.append(f"Total previous tickets: {history['total_tickets']}")
    if "plan" in history:
        parts.append(f"Customer plan: {history['plan']}")
    if "recent_tickets" in history:
        for ticket in history["recent_tickets"][:3]:
            parts.append(f"- Previous: {ticket.get('subject', '')} [{ticket.get('status', '')}]")
    
    return "\n".join(parts) if parts else ""


def _format_conversation_history(history: list[dict]) -> str:
    """Format previous conversation messages into a readable context string."""
    if not history:
        return ""
    
    lines = []
    for msg in history[-10:]:  # Last 10 messages to keep context manageable
        role = msg.get("role", msg.get("sender_type", "unknown"))
        content = msg.get("content", "")
        
        # Map sender types to readable labels
        role_labels = {
            "customer": "Customer",
            "ai_agent": "AI Agent",
            "human_agent": "Human Agent",
            "system": "System",
        }
        label = role_labels.get(role, role.title())
        lines.append(f"[{label}]: {content}")
    
    return "\n".join(lines)

