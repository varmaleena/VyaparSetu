"""Native ADK graph for deterministic supplier risk tools."""

from collections.abc import AsyncGenerator
from uuid import uuid4

from google.adk.agents.context import Context
from google.adk.events import Event, EventActions
from google.adk.workflow import FunctionNode, JoinNode, Workflow

from app.agents.tool_events import reply, tool_call, tool_result
from app.models.invoice import RiskInvoiceInput
from app.models.invoice_duplicate import DuplicateCheckResult
from app.models.pricing import PricingResult
from app.models.supplier import SupplierVerificationInput, SupplierVerificationResult
from app.services.invoice_duplicate_repository import InvoiceDuplicateRepository
from app.services.purchase_order_repository import PurchaseOrderRepository
from app.services.supplier_repository import SupplierRepository
from app.tools.invoice_duplicate_check import build_duplicate_invoice_tool
from app.tools.pricing_anomaly_check import build_pricing_anomaly_tool
from app.tools.supplier_verification import build_supplier_verification_tool


def build_supplier_risk_workflow(
    repository: SupplierRepository,
    duplicates: InvoiceDuplicateRepository,
    purchase_orders: PurchaseOrderRepository,
    *,
    price_tolerance_bps: int = 1000,
    discount_threshold_bps: int = 500,
    demo_merchant: str | None = None,
) -> Workflow:
    supplier_tool = build_supplier_verification_tool(repository.find_by_gstin)
    duplicate_tool = build_duplicate_invoice_tool(
        duplicates, demo_merchant=demo_merchant
    )

    pricing_tool = build_pricing_anomaly_tool(
        purchase_orders,
        demo_merchant=demo_merchant,
        price_tolerance_bps=price_tolerance_bps,
        discount_threshold_bps=discount_threshold_bps,
    )

    async def supplier_verification_step(
        ctx: Context,
        node_input: RiskInvoiceInput | None,
    ) -> AsyncGenerator[Event, None]:
        if node_input is None:
            return
        request = SupplierVerificationInput(
            intake_id=node_input.intake_id,
            supplier_name=node_input.invoice.supplier_name or "",
            supplier_gstin=node_input.invoice.supplier_gstin,
        )
        call_id = str(uuid4())
        yield tool_call(supplier_tool, call_id, {"intake_id": request.intake_id})
        result = SupplierVerificationResult.model_validate(
            await supplier_tool.run_async(
                args={"request": request.model_dump(mode="json")},
                tool_context=ctx,
            )
        )
        yield tool_result(supplier_tool, call_id, result.status, result.code)
        message = result.message
        if result.masked_payout_account:
            message += f" Payout account: {result.masked_payout_account}."
        yield Event(
            content=reply(message),
            output=result.model_dump(mode="json"),
            actions=EventActions(
                state_delta={
                    "supplier_verification_result": result.model_dump(mode="json")
                }
            ),
        )

    async def duplicate_invoice_step(
        ctx: Context,
        node_input: RiskInvoiceInput | None,
    ) -> AsyncGenerator[Event, None]:
        if node_input is None:
            return
        call_id = str(uuid4())
        yield tool_call(duplicate_tool, call_id, {"intake_id": node_input.intake_id})
        result = DuplicateCheckResult.model_validate(
            await duplicate_tool.run_async(
                args={"request": node_input.model_dump(mode="json")},
                tool_context=ctx,
            )
        )
        yield tool_result(duplicate_tool, call_id, result.status, result.code)
        message = result.message
        if match := result.matched_intake_id or result.matched_invoice_id:
            message += f" Prior record: {match}."
        payload = result.model_dump(mode="json")
        yield Event(
            content=reply(message),
            output=payload,
            actions=EventActions(state_delta={"duplicate_check_result": payload}),
        )

    async def pricing_anomaly_step(
        ctx: Context,
        node_input: RiskInvoiceInput | None,
    ) -> AsyncGenerator[Event, None]:
        if node_input is None:
            return
        call_id = str(uuid4())
        yield tool_call(pricing_tool, call_id, {"intake_id": node_input.intake_id})
        result = PricingResult.model_validate(
            await pricing_tool.run_async(
                args={"request": node_input.model_dump(mode="json")}, tool_context=ctx
            )
        )
        yield tool_result(pricing_tool, call_id, result.status, result.code)
        message = result.message
        for line in result.lines:
            if (
                line.status == "PRICE_VARIANCE"
                and line.invoice_price_paise is not None
                and line.reference_price_paise is not None
                and line.difference_paise is not None
            ):

                def inr(paise: int) -> str:
                    whole, fraction = divmod(paise, 100)
                    return f"INR {whole:,}.{fraction:02}"

                message += (
                    f" Line {line.line_number}: {inr(line.invoice_price_paise)} on the invoice"
                    f" versus {inr(line.reference_price_paise)} on the PO"
                    f" ({inr(line.difference_paise)} higher)."
                )
        if (
            result.discount_requires_confirmation
            and result.code != "CONFIRM_DISCOUNT_TERMS"
        ):
            message += " Confirm the early-payment discount separately."
        payload = result.model_dump(mode="json")
        yield Event(
            content=reply(message),
            output=payload,
            actions=EventActions(state_delta={"pricing_anomaly_result": payload}),
        )

    supplier_step = FunctionNode(
        func=supplier_verification_step, name=supplier_tool.name
    )
    duplicate_step = FunctionNode(func=duplicate_invoice_step, name=duplicate_tool.name)
    pricing_step = FunctionNode(func=pricing_anomaly_step, name=pricing_tool.name)
    checks = (supplier_step, duplicate_step, pricing_step)
    return Workflow(
        name="supplier_risk_workflow",
        description="Check the supplier, registered payee, prior submissions, and purchase-order prices.",
        edges=[("START", checks), (checks, JoinNode(name="risk_results"))],
    )
