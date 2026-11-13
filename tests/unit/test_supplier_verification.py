from unittest.mock import Mock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.models.supplier import SupplierRegistryRecord, SupplierVerificationInput
from app.tools.supplier_verification import gstin_checksum, verify_supplier

VALID_GSTIN = "36AAAAA0000A1Z3"


@pytest.mark.parametrize(
    ("gstin", "registry_status", "holder", "expected_status", "code"),
    [
        (
            VALID_GSTIN,
            "ACTIVE",
            "Demo Supplier",
            "VERIFIED",
            "SUPPLIER_AND_PAYEE_VERIFIED",
        ),
        (None, None, None, "NEEDS_REVIEW", "GSTIN_MISSING"),
        ("36AAAAA0000A1Z0", None, None, "NEEDS_REVIEW", "GSTIN_INVALID"),
        (VALID_GSTIN, None, None, "NEEDS_REVIEW", "SUPPLIER_UNKNOWN"),
        (VALID_GSTIN, "BLOCKED", "Demo Supplier", "BLOCKED", "SUPPLIER_BLOCKED"),
        (VALID_GSTIN, "ACTIVE", "Different Holder", "BLOCKED", "PAYOUT_NAME_MISMATCH"),
        (VALID_GSTIN, "UNVERIFIED", None, "NEEDS_REVIEW", "PAYOUT_UNVERIFIED"),
    ],
)
def test_supplier_outcomes(
    gstin, registry_status, holder, expected_status, code
) -> None:
    record = (
        SupplierRegistryRecord(
            id="supplier-id",
            name="Demo Supplier",
            gstin=VALID_GSTIN,
            registry_status=registry_status,
            payout_account_name=holder,
            payout_last4="4200",
            payout_verified=holder is not None,
        )
        if registry_status
        else None
    )
    lookup = Mock(return_value=record)
    request = SupplierVerificationInput(
        intake_id="intake-id", supplier_name="DEMO SUPPLIER", supplier_gstin=gstin
    )
    result = verify_supplier(request, lookup)
    assert (result.status, result.code) == (expected_status, code)
    assert result.masked_payout_account == (
        "****4200" if expected_status == "VERIFIED" else None
    )
    if code in {"GSTIN_MISSING", "GSTIN_INVALID"}:
        lookup.assert_not_called()
    else:
        lookup.assert_called_once_with(VALID_GSTIN)


def test_registry_failure_is_closed() -> None:
    request = SupplierVerificationInput(
        intake_id="intake-id", supplier_name="Demo Supplier", supplier_gstin=VALID_GSTIN
    )
    result = verify_supplier(request, Mock(side_effect=SQLAlchemyError()))
    assert result.status == "UNAVAILABLE"
    assert result.masked_payout_account is None


def test_checksum_matches_known_examples() -> None:
    assert gstin_checksum("27AAPFU0939F1Z") == "V"
    assert gstin_checksum(VALID_GSTIN[:-1]) == "3"
