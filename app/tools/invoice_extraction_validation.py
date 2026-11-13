"""Deterministic checks before extracted invoice facts reach downstream agents."""

from app.models.invoice import ExtractedInvoice, InvoiceUnderstandingResult


def validate_extraction(invoice: ExtractedInvoice) -> InvoiceUnderstandingResult:
    missing_price_inputs = [
        number
        for number, line in enumerate(invoice.lines, start=1)
        if not (
            line.description
            and line.unit
            and line.quantity is not None
            and line.unit_price_paise is not None
        )
    ]
    issue = extraction_issue(invoice)
    if issue:
        code, message = issue
        return InvoiceUnderstandingResult(
            status="NEEDS_CLARIFICATION",
            code=code,
            message=message,
            invoice=invoice,
            lines_missing_price_inputs=missing_price_inputs,
        )
    return InvoiceUnderstandingResult(
        status="EXTRACTED",
        code="FIELDS_VALIDATED",
        message="Invoice fields passed the intake checks.",
        invoice=invoice,
        lines_missing_price_inputs=missing_price_inputs,
    )


def extraction_issue(invoice: ExtractedInvoice) -> tuple[str, str] | None:
    if not (invoice.supplier_name and invoice.invoice_number and invoice.invoice_date):
        return (
            "MISSING_HEADER",
            "Confirm the supplier name, invoice number, and invoice date.",
        )
    if invoice.currency != "INR":
        return "CURRENCY_UNCLEAR", "Confirm that this invoice is in Indian rupees."
    if invoice.due_date is not None and invoice.due_date < invoice.invoice_date:
        return (
            "INVALID_DUE_DATE",
            "Confirm the due date. It appears earlier than the invoice date.",
        )
    if (
        not invoice.lines
        or invoice.total_paise is None
        or invoice.tax_added_paise is None
        or invoice.adjustment_paise is None
        or any(line.amount_paise is None for line in invoice.lines)
    ):
        return (
            "MISSING_AMOUNTS",
            "Confirm the line amounts, tax, adjustments, and invoice total.",
        )
    calculated_total = sum(line.amount_paise or 0 for line in invoice.lines)
    calculated_total += invoice.tax_added_paise + invoice.adjustment_paise
    if calculated_total != invoice.total_paise:
        return (
            "TOTAL_MISMATCH",
            "Confirm the invoice total. It differs from the sum of the extracted amounts.",
        )
    if invoice.discount_status == "none":
        if invoice.discount is not None:
            return (
                "DISCOUNT_UNCLEAR",
                "Confirm whether the supplier offers an early-payment discount.",
            )
        return None
    terms = invoice.discount
    if (
        invoice.discount_status == "unclear"
        or terms is None
        or (
            terms.deadline is None
            or terms.requires_full_payment is None
            or (terms.rate_bps is None and terms.amount_paise is None)
        )
    ):
        return (
            "DISCOUNT_UNCLEAR",
            "Confirm the discount amount or rate, deadline, and whether full payment is required.",
        )
    if terms.deadline < invoice.invoice_date:
        return (
            "INVALID_DISCOUNT_DATE",
            "Confirm the discount deadline. It appears earlier than the invoice date.",
        )
    if terms.amount_paise is not None and terms.amount_paise >= invoice.total_paise:
        return (
            "INVALID_DISCOUNT_AMOUNT",
            "Confirm the discount amount. It is at least as large as the invoice total.",
        )
    if terms.rate_bps is not None and terms.amount_paise is not None:
        expected = (invoice.total_paise * terms.rate_bps + 5000) // 10000
        if abs(expected - terms.amount_paise) > 1:
            return (
                "DISCOUNT_MISMATCH",
                "Confirm the discount rate and amount. They do not agree.",
            )
    return None
