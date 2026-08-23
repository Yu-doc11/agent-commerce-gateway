from src.orchestrator.approval import create_approval_request
import hashlib
import json
import uuid
from datetime import datetime, timezone

from src.db.models import Order, AgentSession, Product
from src.orchestrator.guardrails import (
    check_session_budget,
    check_transaction_limit,
    check_duplicate_order,
    requires_approval,
)
from src.audit.logger import log_event


def make_idempotency_key(session_id: str, product_id: int, quantity: int) -> str:
    """Creates a stable key so the same purchase intent always maps to the same hash."""
    raw = f"{session_id}:{product_id}:{quantity}"
    return hashlib.sha256(raw.encode()).hexdigest()


def create_order(db, session_id: str, product_id: int, quantity: int) -> dict:
    """
    The single entry point for creating an order.
    Every decision made here is logged to audit_logs BEFORE any action is taken.
    """
    session = db.query(AgentSession).filter(AgentSession.id == session_id).first()
    product = db.query(Product).filter(Product.id == product_id).first()

    if not session or not product:
        return {"status": "error", "reason": "Invalid session or product"}

    order_amount = product.price * quantity
    idempotency_key = make_idempotency_key(session_id, product_id, quantity)

    # 1. Check for duplicate order first
    is_duplicate, dup_reason = check_duplicate_order(db, session_id, idempotency_key)
    if is_duplicate:
        log_event(
            db, session_id=session_id, order_id=None, actor="orchestrator",
            event_type="duplicate_blocked", action="create_order",
            input_payload=json.dumps({"product_id": product_id, "quantity": quantity}),
            output_payload=None, decision="blocked", reason=dup_reason,
            amount_involved=order_amount, running_budget_spent=session.budget_spent,
        )
        return {"status": "blocked", "reason": dup_reason}

    # 2. Check per-transaction limit
    txn_ok, txn_reason = check_transaction_limit(order_amount)
    if not txn_ok:
        log_event(
            db, session_id=session_id, order_id=None, actor="orchestrator",
            event_type="guardrail_violation", action="create_order",
            input_payload=json.dumps({"product_id": product_id, "quantity": quantity}),
            output_payload=None, decision="blocked", reason=txn_reason,
            amount_involved=order_amount, running_budget_spent=session.budget_spent,
        )
        return {"status": "blocked", "reason": txn_reason}

    # 3. Check session budget
    budget_ok, budget_reason = check_session_budget(session, order_amount)
    if not budget_ok:
        log_event(
            db, session_id=session_id, order_id=None, actor="orchestrator",
            event_type="guardrail_violation", action="create_order",
            input_payload=json.dumps({"product_id": product_id, "quantity": quantity}),
            output_payload=None, decision="blocked", reason=budget_reason,
            amount_involved=order_amount, running_budget_spent=session.budget_spent,
        )
        return {"status": "blocked", "reason": budget_reason}

    # 4. Create the order record (status depends on whether approval is needed)
    needs_approval = requires_approval(order_amount)
    order_status = "pending_approval" if needs_approval else "created"

    order = Order(
        id=str(uuid.uuid4()),
        session_id=session_id,
        product_id=product_id,
        quantity=quantity,
        amount=order_amount,
        idempotency_key=idempotency_key,
        status=order_status,
        created_at=datetime.now(timezone.utc),
    )
    db.add(order)
    db.commit()
    if needs_approval:
        create_approval_request(db, order)
    log_event(
        db, session_id=session_id, order_id=order.id, actor="orchestrator",
        event_type="order_created", action="create_order",
        input_payload=json.dumps({"product_id": product_id, "quantity": quantity}),
        output_payload=json.dumps({"order_id": order.id, "status": order_status}),
        decision="pending" if needs_approval else "allowed",
        reason="Order created, awaiting approval" if needs_approval else "Order created within limits",
        amount_involved=order_amount, running_budget_spent=session.budget_spent,
    )

    return {"status": order_status, "order_id": order.id, "amount": order_amount}