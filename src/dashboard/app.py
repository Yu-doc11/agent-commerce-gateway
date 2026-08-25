import streamlit as st
import requests
import json
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.db.database import SessionLocal
from src.db.models import AgentSession
from src.agent.buyer_agent import run_buyer_agent
from src.orchestrator.approval import resolve_approval

BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Agent-to-Agent Commerce Gateway", layout="wide")
st.title("🛡️ Agent-to-Agent Commerce Gateway")
st.caption("Live control room: buyer agent activity, guardrails, and audit trail")


with st.sidebar:
    st.header("Start a Buyer Agent Session")
    goal = st.text_input("Shopping goal", value="buy a water bottle and a phone stand")
    budget = st.number_input("Budget (₹)", min_value=100, value=1000, step=100)

    if st.button("🚀 Run Buyer Agent"):
        db = SessionLocal()
        import uuid
        session = AgentSession(
            id=str(uuid.uuid4()), goal=goal, budget_total=int(budget * 100),
            budget_spent=0, status="active",
        )
        db.add(session)
        db.commit()
        session_id = session.id
        db.close()

        with st.spinner("Agent is shopping..."):
            transcript = run_buyer_agent(session.id, goal)

        st.session_state["last_transcript"] = transcript
        st.session_state["last_session_id"] = session_id
        st.rerun()

col1, col2 = st.columns(2)

with col1:
    st.subheader("⏳ Pending Approvals")
    try:
        resp = requests.get(f"{BASE_URL}/approvals/pending")
        approvals = resp.json()
    except Exception:
        approvals = []
        st.error("Backend not reachable. Is `uvicorn src.main:app --reload` running?")

    if not approvals:
        st.info("No pending approvals right now.")
    else:
        for a in approvals:
            with st.container(border=True):
                st.write(f"**Order:** `{a['order_id']}`")
                st.write(f"**Amount requested:** ₹{a['requested_amount'] / 100:.2f}")
                c1, c2 = st.columns(2)
                if c1.button("✅ Approve", key=f"approve_{a['id']}"):
                    db = SessionLocal()
                    resolve_approval(db, a["id"], "approve", "dashboard_reviewer")
                    db.close()
                    st.rerun()
                if c2.button("❌ Reject", key=f"reject_{a['id']}"):
                    db = SessionLocal()
                    resolve_approval(db, a["id"], "reject", "dashboard_reviewer")
                    db.close()
                    st.rerun()

with col2:
    st.subheader("📜 Live Audit Trail")
    try:
        resp = requests.get(f"{BASE_URL}/audit/logs")
        logs = resp.json()
    except Exception:
        logs = []

    if not logs:
        st.info("No audit events yet.")
    else:
        for l in logs[:20]:
            decision_color = {
                "allowed": "green", "blocked": "red", "pending": "orange"
            }.get(l["decision"], "gray")
            with st.container(border=True):
                st.markdown(
                    f"**{l['event_type']}** — :{decision_color}[{l['decision']}]"
                )
                st.caption(l["reason"])
                st.caption(f"actor: {l['actor']} | {l['timestamp']}")

if "last_transcript" in st.session_state:
    st.subheader("🤖 Last Agent Run — Step by Step")
    for step in st.session_state["last_transcript"]:
        if step["type"] == "tool_call":
            st.code(json.dumps(step, indent=2), language="json")
        else:
            st.success(step.get("content", ""))