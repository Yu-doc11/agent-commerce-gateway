# Agent-to-Agent Commerce Gateway

An autonomous buyer agent that shops on behalf of a user within a fixed budget — searching a merchant catalog, deciding what to buy, and completing real Razorpay test-mode transactions — all gated behind a guardrail layer that enforces spend limits, blocks duplicate orders, requires human approval above a threshold, and logs every decision to an auditable trail.

Built for the **Razorpay AI Builder Internship 2026 — Track 1: AI Growth & Agentic Commerce**.

## 🎥 Demo

[Demo video link here]

![Dashboard screenshot](docs/dashboard_screenshot.png)

## Why this exists

NPCI's Unified AI Payments protocol and the global agentic-commerce protocol race (ACP, AP2, x402) make one thing clear: AI agents are starting to transact on behalf of people. This project explores the other half of that problem — **how does a merchant safely let an AI agent buy from it?** Every money-moving action here is explainable, bounded, and gated, with a full audit trail and a demonstrated failure case handled gracefully.

## Architecture
                    ┌─────────────────────────┐
                     │   Streamlit Dashboard    │
                     │ (audit feed + approvals) │
                     └───────────▲──────────────┘
                                 │ reads
                                 │

┌────────────┐ tool calls ┌─────┴─────────────┐ guarded calls ┌──────────────┐
│ Buyer Agent│───────────────▶│ Orchestrator │───────────────▶│ Razorpay API │
│ (Groq LLM) │◀───────────────│ (guardrails + │◀───────────────│ (test mode) │
└────────────┘ results │ state machine) │ order/payment └──────────────┘
└─────┬───────┬──────┘
│ │
writes │ │ reads
▼ ▼
┌────────────────────────┐
│ SQLite DB │
│ products / sessions / │
│ orders / payments / │
│ approvals / audit_logs │
└────────────────────────┘


The Buyer Agent never touches the database or Razorpay directly — it can only call a fixed set of tools, all of which route through the FastAPI layer into the orchestrator. Every orchestrator decision — allowed or blocked — is logged **before** any action is taken.

## Guardrails

| Guardrail | What it prevents | Where it's enforced |
|---|---|---|
| Session spend limit | Agent can't exceed its total allocated budget | `src/orchestrator/guardrails.py::check_session_budget` |
| Per-transaction hard cap | No single order above an absolute ceiling, ever | `src/orchestrator/guardrails.py::check_transaction_limit` |
| Idempotency / duplicate check | Same purchase intent can't create two orders (e.g. on retry) | `src/orchestrator/guardrails.py::check_duplicate_order` |
| Human approval threshold | Orders above a threshold pause for manual sign-off before proceeding | `src/orchestrator/approval.py` |
| Audit trail | Every decision — allowed, blocked, or pending — is logged with a human-readable reason | `src/audit/logger.py` |

## A real failure, handled gracefully

Run:
```bash
python scripts/inject_failure.py
```
This simulates an agent retry (the same order sent twice — e.g. after a network hiccup). The first order succeeds; the orchestrator detects the duplicate via its idempotency key **before it ever reaches Razorpay**, blocks it, and logs why — without halting the rest of the session.

Sample audit log entries from this run:
```json
{"event_type": "order_created", "decision": "allowed", "reason": "Order created within limits"}
{"event_type": "duplicate_blocked", "decision": "blocked", "reason": "Duplicate order detected: idempotency_key '...' already used in order ..."}
```

## Quickstart

```bash
# 1. Clone and enter the repo
git clone https://github.com/Yu-doc11/agent-commerce-gateway.git
cd agent-commerce-gateway

# 2. Set up a virtual environment
python -m venv venv
source venv/Scripts/activate   # Windows Git Bash
# source venv/bin/activate     # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Fill in RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET (test mode), and GROQ_API_KEY

# 5. Seed the database
python -m src.db.seed

# 6. Start the API server (keep this running)
uvicorn src.main:app --reload

# 7. In a new terminal, start the dashboard
streamlit run src/dashboard/app.py

# 8. In another terminal, try the failure scenario
python scripts/inject_failure.py
```

## Tech stack

- **Backend:** Python, FastAPI, SQLAlchemy, SQLite
- **LLM / Agent reasoning:** Groq API (`openai/gpt-oss-20b`) with tool-calling
- **Payments:** Razorpay test-mode Orders API (real) + a deliberately isolated simulated payment-capture step
- **Dashboard:** Streamlit

## Folder structure

agent-commerce-gateway/
├── src/
│ ├── main.py # FastAPI entrypoint
│ ├── config.py # guardrail limits, loaded from .env
│ ├── db/ # models, database engine, seed script
│ ├── catalog/ # (product listing helpers)
│ ├── agent/ # buyer_agent.py, tools.py
│ ├── orchestrator/ # orchestrator.py, guardrails.py, approval.py
│ ├── payments/ # razorpay_client.py
│ ├── audit/ # logger.py
│ └── dashboard/ # Streamlit app
├── data/ # seed_catalog.json
├── scripts/ # inject_failure.py
└── tests/


## A note on payment capture

Razorpay's Orders API is fully server-side — the orders created in this project are real, test-mode orders visible on the Razorpay dashboard. Actually **capturing** a card payment, however, requires Razorpay's Checkout UI by design (PCI-DSS compliance — there's no plain server-to-server "charge this card" endpoint). Since the buyer agent has no human present to enter card details, the payment-capture step is deliberately simulated and isolated in `src/payments/razorpay_client.py::simulate_payment_capture`, so the real/simulated boundary is explicit and easy to swap out later.

## Explicitly out of scope (for this MVP)

- Multi-agent negotiation (buyer and seller both as agents)
- Multiple merchants / a marketplace
- Full implementation of ACP / AP2 / x402 as protocols
- Authentication / user accounts
- Fraud or risk-scoring ML

These were cut deliberately to keep the guardrail and audit-trail engineering — the actual focus of this track — solid rather than spreading effort thin.

## License

MIT
