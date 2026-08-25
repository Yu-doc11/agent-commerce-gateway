"""
Demonstrates the duplicate-order guardrail: attempts to create the same
order twice in a row (simulating an agent retry / network resend), and
shows the orchestrator blocking the second attempt before it ever
reaches Razorpay.

Run with the FastAPI server already running (`uvicorn src.main:app --reload`).
"""

import requests
import time

BASE_URL = "http://127.0.0.1:8000"


def create_session(goal: str, budget_total: int) -> str:
    resp = requests.post(
        f"{BASE_URL}/agent/session",
        params={"goal": goal, "budget_total": budget_total},
    )
    return resp.json()["session_id"]


def create_order(session_id: str, product_id: int, quantity: int) -> dict:
    resp = requests.post(
        f"{BASE_URL}/orders",
        params={"session_id": session_id, "product_id": product_id, "quantity": quantity},
    )
    return resp.json()


def main():
    print("=" * 60)
    print("FAILURE SCENARIO: Duplicate Order Attempt")
    print("=" * 60)

    session_id = create_session("buy office supplies", budget_total=200000)
    print(f"\n[1] Session created: {session_id}")

    print("\n[2] First order attempt (Notebook Set, product_id=6)...")
    first = create_order(session_id, product_id=6, quantity=1)
    print(f"    Result: {first}")

    time.sleep(1)

    print("\n[3] Simulating a retry — same order sent again "
          "(e.g. agent thinks the first request failed and resends it)...")
    second = create_order(session_id, product_id=6, quantity=1)
    print(f"    Result: {second}")

    print("\n" + "=" * 60)
    if second.get("status") == "blocked":
        print("✅ GUARDRAIL WORKED: duplicate order was blocked before")
        print("   reaching Razorpay. No double charge occurred.")
        print(f"   Reason: {second.get('reason')}")
    else:
        print("⚠️  Unexpected: second order was NOT blocked. Check guardrail logic.")
    print("=" * 60)


if __name__ == "__main__":
    main()