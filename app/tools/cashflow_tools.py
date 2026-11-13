"""Deterministic settlement quantiles and fixed-installment sizing."""

from datetime import date, timedelta

from app.models.cashflow import DailyForecast, SettlementForecast

HORIZON = 10
POLICY_SHARE_BPS = 1500


def quantile(values: list[int], percent: int) -> int:
    ordered = sorted(values)
    index, fraction = divmod((len(ordered) - 1) * percent, 100)
    upper = min(index + 1, len(ordered) - 1)
    return (ordered[index] * (100 - fraction) + ordered[upper] * fraction) // 100


def forecast_settlements(
    history: dict[date, int],
    existing_edi_paise: int,
    as_of: date,
    *,
    tenor_days: int = HORIZON,
    policy_share_bps: int = POLICY_SHARE_BPS,
    stress_bps: int = 3000,
) -> SettlementForecast:
    dates = sorted(history)
    if (
        len(dates) < 56
        or dates[-1] != as_of - timedelta(days=1)
        or (dates[-1] - dates[0]).days + 1 != len(dates)
        or min(history.values()) < 0
        or existing_edi_paise < 0
    ):
        raise ValueError("Need at least 56 consecutive completed settlement days.")
    weekdays: list[list[int]] = [[] for _ in range(7)]
    for day in dates:
        weekdays[day.weekday()].append(history[day])
    amounts = [history[day] for day in dates]
    future = [as_of + timedelta(days=offset) for offset in range(tenor_days)]
    return SettlementForecast(
        days=[
            DailyForecast(
                date=day,
                p20_paise=quantile(weekdays[day.weekday()], 20),
                p50_paise=quantile(weekdays[day.weekday()], 50),
            )
            for day in future
        ],
        existing_edi_paise=existing_edi_paise,
        policy_share_bps=policy_share_bps,
        stress_bps=stress_bps,
        historical_window_minima_paise=[
            min(amounts[i : i + tenor_days])
            for i in range(len(amounts) - tenor_days + 1)
        ],
    )


def calculate_repayment_cap(forecast: SettlementForecast) -> dict:
    tightest = min(forecast.days, key=lambda day: day.p20_paise)
    historical_p20 = quantile(forecast.historical_window_minima_paise, 20)

    def room(settlement: int) -> int:
        return max(
            0,
            settlement * forecast.policy_share_bps // 10_000
            - forecast.existing_edi_paise,
        )

    weekday_cap = room(tightest.p20_paise)
    window_cap = room(historical_p20)
    final_cap = min(weekday_cap, window_cap)
    stress_cap = room(
        min(tightest.p20_paise, historical_p20)
        * (10_000 - forecast.stress_bps)
        // 10_000
    )
    return {
        "status": "CAPACITY_AVAILABLE" if final_cap else "NO_CAPACITY",
        "code": "POSITIVE_REPAYMENT_ROOM" if final_cap else "NO_REPAYMENT_ROOM",
        "tightest_forecast_date": tightest.date.isoformat(),
        "existing_edi_paise": forecast.existing_edi_paise,
        "weekday_cap_paise": weekday_cap,
        "window_cap_paise": window_cap,
        "daily_cap_paise": final_cap,
        "stress_daily_cap_paise": stress_cap,
        "policy_share_bps": forecast.policy_share_bps,
        "tenor_days": len(forecast.days),
    }
