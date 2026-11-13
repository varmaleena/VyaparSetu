"""Serialize duplicate screening and persist decisions in PostgreSQL."""

from datetime import date

import sqlalchemy as sa
from sqlalchemy.engine import Connection, Engine

from app.models.invoice import IntakeContext
from app.models.invoice_duplicate import DuplicateCheckResult
from app.services.invoice_repository import intakes
from app.services.supplier_repository import suppliers

checks = sa.table(
    "invoice_duplicate_checks",
    *(
        sa.column(name)
        for name in (
            "intake_id",
            "merchant_id",
            "supplier_gstin",
            "invoice_number",
            "invoice_date",
            "total_paise",
            "fingerprint",
            "image_sha256",
            "created_at",
        )
    ),
    sa.column("result", sa.JSON()),
)
invoices = sa.table(
    "invoices",
    sa.column("id"),
    sa.column("merchant_id"),
    sa.column("supplier_id"),
    sa.column("invoice_number"),
)


class InvoiceDuplicateRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def check(
        self,
        context: IntakeContext,
        *,
        intake_id: str,
        gstin: str,
        invoice_number: str,
        invoice_date: date,
        total_paise: int,
        fingerprint: str,
    ) -> DuplicateCheckResult:
        with self.engine.begin() as conn:
            conn.execute(
                sa.select(
                    sa.func.pg_advisory_xact_lock(
                        sa.func.hashtextextended(
                            f"invoice-duplicate:{context.merchant_id}:{gstin}", 0
                        )
                    )
                )
            )
            image_hash = conn.scalar(
                sa.select(intakes.c.sha256).where(
                    intakes.c.id == intake_id,
                    intakes.c.merchant_id == context.merchant_id,
                    intakes.c.session_id == context.session_id,
                )
            )
            if image_hash is None:
                return DuplicateCheckResult(
                    intake_id=intake_id,
                    status="NEEDS_REVIEW",
                    code="INTAKE_NOT_FOUND",
                    message="The saved invoice is unavailable. Re-upload it before continuing.",
                )

            previous = conn.scalar(
                sa.select(checks.c.result).where(checks.c.intake_id == intake_id)
            )
            if previous is not None:
                return DuplicateCheckResult.model_validate(previous)

            scope = (
                checks.c.merchant_id == context.merchant_id,
                checks.c.supplier_gstin == gstin,
            )
            result = find_match(
                conn,
                intake_id=intake_id,
                scope=scope,
                invoice_number=invoice_number,
                invoice_date=invoice_date,
                total_paise=total_paise,
                fingerprint=fingerprint,
                image_hash=image_hash,
                merchant_id=context.merchant_id,
                gstin=gstin,
            )
            conn.execute(
                checks.insert().values(
                    intake_id=intake_id,
                    merchant_id=context.merchant_id,
                    supplier_gstin=gstin,
                    invoice_number=invoice_number,
                    invoice_date=invoice_date,
                    total_paise=total_paise,
                    fingerprint=fingerprint,
                    image_sha256=image_hash,
                    result=result.model_dump(mode="json"),
                )
            )
            return result


def find_match(
    conn: Connection,
    *,
    intake_id: str,
    scope: tuple,
    invoice_number: str,
    invoice_date: date,
    total_paise: int,
    fingerprint: str,
    image_hash: str,
    merchant_id: str,
    gstin: str,
) -> DuplicateCheckResult:
    candidates = (
        sa.select(checks.c.intake_id)
        .where(*scope)
        .order_by(checks.c.created_at, checks.c.intake_id)
        .limit(1)
    )
    exact = conn.scalar(
        candidates.where(
            sa.or_(
                checks.c.fingerprint == fingerprint,
                checks.c.image_sha256 == image_hash,
            )
        )
    )
    if exact:
        return DuplicateCheckResult(
            intake_id=intake_id,
            status="EXACT_DUPLICATE",
            code="INVOICE_ALREADY_SUBMITTED",
            message="This bill matches a previous submission. A second financing attempt is blocked.",
            matched_intake_id=exact,
        )
    tolerance = total_paise // 100
    near = conn.scalar(
        candidates.where(
            checks.c.invoice_date == invoice_date,
            sa.or_(
                checks.c.invoice_number == invoice_number,
                checks.c.total_paise.between(
                    total_paise - tolerance, total_paise + tolerance
                ),
            ),
        )
    )
    if near:
        return DuplicateCheckResult(
            intake_id=intake_id,
            status="NEEDS_REVIEW",
            code="SIMILAR_INVOICE_FOUND",
            message="A prior bill from this supplier has a similar number or amount. Confirm that this is a separate bill.",
            matched_intake_id=near,
        )
    historical = conn.scalar(
        sa.select(invoices.c.id)
        .select_from(invoices.join(suppliers, invoices.c.supplier_id == suppliers.c.id))
        .where(
            invoices.c.merchant_id == merchant_id,
            suppliers.c.gstin == gstin,
            sa.func.upper(sa.func.btrim(invoices.c.invoice_number)) == invoice_number,
        )
        .order_by(invoices.c.id)
        .limit(1)
    )
    if historical:
        return DuplicateCheckResult(
            intake_id=intake_id,
            status="NEEDS_REVIEW",
            code="INVOICE_NUMBER_ALREADY_RECORDED",
            message="This invoice number already exists in the ledger. Confirm the earlier record before proceeding.",
            matched_invoice_id=historical,
        )
    return DuplicateCheckResult(
        intake_id=intake_id,
        status="CLEAR",
        code="NO_DUPLICATE_FOUND",
        message="No matching invoice was found in the checked records.",
    )
