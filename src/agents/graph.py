"""
LangGraph Workflow — the AGENTIC agent graph with tool selection.

WHY THIS FILE EXISTS:
---------------------
This is the BRAIN of the entire application. It defines the agent's
workflow as a state machine (graph) where the LLM CHOOSES which
tools to call based on the customer's message.

BEFORE (fixed pipeline):
    [Ticket] → [Classify] → [Search KB] → [Resolve] → [Validate] → [Respond]
    
AFTER (agentic tool selection):
    [Ticket] → [Classify] → [Tool Agent] ⟲ (LLM picks tools) → [Respond] → [Validate] → [Finalize]

The key difference: the LLM DECIDES which tools to call (KB search,
order lookup, password reset, etc.) instead of always doing the same steps.

HOW TO USE:
-----------
    from src.agents.graph import process_ticket
    
    result = await process_ticket(
        ticket_id="abc-123",
        customer_email="user@example.com",
        subject="Where is my order #12345?",
        message="I ordered 3 days ago and haven't received anything",
        channel="web",
    )
    
    # The LLM will CHOOSE to call check_order_status("12345")
    # instead of always searching the KB
"""

from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.edges.conditions import (
    should_escalate_after_classify,
    should_escalate_after_validate,
    should_continue_tools,
)
from src.agents.nodes.classifier import classify_ticket
from src.agents.nodes.escalator import escalate_ticket
from src.agents.nodes.validator import validate_response
from src.agents.state import TicketState
from src.agents.tools import ALL_TOOLS
from src.agents.llm import get_llm
from src.utils.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Tool Agent System Prompt
# =============================================================================

TOOL_AGENT_SYSTEM_PROMPT = """You are an AI customer support agent with access to tools.

Your job is to help the customer by using the appropriate tools to gather information
and take actions. You should:

1. ANALYZE the customer's message to understand what they need
2. DECIDE which tools to call (you can call multiple tools if needed)
3. USE the tool results to formulate a helpful response

AVAILABLE TOOLS:
- search_knowledge_base: Search our help articles for policies, how-to guides, FAQs
- check_order_status: Look up order tracking/shipping status by order ID
- create_refund_request: Initiate a refund (only when customer explicitly requests one)
- reset_customer_password: Send a password reset email 
- lookup_customer_info: Check customer account details and history
- create_bug_report: File a bug report for technical issues

GUIDELINES:
- Use search_knowledge_base for general questions, how-to, policies
- Use check_order_status when they mention an order ID or ask about delivery
- Use reset_customer_password when they can't log in or forgot password
- Use lookup_customer_info to personalize your response with account context
- You CAN call multiple tools in sequence if needed
- After gathering all needed information, generate your final response
- Be empathetic, specific, and concise in your response
- If you provided a complete solution, suggest marking the ticket as resolved

CONVERSATION HISTORY:
{conversation_history}

TICKET CLASSIFICATION:
- Intent: {intent}
- Category: {category}  
- Priority: {priority}
- Sentiment: {sentiment}
- Customer Email: {customer_email}
"""


# =============================================================================
# Tool Agent Node — LLM decides which tools to call
# =============================================================================

async def tool_agent(state: TicketState) -> dict:
    """
    The AGENTIC node — LLM decides which tools to use.
    
    This replaces the old fixed search_kb node. Instead of always
    searching the KB, the LLM analyzes the message and decides:
    - Which tools to call (0, 1, or multiple)
    - What arguments to pass
    - When it has enough info to respond
    
    Uses LangChain's bind_tools() to give the LLM access to tools.
    """
    logger.info(
        "tool_agent_thinking",
        ticket_id=state.get("ticket_id", "unknown"),
    )
    
    # Format conversation history for the prompt
    history_text = "No previous messages."
    conv_history = state.get("conversation_history", [])
    if conv_history:
        history_lines = []
        for msg in conv_history[-10:]:  # Last 10 messages max
            role = msg.get("role", msg.get("sender_type", "unknown"))
            content = msg.get("content", "")
            history_lines.append(f"[{role}]: {content}")
        history_text = "\n".join(history_lines)
    
    # Build the system prompt with context
    system_prompt = TOOL_AGENT_SYSTEM_PROMPT.format(
        conversation_history=history_text,
        intent=state.get("intent", "unknown"),
        category=state.get("category", "general"),
        priority=state.get("priority", "medium"),
        sentiment=state.get("sentiment", "neutral"),
        customer_email=state.get("customer_email", ""),
    )
    
    # Build the user message
    user_content = (
        f"Subject: {state.get('subject', '')}\n"
        f"Message: {state.get('message', '')}"
    )
    
    # Get LLM with tools bound
    llm = get_llm()
    llm_with_tools = llm.bind_tools(ALL_TOOLS)
    
    # Construct messages: system + any existing tool conversation + current ticket
    messages = state.get("messages", [])
    if not messages:
        # First call — set up the conversation
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_content),
        ]
    
    # Call the LLM
    response = await llm_with_tools.ainvoke(messages)
    
    logger.info(
        "tool_agent_response",
        ticket_id=state.get("ticket_id", "unknown"),
        has_tool_calls=bool(response.tool_calls),
        num_tool_calls=len(response.tool_calls) if response.tool_calls else 0,
    )
    
    # Record the tool selection in the audit trail
    action = {
        "action_type": "tool_agent_reasoning",
        "action_data": {
            "tool_calls": [
                {"name": tc["name"], "args": tc["args"]}
                for tc in (response.tool_calls or [])
            ],
            "has_final_response": not bool(response.tool_calls),
        },
        "reasoning": "LLM decided which tools to call based on the customer message",
        "outcome": "success",
    }
    
    result = {
        "messages": [response],
        "current_node": "tool_agent",
        "actions_taken": state.get("actions_taken", []) + [action],
    }
    
    # If no tool calls, the LLM is done — extract the response
    if not response.tool_calls:
        result["draft_response"] = response.content
    
    return result


