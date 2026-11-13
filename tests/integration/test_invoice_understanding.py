"""Exercise invoice understanding without invoking the intake agent or Gemini."""

import asyncio
import json
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest
from google.adk.cli.agent_graph import get_agent_graph
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.workflow import Workflow
from google.genai import types

from app.agents.cashflow_workflow import build_cashflow_workflow
from app.agents.invoice_workflow import InvoiceWorkflow
from app.agents.payment_decision_workflow import build_payment_decision_workflow
from app.agents.supplier_risk_workflow import build_supplier_risk_workflow
from app.models.decision import FinancingOffer, Funding
from app.models.invoice import (
    EarlyPaymentTerms,
    ExtractedInvoice,
    InvoiceIntakeResult,
    InvoiceLine,
)
from app.models.invoice_duplicate import DuplicateCheckResult
from app.models.supplier import SupplierRegistryRecord
from app.services.gemini_service import GeminiInvoiceExtractor
from app.services.invoice_duplicate_repository import InvoiceDuplicateRepository
from app.services.invoice_intake import InvoiceIntake
from app.services.invoice_repository import IntakeObject, InvoiceRepository
from app.services.payment_options_repository import PaymentOptionsRepository
from app.services.purchase_order_repository import PurchaseOrderRepository
from app.services.seed_data import AS_OF, build_seed
from app.services.settlement_repository import SettlementRepository
from app.services.supplier_repository import SupplierRepository
from app.tools.invoice_workflow_tools import build_intake_tool, build_understanding_tool


def sample_invoice() -> ExtractedInvoice:
    return ExtractedInvoice(
        supplier_name="Demo Supplier",
        supplier_gstin="36AAAAA0000A1Z3",
        invoice_number="DEMO-42",
        invoice_date=date(2026, 11, 12),
        due_date=date(2026, 11, 27),
        currency="INR",
        lines=[
            InvoiceLine(
                description="Rice",
                hsn="1006",
                quantity=Decimal("40"),
                unit="bags",
                unit_price_paise=100_000,
                amount_paise=4_000_000,
            )
        ],
        total_paise=4_000_000,
        tax_added_paise=0,
        adjustment_paise=0,
        discount_status="offered",
        discount=EarlyPaymentTerms(
            rate_bps=300,
            amount_paise=120_000,
            deadline=date(2026, 11, 12),
            requires_full_payment=True,
        ),
    )


