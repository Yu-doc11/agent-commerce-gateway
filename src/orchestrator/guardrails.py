from src.config import SESSION_SPEND_LIMIT, PER_TRANSACTION_LIMIT, APPROVAL_THRESHOLD
from src.db.models import AgentSession, Order


def check_session_budget(session: AgentSession, order_amount: int) -> tuple[bool, str]:
    """
    Checks if adding this order would exceed the session's total spend limit.
    Returns (allowed: bool, reason: str)
    """
    projected_spend = session.budget_spent + order_amount

    if projected_spend > session.budget_total:
        return False, (
            f"Session budget exceeded: spent {session.budget_spent} + "
            f"order {order_amount} > session limit {session.budget_total}"
        )

    if projected_spend > SESSION_SPEND_LIMIT:
        return False, (
            f"Global session spend limit exceeded: {projected_spend} > {SESSION_SPEND_LIMIT}"
        )

    return True, "Within session budget"


def check_transaction_limit(order_amount: int) -> tuple[bool, str]:
    """
    Checks if a single order amount is within the allowed per-transaction limit.
    Returns (allowed: bool, reason: str)
    """
    if order_amount > PER_TRANSACTION_LIMIT:
        return False, (
            f"Order amount {order_amount} exceeds per-transaction limit {PER_TRANSACTION_LIMIT}"
        )
    return True, "Within per-transaction limit"


def requires_approval(order_amount: int) -> bool:
    """
    Returns True if this order amount needs human approval before proceeding.
    """
    return order_amount > APPROVAL_THRESHOLD


def check_duplicate_order(db, session_id: str, idempotency_key: str) -> tuple[bool, str]:
    """
    Checks if an order with the same idempotency_key already exists.
    Returns (is_duplicate: bool, reason: str)
    """
    existing = db.query(Order).filter(
        Order.idempotency_key == idempotency_key
    ).first()

    if existing:
        return True, (
            f"Duplicate order detected: idempotency_key '{idempotency_key}' "
            f"already used in order {existing.id} (status: {existing.status})"
        )

    return False, "No duplicate found"