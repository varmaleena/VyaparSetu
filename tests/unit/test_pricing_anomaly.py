from datetime import date
from decimal import Decimal

import pytest

from app.models.invoice import (
    EarlyPaymentTerms,
    ExtractedInvoice,
    InvoiceLine,
    RiskInvoiceInput,
)
from app.models.pricing import PurchaseOrderPrice
from app.tools.pricing_anomaly_check import assess_pricing


@pytest.mark.parametrize(
    ("case", "status", "code"),
    [
        ("normal", "CLEAR", "WITHIN_PURCHASE_ORDER_TOLERANCE"),
        ("overcharge", "NEEDS_REVIEW", "PRICE_ABOVE_PURCHASE_ORDER"),
        ("pack", "NOT_COMPARABLE", "INCOMPLETE_LINE_COMPARISON"),
        ("missing_unit", "NOT_COMPARABLE", "INCOMPLETE_LINE_COMPARISON"),
        ("unknown_tax_basis", "NOT_COMPARABLE", "INCOMPLETE_LINE_COMPARISON"),
        ("no_po", "NOT_COMPARABLE", "NO_COMPARABLE_PRICE"),
        ("lookup_failed", "NOT_COMPARABLE", "PRICE_REFERENCE_UNAVAILABLE"),
        ("large_discount", "NEEDS_REVIEW", "CONFIRM_DISCOUNT_TERMS"),
    ],
)
def test_pricing_check(case: str, status: str, code: str) -> None:
    amount = 22_500 if case == "overcharge" else 18_000
    invoice = ExtractedInvoice(
        supplier_name="Demo Supplier",
        supplier_gstin="36AAAAA0000A1Z3",
        purchase_order_number=None if case == "no_po" else "PO-42",
        unit_prices_exclude_tax=None if case == "unknown_tax_basis" else True,
        invoice_number="BILL-42",
        invoice_date=date(2026, 11, 12),
        due_date=None,
        currency="INR",
        lines=[
            InvoiceLine(
                description=f"Refined sunflower oil, {5 if case == 'pack' else 1} L",
                hsn="1512",
                quantity=Decimal("1"),
                unit=None if case == "missing_unit" else "pieces",
                unit_price_paise=amount,
                amount_paise=amount,
            )
        ],
        total_paise=amount + 900,
        tax_added_paise=900,
        adjustment_paise=0,
        discount_status="offered" if case == "large_discount" else "none",
        discount=EarlyPaymentTerms(
            rate_bps=600,
            amount_paise=None,
            deadline=date(2026, 11, 12),
            requires_full_payment=True,
        )
        if case == "large_discount"
        else None,
    )
    references = (
        []
        if case in {"no_po", "lookup_failed"}
        else [
            PurchaseOrderPrice(
                id="po-line",
                description="Refined sunflower oil, 1 L",
                hsn="1512",
                unit="pcs",
                unit_price_paise=18_000,
            )
        ]
    )
    result = assess_pricing(
        RiskInvoiceInput(intake_id="demo", invoice=invoice),
        references,
        price_tolerance_bps=1000,
        discount_threshold_bps=500,
        reference_unavailable=case == "lookup_failed",
    )
    assert (result.status, result.code) == (status, code)
    if case == "overcharge":
        assert result.lines[0].difference_paise == 4500
        assert result.lines[0].reference_line_id == "po-line"
    if case in {"pack", "missing_unit", "unknown_tax_basis"}:
        assert result.lines[0].reference_price_paise is None
    if case == "large_discount":
        assert result.discount_requires_confirmation
        assert result.lines[0].status == "MATCHED"
