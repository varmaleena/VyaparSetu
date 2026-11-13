"""Immutable terms and consent requests for simulated payments."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, PositiveInt

from app.models.decision import PaymentOption


class PaymentProposal(BaseModel):
    id: str
    intake_id: str
    supplier_id: str
    supplier_name: str
    masked_account: str
    amount_paise: PositiveInt
    deadline: date
    tenor_days: int
    option: PaymentOption
    simulated: Literal[True] = True


class PaymentConsent(BaseModel):
    terms_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    accepted: Literal[True]


class SimulatedPayment(BaseModel):
    proposal_id: str
    status: Literal["SIMULATED_PAID"]
    installments_paise: list[int]
