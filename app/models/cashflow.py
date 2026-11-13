"""Settlement forecast and repayment capacity contracts."""

from datetime import date

from pydantic import BaseModel


class DailyForecast(BaseModel):
    date: date
    p20_paise: int
    p50_paise: int


class SettlementForecast(BaseModel):
    days: list[DailyForecast]
    existing_edi_paise: int
    policy_share_bps: int
    stress_bps: int
    historical_window_minima_paise: list[int]
