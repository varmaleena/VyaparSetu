# Test plan

Verify the root imports and the health endpoint returns 200. When workflow stages are implemented, add deterministic calculation and policy tests plus integration cases for full and partial funding, declines, fraud, and payment failures.

Phase 0 covers API health, ADK session creation, local console trace export, reproducible seed
counts, and two matched invoice fixtures with different settlement histories. Run the Alembic
upgrade and seed twice against PostgreSQL, and run the Redis connectivity command after starting
the Compose services.

## Phases 1 through 4

- Verify invoice image validation, merchant-scoped intake, structured extraction, and clarification.
- Verify supplier registry checks, duplicate detection (including concurrent submissions in PostgreSQL),
  and purchase-order price comparisons.
- Verify that unresolved risk skips cash-flow sizing and that the seeded merchants produce different
  repayment caps under the same policy.
- Verify that payment decisions compare cash, instant settlement, financing, and waiting. Confirm
  the full discounted balance is covered and the installment stays within the calculated cap.
- Run the opt-in PostgreSQL tests with `VYAPARSETU_TEST_POSTGRES=1` after applying migrations and
  seeding. Use `VYAPARSETU_TEST_PORT` to select a free port when the playground is running.
- Run `make lint` and `make typecheck` for Ruff and mypy.
