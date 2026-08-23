import uuid
from datetime import datetime, timezone

from src.db.models import Approval, Order, AgentSession
from src.audit.logger import log_event


def create_approval_request(db, order: Order) -> Approval:
    """
    Called by the orchestrator right after an order is marked pending_approval.
    Creates the Approval record a human will later act on.
    """
    approval = Approval(
        id=str(uuid.uuid4()),
        order_id=order.id,
        requested_amount=order.amount,
        status="pending",
        requested_at=datetime.now(timezone.utc),
    )
    db.add(approval)
    db.commit()

    log_event(
        db, session_id=order.session_id, order_id=order.id, actor="orchestrator",
        event_type="approval_requested", action="create_approval_request",
        input_payload=None, output_payload=None,
        decision="pending", reason=f"Order amount {order.amount} requires human approval",
        amount_involved=order.amount, running_budget_spent=None,
    )
    return approval


def resolve_approval(db, approval_id: str, decision: str, resolver: str) -> dict:
    """
    Called when a human approves or rejects a pending order.
    decision must be either 'approve' or 'reject'.
    """
    approval = db.query(Approval).filter(Approval.id == approval_id).first()
    if not approval:
        return {"status": "error", "reason": "Approval not found"}

    if approval.status != "pending":
        return {"status": "error", "reason": f"Approval already resolved as {approval.status}"}

    order = db.query(Order).filter(Order.id == approval.order_id).first()
    session = db.query(AgentSession).filter(AgentSession.id == order.session_id).first()

    if decision == "approve":
        approval.status = "approved"
        order.status = "created"

        session.budget_spent += order.amount

        reason = f"Order manually approved by {resolver}"
        audit_decision = "allowed"
    elif decision == "reject":
        approval.status = "rejected"
        order.status = "failed"

        reason = f"Order manually rejected by {resolver}"
        audit_decision = "blocked"
    else:
        return {"status": "error", "reason": "decision must be 'approve' or 'reject'"}

    approval.resolved_at = datetime.now(timezone.utc)
    approval.resolver = resolver
    db.commit()

    log_event(
        db, session_id=order.session_id, order_id=order.id, actor="human",
        event_type="approval_decision", action="resolve_approval",
        input_payload=None, output_payload=None,
        decision=audit_decision, reason=reason,
        amount_involved=order.amount, running_budget_spent=session.budget_spent,
    )

    return {"status": approval.status, "order_status": order.status}