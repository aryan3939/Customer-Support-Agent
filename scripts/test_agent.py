"""
Test script for the AI Agent workflow.

Run this to process sample tickets through the LangGraph and see the results.

Usage:
    python scripts/test_agent.py

Requirements:
    - .env file with GOOGLE_API_KEY (or GROQ_API_KEY) configured
    - Dependencies installed (pip install -r requirements.txt)
    - DATABASE_URL can be any valid URL (agent doesn't use DB in this test)
"""

import asyncio
import json
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_normal_ticket():
    """Test a normal ticket that should be resolved by AI."""
    from src.agents.graph import process_ticket
    
    print("\n" + "=" * 70)
    print("TEST 1: Normal Ticket — Password Reset")
    print("=" * 70)
    
    result = await process_ticket(
        ticket_id="test-001",
        customer_email="alice@example.com",
        subject="Cannot reset my password",
        message=(
            "Hi, I've been trying to reset my password for the last 30 minutes. "
            "I click 'Forgot Password' and enter my email, but I never receive "
            "the reset link. I've checked my spam folder too. Please help!"
        ),
        channel="web",
    )
    
    _print_result(result)
    return result


async def test_angry_urgent_ticket():
    """Test an urgent+angry ticket that should be escalated."""
    from src.agents.graph import process_ticket
    
    print("\n" + "=" * 70)
    print("TEST 2: Angry + Urgent Ticket — Should Escalate")
    print("=" * 70)
    
    result = await process_ticket(
        ticket_id="test-002",
        customer_email="bob@example.com",
        subject="CHARGED TWICE!! NEED REFUND NOW!!!",
        message=(
            "I WAS CHARGED TWICE FOR MY SUBSCRIPTION! $99 each time! "
            "This is FRAUD! I want a FULL REFUND immediately or I'm "
            "contacting my lawyer and filing a complaint. FIX THIS NOW!"
        ),
        channel="email",
    )
    
    _print_result(result)
    return result


async def test_billing_ticket():
    """Test a billing inquiry ticket."""
    from src.agents.graph import process_ticket
    
    print("\n" + "=" * 70)
    print("TEST 3: Billing Inquiry — Refund Request")
    print("=" * 70)
    
    result = await process_ticket(
        ticket_id="test-003",
        customer_email="carol@example.com",
        subject="Request for refund on last invoice",
        message=(
            "Hello, I'd like to request a refund for my last payment. "
            "I signed up for the Pro plan last month but realized I don't "
            "need the premium features. Can I get my money back? Thanks!"
        ),
        channel="web",
    )
    
    _print_result(result)
    return result


def _print_result(result: dict):
    """Pretty-print the agent's result."""
    print(f"\n{'─' * 50}")
    print("CLASSIFICATION:")
    print(f"  Intent:     {result.get('intent', 'N/A')}")
    print(f"  Category:   {result.get('category', 'N/A')}")
    print(f"  Priority:   {result.get('priority', 'N/A')}")
    print(f"  Sentiment:  {result.get('sentiment', 'N/A')}")
    print(f"  Confidence: {result.get('confidence', 'N/A')}")
    print(f"\nESCALATED: {result.get('needs_escalation', False)}")
    if result.get('escalation_reason'):
        print(f"  Reason: {result.get('escalation_reason')}")
    
    print(f"\nRESPONSE:")
    response = result.get("final_response", result.get("draft_response", "No response"))
    print(f"  {response[:500]}...")
    
    print(f"\nAUDIT TRAIL ({len(result.get('actions_taken', []))} actions):")
    for action in result.get("actions_taken", []):
        print(f"  → {action.get('action_type', '?')}: {action.get('outcome', '?')}")
    
    print(f"{'─' * 50}\n")


async def main():
    """Run all test scenarios."""
    print("\n🤖 Customer Support Agent — Test Suite")
    print("━" * 70)
    
    try:
        await test_normal_ticket()
        await test_billing_ticket()
        await test_angry_urgent_ticket()
        
        print("\n✅ All tests completed successfully!")
        print("━" * 70)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
