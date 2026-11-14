# Architecture

VyaparSetu has two execution paths. The browser demo uses FastAPI and Python services. The separate merchant API runs workflows through Google ADK.

## Browser demo

| Stage | Implementation |
| --- | --- |
| Invoice intake | The merchant UI posts the document to `/api/invoice/process`. Local extraction reads PDF text or runs RapidOCR. Gemini can supplement incomplete extraction when configured. |
| Invoice review | The upload route parses amounts and dates, checks the supplier GSTIN checksum, and uses the shared synthetic QR history for `demo-merchant-00`. A checksum pass does not establish bank-account ownership. |
| Payment planning | The forecast projects daily funds from weekday settlement history. Payment options apply the shop reserve, estimated available cash, and affordability limits. Loan review links to the existing Paytm Business Loan page. |
| Soundbox | The merchant reviews the date, amounts, and set-aside schedule. Sarvam reads localized text on demand. The approval button confirms the displayed plan. |
| Payment tracking | Simulated settlement advances apply the approved daily schedule. The tracker records a reminder and either a simulated payment or a skipped outcome. The merchant can preview withdrawals or cancel. |

`app/api/enterprise_routes.py` coordinates the browser path. Shared calculations live in `app/tools/cashflow_tools.py` and `app/services/payment_options.py`. The UI is served from `app/merchant_ui/`.

## Events and storage

The workflow graph consumes server-sent events from `/api/workflow-runs/{run_id}/events`. Its nodes represent FastAPI workflow events. The API supplies elapsed time for instrumented steps and records merchant outcomes as they occur.

Browser-demo decisions, audit records, and savings plans are process-local. A restart clears active demo state. Reminders appear in the activity feed when the simulated clock advances. The demo does not pull live QR balances or initiate real payments.

## Google ADK path

`app/agent.py` exposes the root agent. The `/merchant/runs/...` API uses an ADK Runner with the workflow assembled in `app/agents/merchant_workflow.py`. It includes invoice intake, supplier and pricing checks, settlement-history forecasting, payment proposals, and repayment monitoring. PostgreSQL stores domain records in this path. Alembic manages the schema and the seed command provides synthetic local data.

A production launch would need merchant authentication, verified payees, durable plans and receipts, actual settlement data, scheduled execution, and delivery of reminders outside the browser.