@pytest.mark.parametrize(
    ("case", "status", "code"),
    [
        ("valid", "EXTRACTED", "FIELDS_VALIDATED"),
        ("missing_unit", "EXTRACTED", "FIELDS_VALIDATED"),
        ("missing_discount", "NEEDS_CLARIFICATION", "DISCOUNT_UNCLEAR"),
        ("total_mismatch", "NEEDS_CLARIFICATION", "TOTAL_MISMATCH"),
        ("discount_mismatch", "NEEDS_CLARIFICATION", "DISCOUNT_MISMATCH"),
        ("provider_error", "UNAVAILABLE", "EXTRACTION_FAILED"),
        ("wrong_owner", "UNAVAILABLE", "INTAKE_NOT_FOUND"),
        ("rejected_intake", None, None),
    ],
)
def test_invoice_workflow_tools(
    case: str, status: str | None, code: str | None
) -> None:
    repository = Mock(spec=InvoiceRepository)
    stored = IntakeObject("gs://private-bucket/intake/abc", "image/png")
    repository.get_invoice_object.return_value = (
        None if case == "wrong_owner" else stored
    )
    extractor = Mock(spec=GeminiInvoiceExtractor)
    extractor.extract = AsyncMock(return_value=sample_invoice())
    invoice = extractor.extract.return_value
    if case == "missing_unit":
        invoice.lines[0].unit = None
    if case == "missing_discount":
        invoice.discount = None
    if case == "total_mismatch":
        invoice.total_paise += 100
    if case == "discount_mismatch":
        invoice.discount.amount_paise += 100
    if case == "provider_error":
        extractor.extract.side_effect = ValueError("invalid provider response")

    async def check() -> None:
        service = InMemorySessionService()
        intake_service = Mock(spec=InvoiceIntake)
        intake_service.process.return_value = InvoiceIntakeResult(
            status="RETRY_CAPTURE" if case == "rejected_intake" else "ACCEPTED",
            code="TEST_INTAKE",
            message="Test intake",
            intake_id=None if case == "rejected_intake" else "abc",
        )
        agent = InvoiceWorkflow(
            build_intake_tool(intake_service),
            build_understanding_tool(repository, extractor),
            show_json=True,
        )
        assert [tool.name for tool in agent.tools] == [
            "invoice_intake",
            "invoice_understanding",
        ]
        graph = await get_agent_graph(agent, [])
        assert "invoice_intake -> invoice_understanding" in graph.source
        suppliers = Mock(spec=SupplierRepository)
        suppliers.find_by_gstin.return_value = SupplierRegistryRecord(
            id="supplier",
            name="Demo Supplier",
            gstin="36AAAAA0000A1Z3",
            registry_status="ACTIVE",
            payout_account_name="Demo Supplier",
            payout_last4="4200",
            payout_verified=True,
        )
        duplicates = Mock(spec=InvoiceDuplicateRepository)
        duplicates.check.return_value = DuplicateCheckResult(
            intake_id="abc", status="CLEAR", code="NO_DUPLICATE_FOUND", message="Clear"
        )
        orders = Mock(spec=PurchaseOrderRepository)
        risk_workflow = build_supplier_risk_workflow(suppliers, duplicates, orders)
        settlements = Mock(spec=SettlementRepository)
        seed = build_seed()
        settlements.history.return_value = (
            {
                row["settlement_date"]: row["amount"] * 100
                for row in seed["settlements"]
                if row["merchant_id"] == "demo-merchant-00"
            },
            120000,
        )
        cashflow = build_cashflow_workflow(settlements, as_of=AS_OF)
        funding = Mock(spec=PaymentOptionsRepository)
        funding.get.return_value = Funding(
            cash=1_680_000,
            offer=FinancingOffer(
                version="test", daily_rate_bps=6, fee_paise=0, tenor_days=10
            ),
        )
        payment = build_payment_decision_workflow(
            funding, as_of=AS_OF, demo_merchant="merchant"
        )
        root = Workflow(
            name="vyaparsetu",
            edges=[
                ("START", agent),
                (agent, risk_workflow),
                (risk_workflow, cashflow),
                (cashflow, payment),
            ],
        )
        runner = Runner(app_name="agents", agent=root, session_service=service)
        session = await service.create_session(
            app_name="agents",
            user_id="merchant",
            state={
                "invoice_image_ref": "gs://untrusted-state/path",
                "invoice_structured": {"old": "stale result"},
            },
        )
        events = [
            event
            async for event in runner.run_async(
                user_id="merchant",
                session_id=session.id,
                new_message=types.UserContent(
                    parts=[
                        types.Part.from_bytes(data=b"invoice", mime_type="image/png")
                    ]
                ),
            )
        ]
        expected_tools = ["invoice_intake"]
        if case != "rejected_intake":
            expected_tools.append("invoice_understanding")
        if status == "EXTRACTED":
            expected_tools.extend(
                [
                    "supplier_verification",
                    "duplicate_invoice_check",
                    "pricing_anomaly_check",
                    "forecast_settlements",
                    "calculate_repayment_cap",
                    "get_payment_options",
                    "calculate_payment_economics",
                    "apply_payment_policy",
                ]
            )
        calls = [call for event in events for call in event.get_function_calls()]
        responses = [
            response for event in events for response in event.get_function_responses()
        ]
        assert [call.name for call in calls[:2]] == expected_tools[:2]
        assert sorted(call.name for call in calls[2:]) == sorted(expected_tools[2:])
        assert {response.id for response in responses} == {call.id for call in calls}
        delta = {
            key: value
            for event in events
            for key, value in event.actions.state_delta.items()
        }
        if status is None:
            assert delta["invoice_understanding_result"] is None
        else:
            assert delta["invoice_understanding_result"]["status"] == status
            assert delta["invoice_understanding_result"]["code"] == code
            context, intake_id = repository.get_invoice_object.call_args.args
            assert (context.merchant_id, context.session_id, intake_id) == (
                "merchant",
                session.id,
                "abc",
            )
        assert (delta["invoice_structured"] is not None) == (status == "EXTRACTED")
        if status == "EXTRACTED":
            assert delta["repayment_capacity"]["daily_cap_paise"] == 240420
            assert delta["payment_decision"]["status"] == "FINANCING_FITS"
            assert delta["payment_decision"]["selected"]["net_savings"] == 106800
            settlements.history.assert_called_once_with("merchant", AS_OF)
        else:
            settlements.history.assert_not_called()
            funding.get.assert_not_called()

        if status == "EXTRACTED":
            assert delta["supplier_verification_result"]["status"] == "VERIFIED"
            assert delta["duplicate_check_result"]["status"] == "CLEAR"
            assert delta["pricing_anomaly_result"]["status"] == "NOT_COMPARABLE"
            duplicates.check.assert_called_once()
            suppliers.find_by_gstin.assert_called_once_with("36AAAAA0000A1Z3")
        else:
            assert delta["supplier_verification_result"] is None
            assert delta["duplicate_check_result"] is None
            assert delta["pricing_anomaly_result"] is None
            duplicates.check.assert_not_called()
            suppliers.find_by_gstin.assert_not_called()
        if status == "EXTRACTED":
            rendered = next(
                part.text
                for event in events
                if event.content
                for part in event.content.parts or []
                if part.text and "Validated invoice JSON" in part.text
            )
            assert (
                json.loads(rendered.split("```json\n")[1].split("\n```")[0])
                == delta["invoice_structured"]
            )
            assert delta["invoice_understanding_result"][
                "lines_missing_price_inputs"
            ] == ([1] if case == "missing_unit" else [])

    asyncio.run(check())
    if case in {"wrong_owner", "rejected_intake"}:
        extractor.extract.assert_not_awaited()
    else:
        extractor.extract.assert_awaited_once_with(stored)
