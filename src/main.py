from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from src.db.database import get_db, init_db
from src.db.models import Product, AgentSession, Order, Approval, AuditLog
from src.orchestrator.orchestrator import create_order as orchestrator_create_order
from src.orchestrator.approval import resolve_approval
import uuid

app = FastAPI(title="Agent-to-Agent Commerce Gateway")


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


# --- Catalog ---

@app.get("/catalog/products")
def list_products(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    return [
        {"id": p.id, "name": p.name, "price": p.price, "stock": p.stock, "category": p.category}
        for p in products
    ]


@app.get("/catalog/products/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        return {"error": "Product not found"}
    return {"id": p.id, "name": p.name, "price": p.price, "stock": p.stock, "category": p.category}


# --- Agent sessions ---

@app.post("/agent/session")
def create_session(goal: str, budget_total: int, db: Session = Depends(get_db)):
    session = AgentSession(
        id=str(uuid.uuid4()), goal=goal, budget_total=budget_total,
        budget_spent=0, status="active",
    )
    db.add(session)
    db.commit()
    return {"session_id": session.id, "goal": goal, "budget_total": budget_total}


@app.get("/agent/session/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db)):
    s = db.query(AgentSession).filter(AgentSession.id == session_id).first()
    if not s:
        return {"error": "Session not found"}
    return {
        "id": s.id, "goal": s.goal, "budget_total": s.budget_total,
        "budget_spent": s.budget_spent, "status": s.status,
    }


# --- Orders ---

@app.post("/orders")
def create_order_endpoint(session_id: str, product_id: int, quantity: int, db: Session = Depends(get_db)):
    return orchestrator_create_order(db, session_id, product_id, quantity)


@app.get("/orders/{order_id}")
def get_order(order_id: str, db: Session = Depends(get_db)):
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        return {"error": "Order not found"}
    return {
        "id": o.id, "session_id": o.session_id, "product_id": o.product_id,
        "quantity": o.quantity, "amount": o.amount, "status": o.status,
        "razorpay_order_id": o.razorpay_order_id,
    }


# --- Approvals ---

@app.get("/approvals/pending")
def pending_approvals(db: Session = Depends(get_db)):
    approvals = db.query(Approval).filter(Approval.status == "pending").all()
    return [
        {"id": a.id, "order_id": a.order_id, "requested_amount": a.requested_amount}
        for a in approvals
    ]


@app.post("/approvals/{approval_id}/decision")
def decide_approval(approval_id: str, decision: str, resolver: str = "dashboard_user", db: Session = Depends(get_db)):
    return resolve_approval(db, approval_id, decision, resolver)


# --- Audit ---

@app.get("/audit/logs")
def audit_logs(session_id: str = None, db: Session = Depends(get_db)):
    query = db.query(AuditLog)
    if session_id:
        query = query.filter(AuditLog.session_id == session_id)
    logs = query.order_by(AuditLog.timestamp.desc()).all()
    return [
        {
            "id": l.id, "session_id": l.session_id, "order_id": l.order_id,
            "timestamp": l.timestamp.isoformat(), "actor": l.actor,
            "event_type": l.event_type, "action": l.action,
            "decision": l.decision, "reason": l.reason,
            "amount_involved": l.amount_involved,
        }
        for l in logs
    ]