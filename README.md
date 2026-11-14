# VyaparSetu

VyaparSetu helps a Paytm merchant decide when and how to pay a supplier invoice. Upload a bill to see its due date, early-payment discount, and projected QR funds. Keep the original terms, review a QR savings plan, or check Business Loan offers through Paytm.

## Run the merchant demo

Install Python 3.11–3.13 and uv, then run these commands from the repository root.

```sh
uv sync
uv run uvicorn app.fast_api_app:app
```

Open the [merchant app](http://127.0.0.1:8000/merchant/) or check [server health](http://127.0.0.1:8000/healthz).

Optional local configuration in `.env`:

- `SARVAM_API_KEY` enables Sarvam speech in Telugu, Hindi, and English.
- `GEMINI_API_KEY` enables Gemini fallback for eligible incomplete extractions.
- `ADK_WEB=true` enables the separate ADK developer UI.

## Demo walkthrough

1. Upload the [Meadowcrest supplier invoice](sample-supplier-invoice.jpg) and click **Process Invoice**.
2. Compare the original due date with the discount deadline. Check the QR forecast by your chosen date and enter an optional shop reserve.
3. If projected funds cover the discounted bill, choose **Use available funds**. Review the daily set-aside in Soundbox and tap **Approve savings plan**.
4. Advance simulated settlement days to see the balance, reminder, and payment outcome. You can also preview a withdrawal and see whether it puts the discount at risk.
5. Try the [pharmacy invoice](pharmacy-supplier-invoice.jpg) for a larger funding gap. The Paytm Business Loan link opens Paytm’s existing offer flow. Eligibility and terms come from its lending partners.

The example invoices use fixed November 2026 discount dates. After those dates, the app treats the offers as expired. The demo uses one synthetic 90-day QR history. Savings, withdrawals, reminders, and supplier payments are simulated.

## ADK workflow and development

The browser demo runs through FastAPI. The repository also provides a separate Google ADK merchant workflow. For its database-backed local setup:

```sh
docker compose up -d --wait
uv run alembic upgrade head
uv run python -m app.services.seed_data
```

Run `uv run pytest tests` to exercise the test suite. See [Architecture](docs/architecture.md) for the two execution paths and their storage.
