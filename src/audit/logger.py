from src.db.models import AuditLog


def log_event(
    db,
    session_id: str,
    order_id: str | None,
    actor: str,
    event_type: str,
    action: str,
    input_payload: str | None,
    output_payload: str | None,
    decision: str | None,
    reason: str | None,
    amount_involved: int | None = None,
    running_budget_spent: int | None = None,
):
    """
    Writes a single audit log entry. This is the ONLY place in the entire
    codebase that should insert rows into audit_logs — every orchestrator
    decision must go through this function.
    """
    entry = AuditLog(
        session_id=session_id,
        order_id=order_id,
        actor=actor,
        event_type=event_type,
        action=action,
        input_payload=input_payload,
        output_payload=output_payload,
        decision=decision,
        reason=reason,
        amount_involved=amount_involved,
        running_budget_spent=running_budget_spent,
    )
    db.add(entry)
    db.commit()
    return entry