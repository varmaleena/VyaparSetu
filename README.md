# VyaparSetu

Google ADK and FastAPI skeleton for an invoice-to-supplier-payment workflow.

- `app/agent.py` is the ADK discovery entry point.
- `app/agents/` holds the sequential root and reserved workflow modules.
- `app/config/`, `app/models/`, `app/tools/`, and `app/services/` hold the application layers.
- `app/fast_api_app.py` serves ADK, A2A, and `GET /healthz`.
- `tests/` and `docs/` hold verification and architecture material.

Install and start locally with `uv sync` and `uv run uvicorn app.fast_api_app:app`. The health endpoint is available at http://127.0.0.1:8000/healthz. Set `ADK_WEB=true` to serve the ADK browser UI or `OTEL_TO_CLOUD=true` to enable Cloud telemetry export.

## Phase 0 local workflow

Install Docker with Compose and run these commands from the project root.

```sh
uv sync --extra lint
docker compose up -d --wait
uv run alembic upgrade head
uv run python -m app.services.seed_data
uv run python -m app.services.redis_service
uv run uvicorn app.fast_api_app:app
```

The optional `.env` overrides the local database and Redis defaults in `.env.example`.
Check `GET /healthz` and create a session with `POST /apps/app/users/demo/sessions`
using `{}` as the request body. Set `OTEL_CONSOLE=true` before startup to print
request traces alongside structured server logs.

The seed contains 20 merchants, 50 suppliers, 500 invoices, and 90 days of
settlements per merchant. The two `DEMO-OFFER` invoices are a fixed synthetic
snapshot dated 2026-11-12. Re-running the seed preserves existing records.

Run `make lint`, `make typecheck`, and `make test` before starting the next phase.

## Invoice intake

Run `uv run alembic upgrade head` and set `INVOICE_BUCKET`, `INVOICE_GCP_PROJECT`,
and a private random `INVOICE_DEMO_TOKEN` in your local environment. The demo token
maps to `INVOICE_DEMO_MERCHANT_ID`, which defaults to the seeded merchant
`demo-merchant-00`. Local Google Cloud requests use Application Default Credentials.

1. Send `POST /invoice-intake/sessions` with `Authorization: Bearer <token>`.
2. Send `POST /invoice-intake/sessions/<session_id>/image` with the same authorization
   and the original image as the raw request body. JPEG, PNG, and WebP are accepted
   up to 10 MiB. Use `Content-Type: image/png` for a PNG.
3. On acceptance, the response includes the intake ID and private `gs://` reference.

The independent intake runner uses process-local sessions and a single demo merchant.
A production deployment requires merchant identity integration, a shared session
store, and a workload identity with object permissions scoped to the invoice bucket.

For a local browser test, set `INVOICE_PLAYGROUND_ENABLED=true` and start
`agents-cli playground --host 127.0.0.1`. Select `invoice_intake_playground`
and attach one synthetic invoice. This loopback-only demo uses the configured
demo merchant. ADK Playground can retain attachments in its local session history.

## Invoice understanding

The Phase 1 playground runs the `invoice_workflow` agent. It invokes the
`invoice_intake` and `invoice_understanding` ADK function tools in sequence. Its default model
is `gemini-3.5-flash-lite` in `global`, configurable through
`INVOICE_GEMINI_MODEL` and `INVOICE_GEMINI_LOCATION`. The understanding tool retrieves the stored
image reference scoped to the merchant and session, sends one structured extraction
request, and checks totals, dates, and discount arithmetic. ADK state receives
`invoice_structured` only after the checks pass. Clarifications are reported in
`invoice_understanding_result`.

## Supplier risk demo

After `uv run alembic upgrade head`, rerun `uv run python -m app.services.seed_data`.
Supplier verification uses the seeded registry and returns
`supplier_verification_result` after validated extraction. The verified demo supplier is
Sri Lakshmi Kirana Wholesale, with synthetic GSTIN `36AAAAA0000A1Z3` and payout
account ending in `4200`.

The seeded merchant `demo-merchant-00` has a synthetic POS purchase order `PO-SLW-0042`.
The QR-only demo merchant `demo-merchant-01` has no purchase-order references.
Set `PRICING_PO_TOLERANCE_BPS` and `PRICING_DISCOUNT_REVIEW_BPS` to override
the demo defaults of 10% and 5%, respectively.
