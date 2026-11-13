"""Typed input, registry data, and result for supplier verification."""

from typing import Literal

from pydantic import BaseModel, Field


class SupplierVerificationInput(BaseModel):
    intake_id: str = Field(min_length=1, max_length=36)
    supplier_name: str = Field(min_length=1, max_length=160)
    supplier_gstin: str | None = Field(max_length=32)


class SupplierRegistryRecord(BaseModel):
    id: str
    name: str
    gstin: str
    registry_status: Literal["ACTIVE", "UNVERIFIED", "BLOCKED"]
    payout_account_name: str | None
    payout_last4: str | None
    payout_verified: bool


class SupplierVerificationResult(BaseModel):
    intake_id: str
    status: Literal["VERIFIED", "NEEDS_REVIEW", "BLOCKED", "UNAVAILABLE"]
    code: str
    message: str
    supplier_id: str | None = None
    supplier_name: str | None = None
    masked_payout_account: str | None = None
