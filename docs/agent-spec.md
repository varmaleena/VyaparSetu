# Agent specification

The foundation exposes an empty ADK sequential root. Add workflow stages in the order specified in the architecture. The three parallel checks use independent state keys: `supplier_verification_result`, `duplicate_check_result`, and `pricing_anomaly_result`.

Phase 0 exposes an ADK session through the existing entry point. Each later agent cycle
adds its implementation and independent tests before adding it to the root workflow.

The native ADK `invoice_workflow` graph displays `invoice_intake` and
`invoice_understanding` as two steps backed by ADK FunctionTools. The graph
routes to understanding only when intake accepts an image. Intake validates a bounded
image, stores it in private Cloud Storage, and records its audit event in PostgreSQL.
The workflow publishes `invoice_intake_result` and `invoice_image_ref` to ADK state.
The standalone upload API keeps invoice bytes outside ADK message history.

The `invoice_understanding` tool reads the Cloud Storage reference from the persisted intake record
for the same merchant and session. Gemini returns typed invoice fields. The validation tool
checks line totals, dates, and early-payment terms before publishing `invoice_structured`.

## Supplier verification

The playground root invokes `supplier_risk_workflow` after successful invoice extraction.
Its first tool checks GSTIN format and checksum, then compares the supplier and payout
account holder against the seeded PostgreSQL registry. A verified result contains a
masked account reference. Review, blocked, and unavailable results contain a reason code.
The registry contains synthetic payout evidence for this cycle.

The `duplicate_invoice_check` tool runs in parallel with supplier verification.
It scopes history to the merchant and supplier, checks the image hash and normalized
invoice fingerprint, and flags same-date bills with a matching number or an amount within
1% for review. A prior ledger invoice with the same number also requires review.
The tool writes `duplicate_check_result` and links a matching prior record when available.

The `pricing_anomaly_check` tool runs alongside supplier and duplicate checks.
It compares a bill with the referenced synthetic purchase order for the same merchant and
supplier. Matching requires the same product description, HSN, unit, and a known pre-tax
basis. Missing or ambiguous references produce `NOT_COMPARABLE` while the other checks
continue. The tool publishes `pricing_anomaly_result` with line evidence. A large
early-payment discount is a separate confirmation flag.

## Payment decision

The `payment_decision_workflow` runs after cash-flow sizing. It loads demo cash
and instant-settlement availability, compares full-bill payment routes, and applies
the repayment cap and positive-net-savings rule. The result is published as
`payment_decision`. The demo models flat financing cost at 6 basis points per day
over ten days and uses the same synthetic as-of date as the settlement forecast.
