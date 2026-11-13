"""Compare payment options after validated invoice and cash-flow results."""

from collections.abc import AsyncGenerator
from datetime import date
from uuid import uuid4

from google.adk.agents.context import Context
from google.adk.events import Event, EventActions
from google.adk.tools import FunctionTool, ToolContext
from google.adk.workflow import Workflow
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from app.agents.tool_events import reply, tool_call, tool_result
from app.models.decision import Funding, PaymentDecision, PaymentEconomics
from app.services.payment_options_repository import PaymentOptionsRepository
from app.tools.payment_decision_tools import (
    apply_payment_policy,
    calculate_payment_economics,
)


def build_payment_decision_workflow(
    repository: PaymentOptionsRepository,
    *,
    as_of: date,
    demo_merchant: str,
) -> Workflow:
    async def get_payment_options(
        evaluation_date: str, tool_context: ToolContext
    ) -> dict:
        """Load synthetic funding availability for the configured merchant."""
        return {
            "funding": await run_in_threadpool(
                repository.get, demo_merchant, date.fromisoformat(evaluation_date)
            )
        }

    options = FunctionTool(get_payment_options)
    economics = FunctionTool(calculate_payment_economics)
    policy = FunctionTool(apply_payment_policy)

    async def get_payment_options_step(
        ctx: Context, node_input: dict | None
    ) -> AsyncGenerator[Event, None]:
        if not node_input or node_input.get("status") not in {
            "CAPACITY_AVAILABLE",
            "NO_CAPACITY",
        }:
            return
        invoice = ctx.state.get("invoice_structured")
        if not invoice:
            return
        call_id = str(uuid4())
        yield tool_call(options, call_id, {})
        evaluation_date = node_input.get("as_of", as_of.isoformat())
        try:
            funding = (
                await options.run_async(
                    args={"evaluation_date": evaluation_date}, tool_context=ctx
                )
            )["funding"]
        except (SQLAlchemyError, ValueError):
            funding = None
        if funding is None:
            yield tool_result(options, call_id, "NEEDS_REVIEW", "FUNDING_UNAVAILABLE")
            yield Event(
                content=reply("Available funds could not be verified."),
                actions=EventActions(
                    state_delta={
                        "payment_decision": {
                            "status": "NEEDS_REVIEW",
                            "code": "FUNDING_UNAVAILABLE",
                            "simulated": True,
                        }
                    }
                ),
            )
            return
        funding = Funding.model_validate(funding)
        if funding.offer and funding.offer.tenor_days != node_input.get("tenor_days"):
            funding = funding.model_copy(update={"offer": None})
        yield tool_result(options, call_id, "READY", "FUNDING_LOADED")
        yield Event(
            output={
                "invoice": invoice,
                "as_of": evaluation_date,
                "funding": Funding.model_validate(funding).model_dump(),
                "daily_cap": node_input["daily_cap_paise"],
            }
        )

    async def calculate_payment_economics_step(
        ctx: Context, node_input: dict | None
    ) -> AsyncGenerator[Event, None]:
        if node_input is None:
            return
        call_id = str(uuid4())
        yield tool_call(economics, call_id, {})
        result = await economics.run_async(
            args={**node_input, "as_of": date.fromisoformat(node_input["as_of"])},
            tool_context=ctx,
        )
        value = PaymentEconomics.model_validate(result)
        yield tool_result(economics, call_id, "COMPARED", value.code)
        yield Event(output=value.model_dump(mode="json"))

    async def apply_payment_policy_step(
        ctx: Context, node_input: PaymentEconomics | None
    ) -> AsyncGenerator[Event, None]:
        if node_input is None:
            return
        call_id = str(uuid4())
        yield tool_call(policy, call_id, {})
        result = PaymentDecision.model_validate(
            await policy.run_async(
                args={"economics": node_input.model_dump(mode="json")}, tool_context=ctx
            )
        )
        yield tool_result(policy, call_id, result.status, result.code)
        payload = result.model_dump(mode="json")
        yield Event(
            content=reply(decision_message(result)),
            output=payload,
            actions=EventActions(state_delta={"payment_decision": payload}),
        )

    from google.adk.workflow import FunctionNode

    return Workflow(
        name="payment_decision_workflow",
        edges=[
            (
                "START",
                FunctionNode(func=get_payment_options_step, name=options.name),
                FunctionNode(
                    func=calculate_payment_economics_step, name=economics.name
                ),
                FunctionNode(func=apply_payment_policy_step, name=policy.name),
            )
        ],
    )


def decision_message(decision: PaymentDecision) -> str:
    def money(paise: int) -> str:
        return f"INR {paise / 100:,.2f}"

    economics = decision.economics
    message = f"Payment comparison (simulation): {decision.status} ({decision.code})."
    if economics.early_amount is not None and economics.code != "DISCOUNT_EXPIRED":
        message += (
            f" Pay {money(economics.early_amount)} by {economics.discount_deadline}"
            f" to save {money(economics.discount)} before costs."
        )
    if option := decision.selected:
        message += (
            f" Cash {money(option.cash)}, instant-settlement funds {money(option.instant_net)},"
            f" financing {money(option.principal)}, total cost {money(option.cost)},"
            f" estimated net savings {money(option.net_savings)}."
        )
        if option.principal and economics.offer:
            message += f" Financing terms: {economics.offer.version}."
            message += f" Repay up to {money(option.daily_installment)} per day for {economics.tenor_days} days."
    elif decision.status == "WAIT" and economics.due_date:
        message += f" Plan to pay by the normal due date, {economics.due_date}."
    return message
