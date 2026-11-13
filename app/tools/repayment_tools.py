"""Assess projected installment coverage using the existing settlement model."""

from datetime import date, timedelta

from app.models.payment import SimulatedPayment
from app.tools.cashflow_tools import forecast_settlements


def assess_repayment_coverage(
    receipt: SimulatedPayment,
    history: dict[date, int],
    existing: int,
    as_of: date,
    policy_share_bps: int,
) -> dict:
    if not receipt.installments_paise:
        return {"status": "NO_INSTALLMENTS"}
    if receipt.scheduled_from is None:
        return {"status": "UNKNOWN"}
    schedule = [
        (receipt.scheduled_from + timedelta(days=offset), amount)
        for offset, amount in enumerate(receipt.installments_paise, start=1)
    ]
    upcoming = [(day, amount) for day, amount in schedule if day >= as_of]
    result = {
        "status": "UNKNOWN",
        "scheduled_paise": sum(amount for _, amount in schedule),
        "upcoming_paise": sum(amount for _, amount in upcoming),
        "earlier_scheduled_paise": sum(
            amount for day, amount in schedule if day < as_of
        ),
    }
    if not upcoming:
        return result
    next_date, next_amount = upcoming[0]
    result.update(next_date=next_date.isoformat(), next_paise=next_amount)
    if receipt.scheduled_from > as_of:
        return result
    try:
        forecast = forecast_settlements(
            history,
            existing,
            as_of,
            tenor_days=(upcoming[-1][0] - as_of).days + 1,
            policy_share_bps=policy_share_bps,
        )
    except ValueError:
        return result
    projected = {
        day.date: max(0, day.p20_paise * policy_share_bps // 10_000 - existing)
        for day in forecast.days
    }
    shortfall = sum(max(0, amount - projected[day]) for day, amount in upcoming)
    return {
        **result,
        "status": "PROJECTED_SHORTFALL" if shortfall else "ON_TRACK",
        "projected_shortfall_paise": shortfall,
    }
