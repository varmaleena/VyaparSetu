"""Typed purchase-order evidence and pricing results."""

from typing import Literal

from pydantic import BaseModel, Field


class PurchaseOrderPrice(BaseModel):
    id: str
    description: str
    hsn: str
    unit: str
    unit_price_paise: int = Field(gt=0)


class PriceLineResult(BaseModel):
    line_number: int
    description: str | None
    status: Literal["MATCHED", "PRICE_VARIANCE", "NOT_COMPARABLE"]
    code: str
    invoice_price_paise: int | None = None
    reference_price_paise: int | None = None
    difference_paise: int | None = None
    reference_line_id: str | None = None


class PricingResult(BaseModel):
    intake_id: str
    status: Literal["CLEAR", "NEEDS_REVIEW", "NOT_COMPARABLE"]
    code: str
    message: str
    purchase_order_number: str | None = None
    lines: list[PriceLineResult] = Field(default_factory=list)
    discount_requires_confirmation: bool = False
