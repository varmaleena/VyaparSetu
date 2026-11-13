"""Typed inputs and results for invoice image intake."""

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, WithJsonSchema

MAX_INVOICE_BYTES = 10 * 1024 * 1024


class IntakeContext(BaseModel):
    merchant_id: str = Field(min_length=1, max_length=36)
    session_id: str = Field(min_length=1, max_length=160)


class InvoiceImage(BaseModel):
    content: bytes
    media_type: str
    width: int
    height: int
    sha256: str


class InvoiceIntakeResult(BaseModel):
    status: Literal["ACCEPTED", "RETRY_CAPTURE", "UNAVAILABLE"]
    code: str
    message: str
    intake_id: str | None = None
    invoice_image_ref: str | None = None


class ExtractionFields(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InvoiceLine(ExtractionFields):
    description: str | None = Field(max_length=200)
    hsn: str | None = Field(default=None, pattern=r"^[0-9]{4,8}$")
    quantity: Annotated[Decimal, WithJsonSchema({"type": "string"})] | None = Field(
        default=None, gt=0, max_digits=12, decimal_places=4
    )
    unit: str | None = Field(default=None, min_length=1, max_length=40)
    unit_price_paise: int | None = Field(default=None, ge=0, le=999_999_999_999)
    amount_paise: int | None = Field(ge=0, le=999_999_999_999)


class EarlyPaymentTerms(ExtractionFields):
    rate_bps: int | None = Field(ge=1, le=9_999)
    amount_paise: int | None = Field(ge=1, le=999_999_999_999)
    deadline: date | None
    requires_full_payment: bool | None


class ExtractedInvoice(ExtractionFields):
    supplier_name: str | None = Field(max_length=160)
    supplier_gstin: str | None = Field(max_length=32)
    purchase_order_number: str | None = Field(default=None, max_length=80)
    unit_prices_exclude_tax: bool | None = None
    invoice_number: str | None = Field(max_length=160)
    invoice_date: date | None
    due_date: date | None
    currency: Literal["INR", "OTHER"] | None
    lines: list[InvoiceLine] = Field(max_length=100)
    total_paise: int | None = Field(ge=1, le=999_999_999_999)
    tax_added_paise: int | None = Field(ge=0, le=999_999_999_999)
    adjustment_paise: int | None = Field(ge=-999_999_999_999, le=999_999_999_999)
    discount_status: Literal["offered", "none", "unclear"]
    discount: EarlyPaymentTerms | None


class InvoiceUnderstandingResult(BaseModel):
    status: Literal["EXTRACTED", "NEEDS_CLARIFICATION", "UNAVAILABLE"]
    code: str
    message: str
    invoice: ExtractedInvoice | None = None
    lines_missing_price_inputs: list[int] = Field(default_factory=list)


class RiskInvoiceInput(BaseModel):
    intake_id: str = Field(min_length=1, max_length=36)
    invoice: ExtractedInvoice
