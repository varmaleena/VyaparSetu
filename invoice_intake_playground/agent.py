"""Local ADK Playground entrypoint."""

from google.adk.apps import App

from app.agents.merchant_workflow import build_merchant_workflow
from app.config.settings import get_settings

settings = get_settings()
if not settings.invoice_playground_enabled or not settings.invoice_bucket:
    raise RuntimeError(
        "Set INVOICE_PLAYGROUND_ENABLED=true and INVOICE_BUCKET to use this local demo."
    )

root_agent = build_merchant_workflow(settings)
app = App(name="invoice_intake_playground", root_agent=root_agent)
