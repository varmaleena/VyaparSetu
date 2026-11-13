"""Native ADK graph for the invoice intake and understanding tools."""

from collections.abc import AsyncGenerator
from uuid import uuid4

from google.adk.agents.context import Context
from google.adk.events import Event, EventActions
from google.adk.tools import FunctionTool
from google.adk.workflow import Workflow
from google.adk.workflow._graph import EdgeItem
from pydantic import PrivateAttr

from app.agents.tool_events import reply, tool_call, tool_result
from app.models.invoice import InvoiceIntakeResult, InvoiceUnderstandingResult


class InvoiceWorkflow(Workflow):
    _tools: tuple[FunctionTool, ...] = PrivateAttr()

    def __init__(
        self,
        intake: FunctionTool,
        understanding: FunctionTool | None = None,
        *,
        show_json: bool = False,
    ) -> None:
        async def invoice_intake(ctx: Context) -> AsyncGenerator[Event, None]:
            call_id = str(uuid4())
            yield tool_call(intake, call_id, {})
            result = InvoiceIntakeResult.model_validate(
                await intake.run_async(args={}, tool_context=ctx)
            )
            yield tool_result(intake, call_id, result.status, result.code)
            state = {
                "invoice_intake_result": result.model_dump(mode="json"),
                "invoice_image_ref": result.invoice_image_ref,
                "invoice_understanding_result": None,
                "invoice_structured": None,
                "supplier_verification_result": None,
                "duplicate_check_result": None,
                "pricing_anomaly_result": None,
                "cashflow_forecast": None,
                "repayment_capacity": None,
                "payment_decision": None,
            }
            message = result.message
            if result.intake_id:
                message += f" Intake ID: {result.intake_id}"
            if (
                understanding is not None
                and result.status == "ACCEPTED"
                and result.intake_id
            ):
                yield Event(
                    actions=EventActions(state_delta=state, route="accepted"),
                    output=result.model_dump(mode="json"),
                )
            else:
                yield Event(
                    content=reply(message), actions=EventActions(state_delta=state)
                )

        async def invoice_understanding(
            ctx: Context, node_input: InvoiceIntakeResult
        ) -> AsyncGenerator[Event, None]:
            assert understanding is not None and node_input.intake_id is not None
            args = {"intake_id": node_input.intake_id}
            call_id = str(uuid4())
            yield tool_call(understanding, call_id, args)
            result = InvoiceUnderstandingResult.model_validate(
                await understanding.run_async(args=args, tool_context=ctx)
            )
            yield tool_result(understanding, call_id, result.status, result.code)
            invoice = result.invoice
            verified_input = (
                {
                    "intake_id": node_input.intake_id,
                    "invoice": invoice.model_dump(mode="json"),
                }
                if result.status == "EXTRACTED" and invoice is not None
                else None
            )
            yield Event(
                output=verified_input,
                content=reply(
                    f"{node_input.message} Intake ID: {node_input.intake_id}\n\n"
                    + understanding_message(result, show_json=show_json)
                ),
                actions=EventActions(
                    state_delta={
                        "invoice_understanding_result": result.model_dump(mode="json"),
                        "invoice_structured": invoice.model_dump(mode="json")
                        if result.status == "EXTRACTED" and invoice is not None
                        else None,
                    }
                ),
            )

        edges: list[EdgeItem] = [("START", invoice_intake)]
        if understanding is not None:
            edges.append((invoice_intake, {"accepted": invoice_understanding}))
        super().__init__(
            name="invoice_workflow",
            description="Store and validate supplier invoices.",
            edges=edges,
        )
        self._tools = (intake,) if understanding is None else (intake, understanding)

    @property
    def tools(self) -> tuple[FunctionTool, ...]:
        return self._tools


def understanding_message(
    result: InvoiceUnderstandingResult, *, show_json: bool
) -> str:
    invoice = result.invoice
    message = result.message
    if result.status != "EXTRACTED" or invoice is None or invoice.total_paise is None:
        return message
    whole, paise = divmod(invoice.total_paise, 100)
    message += f" Total: INR {whole:,}.{paise:02}. Line items: {len(invoice.lines)}."
    if invoice.discount_status == "none":
        message += " No early-payment discount was shown."
    elif invoice.discount and invoice.discount.rate_bps is not None:
        whole_rate, decimal_rate = divmod(invoice.discount.rate_bps, 100)
        message += f" Early-payment discount: {whole_rate}.{decimal_rate:02}%."
        message += f" Deadline: {invoice.discount.deadline}."
    if result.lines_missing_price_inputs:
        lines = ", ".join(map(str, result.lines_missing_price_inputs))
        message += f" Missing unit-price comparison inputs on lines {lines}."
    if show_json:
        payload = invoice.model_dump_json(indent=2).replace(chr(96), chr(92) + "u0060")
        message += f"\n\nValidated invoice JSON\n\n```json\n{payload}\n```"
    return message
