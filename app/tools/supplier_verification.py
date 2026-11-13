"""Deterministic GSTIN and registered payout checks."""

import logging
import re
import unicodedata
from collections.abc import Callable
from typing import Literal

from google.adk.tools import FunctionTool
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from app.models.supplier import (
    SupplierRegistryRecord,
    SupplierVerificationInput,
    SupplierVerificationResult,
)

logger = logging.getLogger(__name__)
SupplierStatus = Literal["VERIFIED", "NEEDS_REVIEW", "BLOCKED", "UNAVAILABLE"]
BASE36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
GSTIN_FORMAT = re.compile(r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]")


def gstin_checksum(prefix: str) -> str:
    total = 0
    for index, character in enumerate(prefix):
        quotient, remainder = divmod(BASE36.index(character) * (1 + index % 2), 36)
        total += quotient + remainder
    return BASE36[-total % 36]


def is_valid_gstin(gstin: str) -> bool:
    return (
        bool(GSTIN_FORMAT.fullmatch(gstin)) and gstin_checksum(gstin[:-1]) == gstin[-1]
    )


def normalized_name(name: str) -> str:
    normalized = unicodedata.normalize("NFKC", name).casefold()
    return "".join(character for character in normalized if character.isalnum())


def verify_supplier(
    request: SupplierVerificationInput,
    lookup: Callable[[str], SupplierRegistryRecord | None],
) -> SupplierVerificationResult:
    gstin = (request.supplier_gstin or "").strip().upper()
    status: SupplierStatus
    record = None
    if not gstin:
        status, code, message = (
            "NEEDS_REVIEW",
            "GSTIN_MISSING",
            "Confirm the supplier GSTIN before choosing a payee.",
        )
    elif not is_valid_gstin(gstin):
        status, code, message = (
            "NEEDS_REVIEW",
            "GSTIN_INVALID",
            "Check the supplier GSTIN. Its format or checksum is invalid.",
        )
    else:
        try:
            record = lookup(gstin)
        except (SQLAlchemyError, ValueError):
            logger.warning(
                "supplier_registry_lookup_failed intake_id=%s", request.intake_id
            )
            status, code, message = (
                "UNAVAILABLE",
                "REGISTRY_UNAVAILABLE",
                "Supplier verification is temporarily unavailable.",
            )
        else:
            status, code, message = registry_outcome(record, request.supplier_name)

    return SupplierVerificationResult(
        intake_id=request.intake_id,
        status=status,
        code=code,
        message=message,
        supplier_id=record.id if record else None,
        supplier_name=record.name if record else None,
        masked_payout_account=f"****{record.payout_last4}"
        if status == "VERIFIED" and record
        else None,
    )


def registry_outcome(
    record: SupplierRegistryRecord | None, claimed_name: str
) -> tuple[SupplierStatus, str, str]:
    if record is None:
        return (
            "NEEDS_REVIEW",
            "SUPPLIER_UNKNOWN",
            "This supplier is missing from the verified registry.",
        )
    if record.registry_status == "BLOCKED":
        return (
            "BLOCKED",
            "SUPPLIER_BLOCKED",
            "Supplier-directed payment is blocked for this supplier.",
        )
    legal_name = normalized_name(record.name)
    if not legal_name or normalized_name(claimed_name) != legal_name:
        return (
            "NEEDS_REVIEW",
            "SUPPLIER_NAME_MISMATCH",
            "The name on the bill differs from the registered supplier name.",
        )
    if (
        record.registry_status != "ACTIVE"
        or not record.payout_verified
        or not record.payout_account_name
    ):
        return (
            "NEEDS_REVIEW",
            "PAYOUT_UNVERIFIED",
            "Confirm a verified payout account for this supplier.",
        )
    if normalized_name(record.payout_account_name) != legal_name:
        return (
            "BLOCKED",
            "PAYOUT_NAME_MISMATCH",
            "The payout account holder differs from the registered supplier.",
        )
    if not re.fullmatch(r"[0-9]{4}", record.payout_last4 or ""):
        return (
            "NEEDS_REVIEW",
            "PAYOUT_UNVERIFIED",
            "The verified payout reference is incomplete.",
        )
    return (
        "VERIFIED",
        "SUPPLIER_AND_PAYEE_VERIFIED",
        "The supplier and registered payout account passed verification.",
    )


def build_supplier_verification_tool(
    lookup: Callable[[str], SupplierRegistryRecord | None],
) -> FunctionTool:
    async def supplier_verification(
        request: SupplierVerificationInput,
    ) -> dict[str, object]:
        """Check the validated invoice supplier against the payout registry."""
        result = await run_in_threadpool(verify_supplier, request, lookup)
        return result.model_dump(mode="json")

    return FunctionTool(supplier_verification)
