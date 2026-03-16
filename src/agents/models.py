"""
Pydantic models for structured LLM output.

WHY THIS FILE EXISTS:
---------------------
Instead of prompting the LLM to return raw JSON and then manually parsing it
with json.loads() (which is fragile and error-prone), we define Pydantic models
that represent the exact structure we expect. LangChain's `with_structured_output()`
binds these models to the LLM call, guaranteeing valid, typed output.

HOW IT WORKS:
-------------
    1. Define a Pydantic model (e.g., ClassificationResult)
    2. Call llm.with_structured_output(ClassificationResult)
    3. The LLM returns a validated Pydantic object — no manual parsing needed
    4. Access fields with attribute access: result.intent, result.priority, etc.
"""

from typing import Literal

from pydantic import BaseModel, Field


# =============================================================================
# Classification Result — structured output from the classifier node
# =============================================================================

class ClassificationResult(BaseModel):
    """
    The AI's classification of a customer support ticket.
    
    Used by the classifier node to get structured, validated output
    from the LLM instead of parsing raw JSON strings.
    """
    
    intent: Literal[
        "password_reset",
        "billing_inquiry",
        "refund_request",
        "bug_report",
        "feature_request",
        "account_issue",
        "order_status",
        "general_question",
        "complaint",
        "other",
    ] = Field(
        description="The customer's primary intent — what they want help with."
    )
    
    category: Literal[
        "account",
        "billing",
        "technical",
        "product",
        "shipping",
        "general",
        "other",
    ] = Field(
        description="Which department or category handles this type of issue."
    )
    
    priority: Literal["low", "medium", "high", "urgent"] = Field(
        description=(
            "How urgent this ticket is. "
            "low: general questions, feature requests. "
            "medium: standard issues, billing inquiries. "
            "high: account locked, payment failed, data loss risk. "
            "urgent: security breach, system down, legal threat, repeated failures."
        )
    )
    
    sentiment: Literal["positive", "neutral", "negative", "angry"] = Field(
        description=(
            "The customer's emotional state. "
            "positive: polite, thankful, patient. "
            "neutral: matter-of-fact, no strong emotion. "
            "negative: frustrated, disappointed, impatient. "
            "angry: hostile, threatening, ALL CAPS, excessive punctuation."
        )
    )
    
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="How confident the AI is in this classification, from 0.0 to 1.0.",
    )
