import razorpay
import uuid
from datetime import datetime, timezone

from src.config import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


def create_razorpay_order(amount: int, receipt: str) -> dict:
    """
    Creates a REAL order on Razorpay's test-mode servers.
    amount must be in paise. Returns the Razorpay order object.
    """
    order = client.order.create({
        "amount": amount,
        "currency": "INR",
        "receipt": receipt,
    })
    return order


def simulate_payment_capture(razorpay_order_id: str, amount: int) -> dict:
    """
    Razorpay requires the Checkout UI (client-side, human card entry) to
    actually authorize a card payment — there is no plain server-to-server
    'charge this card' API, by PCI-DSS design.

    Since this project's buyer agent has no human to enter a card, we
    simulate the capture step here rather than build a fragile headless
    browser automation. The order itself (above) is 100% real. This
    function is intentionally isolated so it's obvious where the real
    boundary is, and easy to swap out later (e.g. for a headless
    Checkout automation) without touching the orchestrator.
    """
    return {
        "id": f"pay_sim_{uuid.uuid4().hex[:14]}",
        "order_id": razorpay_order_id,
        "amount": amount,
        "status": "captured",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "simulated": True,
    }