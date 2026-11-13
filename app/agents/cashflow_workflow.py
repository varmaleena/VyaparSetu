"""Run settlement forecasting and repayment sizing after risk checks."""

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
from app.models.cashflow import SettlementForecast
from app.services.payment_options_repository import PaymentOptionsRepository
from app.services.settlement_repository import SettlementRepository
from app.tools.cashflow_tools import HORIZON
from app.tools.cashflow_tools import calculate_repayment_cap as size_cap
from app.tools.cashflow_tools import forecast_settlements as forecast_history


def build_cashflow_workflow(
    repository: SettlementRepository,
    *,
    as_of: date | Callable[[], date],
    demo_merchant: str | None = None,
    funding_repository: PaymentOptionsRepository | None = None,
    policy_share_bps: int = 1500,
    stress_bps: int = 3000,
) -> Workflow:
    async def forecast_settlements(tool_context: ToolContext) -> dict:
        """Load settlement history and estimate weekday quantiles."""
        evaluation_date = as_of() if callable(as_of) else as_of
        history, existing = await run_in_threadpool(
            repository.history,
            demo_merchant or tool_context.session.user_id,
            evaluation_date,
        )
        funding = (
            await run_in_threadpool(
                funding_repository.get,
                demo_merchant or tool_context.session.user_id,
                evaluation_date,
            )
            if funding_repository
            else None
        )
        forecast = forecast_history(
            history,
            existing,
            evaluation_date,
            tenor_days=funding.offer.tenor_days
            if funding and funding.offer
            else HORIZON,
            policy_share_bps=policy_share_bps,
            stress_bps=stress_bps,
        )
        return forecast.model_dump(mode="json")

    def calculate_repayment_cap(forecast: SettlementForecast) -> dict:
        """Apply the daily and historical-window repayment limits."""
        return size_cap(forecast)

    forecast_tool = FunctionTool(forecast_settlements)
    sizing_tool = FunctionTool(calculate_repayment_cap)

    async def forecast_settlements_step(
        ctx: Context, node_input: dict | None
    ) -> AsyncGenerator[Event, None]:
        checks = node_input or {}
        supplier = checks.get("supplier_verification") or {}
        duplicate = checks.get("duplicate_invoice_check") or {}
        pricing = checks.get("pricing_anomaly_check") or {}
        if (
            supplier.get("status") != "VERIFIED"
            or duplicate.get("status") != "CLEAR"
            or pricing.get("status") not in {"CLEAR", "NOT_COMPARABLE"}
        ):
            return
        call_id = str(uuid4())
        yield tool_call(forecast_tool, call_id, {})
        try:
            forecast = SettlementForecast.model_validate(
                await forecast_tool.run_async(args={}, tool_context=ctx)
            )
        except (SQLAlchemyError, ValueError):
            yield tool_result(
                forecast_tool, call_id, "NEEDS_REVIEW", "SETTLEMENT_HISTORY_UNAVAILABLE"
            )
            yield Event(
                content=reply(
                    "Settlement history needs review before sizing repayment."
                ),
                actions=EventActions(
                    state_delta={
                        "repayment_capacity": {
                            "status": "NEEDS_REVIEW",
                            "code": "SETTLEMENT_HISTORY_UNAVAILABLE",
                        }
                    }
                ),
            )
            return
        yield tool_result(forecast_tool, call_id, "READY", "FORECAST_READY")
        payload = forecast.model_dump(
            mode="json", exclude={"historical_window_minima_paise"}
        )
        yield Event(
            output=forecast.model_dump(mode="json"),
            actions=EventActions(
                route="forecast_ready", state_delta={"cashflow_forecast": payload}
            ),
        )

    async def calculate_repayment_cap_step(
        ctx: Context, node_input: SettlementForecast
    ) -> AsyncGenerator[Event, None]:
        call_id = str(uuid4())
        yield tool_call(sizing_tool, call_id, {})
        result = await sizing_tool.run_async(
            args={"forecast": node_input.model_dump(mode="json")}, tool_context=ctx
        )
        result["as_of"] = node_input.days[0].date.isoformat()
        yield tool_result(sizing_tool, call_id, result["status"], result["code"])
        cap = result["daily_cap_paise"] / 100
        stress = result["stress_daily_cap_paise"] / 100
        yield Event(
            output=result,
            content=reply(
                f"Daily repayment room: INR {cap:,.2f}. "
                f"With {node_input.stress_bps / 100:g}% lower settlements: INR {stress:,.2f}."
            ),
            actions=EventActions(state_delta={"repayment_capacity": result}),
        )

    forecast = FunctionNode(func=forecast_settlements_step, name="forecast_settlements")
    sizing = FunctionNode(
        func=calculate_repayment_cap_step, name="calculate_repayment_cap"
    )
    return Workflow(
        name="cashflow_workflow",
        edges=[("START", forecast), (forecast, {"forecast_ready": sizing})],
    )
