"""Normalize invoice fields and expose duplicate screening as an ADK tool."""

import hashlib
import json
import logging
import unicodedata

from google.adk.tools import FunctionTool, ToolContext
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from app.models.invoice import ExtractedInvoice, IntakeContext, RiskInvoiceInput
from app.models.invoice_duplicate import DuplicateCheckResult
from app.services.invoice_duplicate_repository import InvoiceDuplicateRepository
from app.tools.supplier_verification import is_valid_gstin

logger = logging.getLogger(__name__)


def normalized_text(value: str | None) -> str:
    return " ".join(unicodedata.normalize("NFKC", value or "").casefold().split())


def invoice_fingerprint(invoice: ExtractedInvoice, gstin: str, number: str) -> str:
    lines = sorted(
        json.dumps(
            [
                normalized_text(line.description),
                line.hsn,
                str(line.quantity.normalize()) if line.quantity is not None else None,
                normalized_text(line.unit),
                line.unit_price_paise,
                line.amount_paise,
            ],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        for line in invoice.lines
    )
    payload = [gstin, number, str(invoice.invoice_date), invoice.total_paise, lines]
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def build_duplicate_invoice_tool(
    repository: InvoiceDuplicateRepository,
    *,
    demo_merchant: str | None = None,
) -> FunctionTool:
    async def duplicate_invoice_check(
        request: RiskInvoiceInput, tool_context: ToolContext
    ) -> dict[str, object]:
        """Check the validated bill for exact and near matches in merchant records."""
        invoice = request.invoice
        gstin = (invoice.supplier_gstin or "").strip().upper()
        number = (
            unicodedata.normalize("NFKC", invoice.invoice_number or "").strip().upper()
        )
        if (
            not is_valid_gstin(gstin)
            or not number
            or invoice.invoice_date is None
            or invoice.total_paise is None
        ):
            result = DuplicateCheckResult(
                intake_id=request.intake_id,
                status="NEEDS_REVIEW",
                code="DUPLICATE_INPUT_INCOMPLETE",
                message="Confirm the supplier GSTIN and invoice details before checking for duplicates.",
            )
        else:
            session = tool_context.session
            context = IntakeContext(
                merchant_id=demo_merchant or session.user_id,
                session_id=session.id,
            )
            try:
                result = await run_in_threadpool(
                    repository.check,
                    context,
                    intake_id=request.intake_id,
                    gstin=gstin,
                    invoice_number=number,
                    invoice_date=invoice.invoice_date,
                    total_paise=invoice.total_paise,
                    fingerprint=invoice_fingerprint(invoice, gstin, number),
                )
            except (SQLAlchemyError, ValueError):
                logger.warning("duplicate_check_failed intake_id=%s", request.intake_id)
                result = DuplicateCheckResult(
                    intake_id=request.intake_id,
                    status="NEEDS_REVIEW",
                    code="DUPLICATE_CHECK_UNAVAILABLE",
                    message="Duplicate screening is unavailable. Review this invoice before proceeding.",
                )
        return result.model_dump(mode="json")

    return FunctionTool(duplicate_invoice_check)