# =============================================================================
# Build the Graph
# =============================================================================

def build_graph() -> StateGraph:
    """
    Construct the AGENTIC LangGraph workflow.
    
    The graph looks like this:
    
        START
          │
          ▼
        [classify] ──→ should_escalate? ──→ [escalate] → END
          │                                     ↑
          ▼ (continue)                          │
        [tool_agent] ◄──┐                      │
          │              │                      │
          ▼              │                      │
        should_continue? │                      │
          │    └─ tools ─┘                      │
          ▼ (done)                              │
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
    graph.add_node("classify", classify_ticket)
    graph.add_node("tool_agent", tool_agent)
    graph.add_node("tools", ToolNode(ALL_TOOLS))  # Auto-executes tool calls
    graph.add_node("validate", validate_response)
    graph.add_node("escalate", escalate_ticket)
    graph.add_node("respond", _finalize_response)
    
    # ---- Set Entry Point ----
    graph.set_entry_point("classify")
    
    # ---- Add Edges ----
    
    # After classification: escalate or continue to tool agent?
    graph.add_conditional_edges(
        "classify",
        should_escalate_after_classify,
        {
            "escalate": "escalate",
            "continue": "tool_agent",
        },
    )
    
    # After tool_agent: did the LLM call tools or is it done?
    graph.add_conditional_edges(
        "tool_agent",
        should_continue_tools,
        {
            "tools": "tools",       # LLM called tools → execute them
            "done": "validate",     # LLM is done → validate response
        },
    )
    
    # After tool execution: always go back to tool_agent
    # (LLM sees the results and can call more tools or respond)
    graph.add_edge("tools", "tool_agent")
    
    # After validation: escalate, retry, or respond?
    graph.add_conditional_edges(
        "validate",
        should_escalate_after_validate,
        {
            "escalate": "escalate",
            "resolve": "tool_agent",    # Retry → back to tool agent
            "respond": "respond",
        },
    )
    
    # Terminal nodes
    graph.add_edge("escalate", END)
    graph.add_edge("respond", END)
    
    return graph


# =============================================================================
# Finalize Response Node
# =============================================================================

async def _finalize_response(state: TicketState) -> dict:
    """
    Final node — marks the ticket as resolved.
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
    conversation_history: list[dict] | None = None,
) -> TicketState:
    """
    Process a support ticket through the AGENTIC AI workflow.
    
    This is the MAIN ENTRY POINT for the agent system.
    
    Args:
        ticket_id: Unique ticket identifier
        customer_email: Customer's email address
        subject: Ticket subject line
        message: Customer's message
        channel: Source channel (web, email, api)
        conversation_history: Previous messages for context (follow-ups)
    
    Returns:
        Final TicketState with:
        - final_response: AI-generated response (or escalation message)
        - actions_taken: Complete audit trail showing WHICH tools were used
        - needs_escalation: Whether a human agent should take over
        - All classification data (intent, category, priority, sentiment)
    """
    logger.info(
        "processing_ticket",
        ticket_id=ticket_id,
        subject=subject,
        channel=channel,
        has_history=bool(conversation_history),
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
        "conversation_history": conversation_history or [],
        "messages": [],
    }
    
    # LangSmith tracing config
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
        "recursion_limit": 25,
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
