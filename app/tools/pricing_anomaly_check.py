"""Compare like-for-like invoice and purchase-order line prices."""

import logging
from decimal import ROUND_HALF_UP
from typing import Literal, TypedDict

from google.adk.tools import FunctionTool, ToolContext
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from app.models.invoice import ExtractedInvoice, InvoiceLine, RiskInvoiceInput
from app.models.pricing import PriceLineResult, PricingResult, PurchaseOrderPrice
from app.services.purchase_order_repository import PurchaseOrderRepository
from app.tools.invoice_duplicate_check import normalized_text

logger = logging.getLogger(__name__)
UNIT_ALIASES = {
    "bag": "bags",
    "piece": "pcs",
    "pieces": "pcs",
    "pc": "pcs",
    "pack": "packs",
}


def line_key(
    description: str | None, hsn: str | None, unit: str | None
) -> tuple[str, str, str]:
    unit_key = normalized_text(unit)
    return normalized_text(description), hsn or "", UNIT_ALIASES.get(unit_key, unit_key)


class PriceLineFields(TypedDict):
    line_number: int
    description: str | None
    invoice_price_paise: int | None


def compare_line(
    line: InvoiceLine,
    number: int,
    reference_prices: list[PurchaseOrderPrice],
    *,
    tax_basis_known: bool,
    price_tolerance_bps: int,
) -> PriceLineResult:
    fields: PriceLineFields = {
        "line_number": number,
        "description": line.description,
        "invoice_price_paise": line.unit_price_paise,
    }
    key = line_key(line.description, line.hsn, line.unit)
    if (
        not all(key)
        or line.quantity is None
        or line.unit_price_paise is None
        or line.amount_paise is None
    ):
        return PriceLineResult(
            **fields, status="NOT_COMPARABLE", code="LINE_DETAILS_MISSING"
        )
    expected_amount = (line.quantity * line.unit_price_paise).to_integral_value(
        rounding=ROUND_HALF_UP
    )
    if not tax_basis_known or abs(expected_amount - line.amount_paise) > 1:
        return PriceLineResult(
            **fields, status="NOT_COMPARABLE", code="UNIT_PRICE_BASIS_UNCLEAR"
        )
    matching = [
        reference
        for reference in reference_prices
        if line_key(reference.description, reference.hsn, reference.unit) == key
    ]
    if len(matching) != 1:
        code = "REFERENCE_AMBIGUOUS" if matching else "NO_MATCHING_PO_LINE"
        return PriceLineResult(**fields, status="NOT_COMPARABLE", code=code)

    reference = matching[0]
    difference = line.unit_price_paise - reference.unit_price_paise
    exceeds = difference * 10_000 > reference.unit_price_paise * price_tolerance_bps
    return PriceLineResult(
        **fields,
        status="PRICE_VARIANCE" if exceeds else "MATCHED",
        code="PRICE_ABOVE_TOLERANCE" if exceeds else "PRICE_WITHIN_TOLERANCE",
        reference_price_paise=reference.unit_price_paise,
        difference_paise=difference,
        reference_line_id=reference.id,
    )


def discount_needs_confirmation(invoice: ExtractedInvoice, threshold_bps: int) -> bool:
    terms = invoice.discount
    if invoice.discount_status != "offered" or terms is None:
        return False
    if terms.rate_bps is not None:
        return terms.rate_bps > threshold_bps
    return bool(
        terms.amount_paise is not None
        and invoice.total_paise is not None
        and terms.amount_paise * 10_000 > invoice.total_paise * threshold_bps
    )


def assess_pricing(
    request: RiskInvoiceInput,
    references: list[PurchaseOrderPrice],
    *,
    price_tolerance_bps: int,
    discount_threshold_bps: int,
    reference_unavailable: bool = False,
) -> PricingResult:
    invoice = request.invoice
    po = invoice.purchase_order_number
    discount_review = discount_needs_confirmation(invoice, discount_threshold_bps)
    lines = (
        [
            compare_line(
                line,
                number,
                references,
                tax_basis_known=invoice.unit_prices_exclude_tax is True,
                price_tolerance_bps=price_tolerance_bps,
            )
            for number, line in enumerate(invoice.lines, 1)
        ]
        if references
        else []
    )
    flagged = [line for line in lines if line.status == "PRICE_VARIANCE"]
    status: Literal["CLEAR", "NEEDS_REVIEW", "NOT_COMPARABLE"]
    if flagged:
        status, code = "NEEDS_REVIEW", "PRICE_ABOVE_PURCHASE_ORDER"
        message = "A unit price exceeds the purchase-order tolerance."
    elif discount_review:
        status, code = "NEEDS_REVIEW", "CONFIRM_DISCOUNT_TERMS"
        message = (
            "Confirm the unusually large early-payment discount with the supplier."
        )
    elif reference_unavailable:
        status, code = "NOT_COMPARABLE", "PRICE_REFERENCE_UNAVAILABLE"
        message = "Purchase-order price lookup is unavailable."
    elif not references:
        status, code = "NOT_COMPARABLE", "NO_COMPARABLE_PRICE"
        message = "No comparable price on file."
    elif not lines or any(line.status == "NOT_COMPARABLE" for line in lines):
        status, code = "NOT_COMPARABLE", "INCOMPLETE_LINE_COMPARISON"
        message = "Some invoice lines could not be compared with this purchase order."
    else:
        status, code = "CLEAR", "WITHIN_PURCHASE_ORDER_TOLERANCE"
        message = "Invoice unit prices are within the purchase-order tolerance."
    return PricingResult(
        intake_id=request.intake_id,
        status=status,
        code=code,
        message=message,
        purchase_order_number=po,
        lines=lines,
        discount_requires_confirmation=discount_review,
    )


def build_pricing_anomaly_tool(
    repository: PurchaseOrderRepository,
    *,
    demo_merchant: str | None = None,
    price_tolerance_bps: int,
    discount_threshold_bps: int,
) -> FunctionTool:
    async def pricing_anomaly_check(
        request: RiskInvoiceInput,
        tool_context: ToolContext,
    ) -> dict[str, object]:
        """Compare invoice lines with a merchant's referenced purchase order."""
        invoice = request.invoice
        gstin = (invoice.supplier_gstin or "").strip().upper()
        po = (invoice.purchase_order_number or "").strip().upper()
        references = []
        lookup_failed = False
        if gstin and po:
            try:
                references = await run_in_threadpool(
                    repository.find_prices,
                    demo_merchant or tool_context.session.user_id,
                    gstin,
                    po,
                )
            except (SQLAlchemyError, ValueError):
                logger.warning(
                    "purchase_order_lookup_failed intake_id=%s", request.intake_id
                )
                lookup_failed = True
        return assess_pricing(
            request,
            references,
            price_tolerance_bps=price_tolerance_bps,
            discount_threshold_bps=discount_threshold_bps,
            reference_unavailable=lookup_failed,
        ).model_dump(mode="json")

    return FunctionTool(pricing_anomaly_check)
