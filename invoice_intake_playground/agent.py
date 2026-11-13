"""Local ADK playground for the invoice workflow."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from google import genai
from google.adk.apps import App
from google.adk.workflow import FunctionNode, Workflow
from google.genai import types

from app.agents.cashflow_workflow import build_cashflow_workflow
from app.agents.invoice_workflow import InvoiceWorkflow
from app.agents.payment_decision_workflow import build_payment_decision_workflow
from app.agents.playground_payment_review import build_payment_review
from app.agents.repayment_monitoring_agent import build_repayment_monitoring_workflow
from app.agents.supplier_risk_workflow import build_supplier_risk_workflow
from app.config.settings import get_settings
from app.services.gemini_service import GeminiInvoiceExtractor
from app.services.invoice_duplicate_repository import InvoiceDuplicateRepository
from app.services.invoice_intake import create_invoice_intake
from app.services.payment_options_repository import PaymentOptionsRepository
from app.services.payment_proposals import PaymentProposals
from app.services.purchase_order_repository import PurchaseOrderRepository
from app.services.settlement_repository import SettlementRepository
from app.services.supplier_repository import SupplierRepository
from app.tools.invoice_workflow_tools import build_intake_tool, build_understanding_tool

settings = get_settings()
if not settings.invoice_playground_enabled or not settings.invoice_bucket:
    raise RuntimeError(
        "Set INVOICE_PLAYGROUND_ENABLED=true and INVOICE_BUCKET to use this local demo."
    )

intake = create_invoice_intake(settings)
client = genai.Client(
    vertexai=True,
    project=settings.invoice_gcp_project,
    location=settings.invoice_gemini_location,
    http_options=types.HttpOptions(api_version="v1", timeout=30000),
)
invoice_workflow = InvoiceWorkflow(
    build_intake_tool(intake, demo_merchant=settings.invoice_demo_merchant_id),
    build_understanding_tool(
        intake.repository,
        GeminiInvoiceExtractor(client, settings.invoice_gemini_model),
        demo_merchant=settings.invoice_demo_merchant_id,
    ),
    show_json=True,
)
supplier_risk_workflow = build_supplier_risk_workflow(
    SupplierRepository(intake.repository.engine),
    InvoiceDuplicateRepository(intake.repository.engine),
    PurchaseOrderRepository(intake.repository.engine),
    price_tolerance_bps=settings.pricing_po_tolerance_bps,
    discount_threshold_bps=settings.pricing_discount_review_bps,
    demo_merchant=settings.invoice_demo_merchant_id,
)
funding_repository = PaymentOptionsRepository(intake.repository.engine)


def evaluation_date() -> date:
    return settings.scenario_date or datetime.now(ZoneInfo("Asia/Kolkata")).date()


settlements = SettlementRepository(intake.repository.engine)
cashflow_workflow = build_cashflow_workflow(
    settlements,
    funding_repository=funding_repository,
    policy_share_bps=settings.repayment_share_bps,
    stress_bps=settings.settlement_stress_bps,
    as_of=evaluation_date,
    demo_merchant=settings.invoice_demo_merchant_id,
)
proposals = PaymentProposals(intake.repository.engine)
payment_decision_workflow = build_payment_decision_workflow(
    funding_repository,
    as_of=evaluation_date(),
    proposals=proposals,
    playground_review=True,
    demo_merchant=settings.invoice_demo_merchant_id,
)
review = FunctionNode(
    func=build_payment_review(
        proposals,
        settings.invoice_demo_merchant_id,
        evaluation_date,
        settings.pricing_discount_review_bps,
    ),
    name="merchant_payment_review",
)
repayment_monitoring = build_repayment_monitoring_workflow(
    proposals,
    settlements,
    settings.invoice_demo_merchant_id,
    evaluation_date,
    settings.repayment_share_bps,
)
root_agent = Workflow(
    name="vyaparsetu",
    description="Process an invoice and check its supplier.",
    edges=[
        ("START", review),
        (
            review,
            {
                "invoice": invoice_workflow,
                "offer": payment_decision_workflow,
                "repayment": repayment_monitoring,
            },
        ),
        (invoice_workflow, supplier_risk_workflow),
        (supplier_risk_workflow, cashflow_workflow),
        (cashflow_workflow, payment_decision_workflow),
    ],
)
app = App(name="invoice_intake_playground", root_agent=root_agent)
