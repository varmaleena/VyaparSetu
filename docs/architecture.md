# Architecture

The ADK workflow lives in `app/agents` and is exposed by `app/fast_api_app.py`. The planned workflow sequences invoice intake and understanding, parallel supplier/duplicate/pricing checks, cashflow, arbitrage, policy, voice consent, simulated payment, and repayment monitoring. Deterministic tools own policy, consent validation, and financial actions. Shared session state connects the stages.

## Phase 0 data flow

FastAPI serves the existing ADK app. Local ADK sessions use the scaffold's in-memory service.
PostgreSQL stores durable domain records, and Redis is available for later short-lived caches.
The initial Alembic migration creates the ledger and payment idempotency constraint.
