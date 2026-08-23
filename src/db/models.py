import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def gen_uuid():
    return str(uuid.uuid4())


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    price = Column(Integer, nullable=False)  # in paise
    stock = Column(Integer, nullable=False, default=0)
    category = Column(String, nullable=True)


class AgentSession(Base):
    __tablename__ = "agent_sessions"

    id = Column(String, primary_key=True, default=gen_uuid)
    goal = Column(String, nullable=False)
    budget_total = Column(Integer, nullable=False)  # paise
    budget_spent = Column(Integer, nullable=False, default=0)
    status = Column(String, nullable=False, default="active")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, default=gen_uuid)
    session_id = Column(String, ForeignKey("agent_sessions.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    amount = Column(Integer, nullable=False)
    idempotency_key = Column(String, unique=True, nullable=False)
    razorpay_order_id = Column(String, nullable=True)
    status = Column(String, nullable=False, default="created")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String, primary_key=True, default=gen_uuid)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    razorpay_payment_id = Column(String, nullable=True)
    status = Column(String, nullable=False, default="attempted")
    amount = Column(Integer, nullable=False)
    captured_at = Column(DateTime, nullable=True)


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(String, primary_key=True, default=gen_uuid)
    order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    requested_amount = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="pending")
    requested_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime, nullable=True)
    resolver = Column(String, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=gen_uuid)
    session_id = Column(String, nullable=False)
    order_id = Column(String, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    actor = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    action = Column(String, nullable=False)
    input_payload = Column(String, nullable=True)
    output_payload = Column(String, nullable=True)
    decision = Column(String, nullable=True)
    reason = Column(String, nullable=True)
    amount_involved = Column(Integer, nullable=True)
    running_budget_spent = Column(Integer, nullable=True)