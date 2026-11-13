"""Duplicate fingerprint regression checks."""

from datetime import date
from decimal import Decimal

from app.models.invoice import ExtractedInvoice, InvoiceLine
from app.tools.invoice_duplicate_check import invoice_fingerprint


def test_fingerprint_normalizes_lines_and_keeps_supplier_scope() -> None:
    invoice = ExtractedInvoice(
        supplier_name="Demo Supplier",
        supplier_gstin="36AAAAA0000A1Z3",
        invoice_number="BILL-001",
        invoice_date=date(2026, 11, 12),
        due_date=None,
        currency="INR",
        lines=[
            InvoiceLine(
                description="Rice bag",
                quantity=Decimal("40"),
                unit="bag",
                amount_paise=400_000,
            ),
            InvoiceLine(description="Oil tin", amount_paise=200_000),
        ],
        total_paise=600_000,
        tax_added_paise=0,
        adjustment_paise=0,
        discount_status="none",
        discount=None,
    )
    duplicate = invoice.model_copy(deep=True)
    duplicate.lines[0].description = " RICE   BAG "
    duplicate.lines[0].quantity = Decimal("40.00")
    duplicate.lines[0].unit = "Bag"
    duplicate.lines.reverse()
    expected = invoice_fingerprint(invoice, "36AAAAA0000A1Z3", "BILL-001")
    assert invoice_fingerprint(duplicate, "36AAAAA0000A1Z3", "BILL-001") == expected
    assert invoice_fingerprint(duplicate, "36AAAAA0001A1Z2", "BILL-001") != expected
    assert invoice_fingerprint(duplicate, "36AAAAA0000A1Z3", "BILL-002") != expected
