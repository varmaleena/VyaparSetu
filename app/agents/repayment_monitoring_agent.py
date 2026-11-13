"""Independent ADK workflow for simulated repayment status."""

from collections.abc import AsyncGenerator, Callable
from datetime import date
from uuid import uuid4

from google.adk.agents.context import Context
from google.adk.events import Event, EventActions
from google.adk.tools import FunctionTool, ToolContext
from google.adk.workflow import FunctionNode, Workflow
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from app.agents.tool_events import reply, tool_call, tool_result
from app.models.payment import SimulatedPayment
from app.services.payment_proposals import PaymentProposals
from app.services.settlement_repository import SettlementRepository
from app.tools.repayment_tools import assess_repayment_coverage


def build_repayment_monitoring_workflow(
    proposals: PaymentProposals,
    settlements: SettlementRepository,
    merchant: str,
    today: Callable[[], date],
    policy_share_bps: int,
) -> Workflow:
    async def load_repayment_schedule(
        proposal_id: str, tool_context: ToolContext
    ) -> dict:
        """Read the confirmed receipt for this merchant and session."""
        receipt = await run_in_threadpool(
            proposals.confirmed_receipt, merchant, tool_context.session.id, proposal_id
        )
        return receipt.model_dump(mode="json") if receipt else {}

    async def load_settlement_history(as_of: date) -> dict:
        """Read completed merchant settlements and existing daily deductions."""
        history, existing = await run_in_threadpool(
            settlements.history, merchant, as_of
        )
        return {
            "history": {day.isoformat(): amount for day, amount in history.items()},
            "existing": existing,
        }

    schedule_tool = FunctionTool(load_repayment_schedule)
    history_tool = FunctionTool(load_settlement_history)
    coverage_tool = FunctionTool(assess_repayment_coverage)

    async def schedule(
        ctx: Context, node_input: dict | None
    ) -> AsyncGenerator[Event, None]:
        call_id = str(uuid4())
        proposal_id = (node_input or {}).get("proposal_id")
        yield tool_call(schedule_tool, call_id, {})
        try:
            receipt = (
                await schedule_tool.run_async(
                    args={"proposal_id": proposal_id}, tool_context=ctx
                )
                if proposal_id
                else {}
            )
        except (ValueError, SQLAlchemyError):
            receipt = {}
        yield tool_result(
            schedule_tool, call_id, "READY" if receipt else "UNKNOWN", "RECEIPT_LOOKUP"
        )
        if not receipt:
            yield Event(
                content=reply(
                    "A confirmed simulated payment is required to view its schedule."
                ),
                actions=EventActions(
                    state_delta={"repayment_monitoring": {"status": "UNKNOWN"}}
                ),
            )
            return
        yield Event(output={"receipt": receipt, "as_of": today().isoformat()})

    async def history(
        ctx: Context, node_input: dict | None
    ) -> AsyncGenerator[Event, None]:
        if not node_input:
            return
        inputs = {"history": {}, "existing": 0}
        if node_input["receipt"]["installments_paise"]:
            call_id = str(uuid4())
            yield tool_call(history_tool, call_id, {})
            try:
                inputs = await history_tool.run_async(
                    args={"as_of": date.fromisoformat(node_input["as_of"])},
                    tool_context=ctx,
                )
            except (SQLAlchemyError, ValueError):
                pass
            yield tool_result(
                history_tool,
                call_id,
                "READY" if inputs["history"] else "UNKNOWN",
                "SETTLEMENT_LOOKUP",
            )
        yield Event(output={**node_input, **inputs})

    async def coverage(
        ctx: Context, node_input: dict | None
    ) -> AsyncGenerator[Event, None]:
        if not node_input:
            return
        call_id = str(uuid4())
        yield tool_call(coverage_tool, call_id, {})
        result = await coverage_tool.run_async(
            args={
                "receipt": SimulatedPayment.model_validate(node_input["receipt"]),
                "history": {
                    date.fromisoformat(day): amount
                    for day, amount in node_input["history"].items()
                },
                "existing": node_input["existing"],
                "as_of": date.fromisoformat(node_input["as_of"]),
                "policy_share_bps": policy_share_bps,
            },
            tool_context=ctx,
        )
        yield tool_result(coverage_tool, call_id, result["status"], "COVERAGE_ASSESSED")
        yield Event(
            content=reply(monitoring_message(result)),
            actions=EventActions(state_delta={"repayment_monitoring": result}),
            output=result,
        )

    return Workflow(
        name="repayment_monitoring_workflow",
        edges=[
            (
                "START",
                FunctionNode(func=schedule, name=schedule_tool.name),
                FunctionNode(func=history, name=history_tool.name),
                FunctionNode(func=coverage, name=coverage_tool.name),
            )
        ],
    )


def monitoring_message(result: dict) -> str:
    def money(paise: int) -> str:
        whole, remainder = divmod(paise, 100)
        return f"INR {whole:,}.{remainder:02d}"

    if result["status"] == "NO_INSTALLMENTS":
        return "This simulated payment has no financing installments."
    text = "Simulated repayment coverage is unknown."
    if result["status"] == "ON_TRACK":
        text = (
            "Projected settlement coverage is on track for the upcoming installments."
        )
    elif result["status"] == "PROJECTED_SHORTFALL":
        text = f"Projected installment shortfall is {money(result['projected_shortfall_paise'])}."
    if "next_date" in result:
        text += f" Next scheduled installment is {money(result['next_paise'])} on {result['next_date']}."
    if "upcoming_paise" in result:
        text += f" Upcoming scheduled total is {money(result['upcoming_paise'])}."
    if result.get("earlier_scheduled_paise"):
        text += f" Earlier scheduled installments total {money(result['earlier_scheduled_paise'])}."
    return text + " Actual repayment status is unknown."
