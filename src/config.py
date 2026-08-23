import os
from dotenv import load_dotenv

load_dotenv()

# Razorpay credentials (loaded from .env)
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

# --- Guardrail limits (in paise, since Razorpay uses paise) ---

# Maximum a single buyer-agent session can spend in total
SESSION_SPEND_LIMIT = 500000  # ₹5000

# Maximum amount allowed for a single order without human approval
PER_TRANSACTION_LIMIT = 150000  # ₹1500

# Any order above this amount requires human approval before proceeding
APPROVAL_THRESHOLD = 150000  # ₹1500 (same as per-transaction limit for now)

# Safety check: refuse to start if live keys are accidentally used
if RAZORPAY_KEY_ID and not RAZORPAY_KEY_ID.startswith("rzp_test_"):
    raise RuntimeError(
        "Refusing to start: RAZORPAY_KEY_ID does not look like a test-mode key. "
        "This project must only run with test-mode credentials."
    )