"""Contracts for duplicate-invoice screening."""

from typing import Literal

from pydantic import BaseModel


class DuplicateCheckResult(BaseModel):
    intake_id: str
    status: Literal["CLEAR", "EXACT_DUPLICATE", "NEEDS_REVIEW"]
    code: str
    message: str
    matched_intake_id: str | None = None
    matched_invoice_id: str | None = None
