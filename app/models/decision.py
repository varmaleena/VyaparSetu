"""Payment options and advisory decisions in integer paise."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, NonNegativeInt


class FinancingOffer(BaseModel):
    version: str
    daily_rate_bps: int = Field(ge=0, le=10_000)
    fee_paise: NonNegativeInt
    tenor_days: int = Field(ge=1, le=30)


class Funding(BaseModel):
    cash: NonNegativeInt
    instant_net: NonNegativeInt = 0
    instant_fee: NonNegativeInt = 0
    offer: FinancingOffer | None = None


class PaymentOption(BaseModel):
    method: Literal["CASH", "INSTANT_SETTLEMENT", "FINANCING", "WAIT"]
    cash: NonNegativeInt = 0
    instant_net: NonNegativeInt = 0
    principal: NonNegativeInt = 0
    cost: NonNegativeInt = 0
    daily_installment: NonNegativeInt = 0
    net_savings: int = 0


class PaymentEconomics(BaseModel):
    code: str
    due_date: date | None
    discount_deadline: date | None = None
    invoice_total: int | None
    early_amount: int | None = None
    discount: int = 0
    tenor_days: int
    offer: FinancingOffer | None = None
    daily_cap: NonNegativeInt
    options: list[PaymentOption]


class PaymentDecision(BaseModel):
    status: Literal[
        "PAY_FROM_AVAILABLE_FUNDS", "FINANCING_FITS", "WAIT", "NEEDS_REVIEW"
    ]
    code: str
    economics: PaymentEconomics
    selected: PaymentOption | None = None
    simulated: bool = True
