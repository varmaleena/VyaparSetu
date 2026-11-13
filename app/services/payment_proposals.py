"""Persist and execute consent-bound proposals under a PostgreSQL row lock."""

import hashlib
import json
from datetime import UTC, date, datetime
from hmac import compare_digest
from uuid import uuid4
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Connection, Engine

from app.models.decision import PaymentDecision
from app.models.payment import PaymentConsent, PaymentProposal, SimulatedPayment
from app.services.invoice_repository import intakes
from app.services.payment_simulator import simulate_payment
from app.tools.supplier_verification import normalized_name

proposals = sa.table(
    "payment_proposals",
    *(
        sa.column(name)
        for name in (
            "id",
            "intake_id",
            "merchant_id",
            "supplier_id",
            "invoice_key",
            "account_token",
            "digest",
            "consent_at",
        )
    ),
    sa.column("terms", sa.JSON()),
    sa.column("receipt", sa.JSON(none_as_null=True)),
)


class ProposalConflict(ValueError):
    """The proposal cannot be executed with its current terms."""


def payee(connection: Connection, supplier_id: str) -> tuple[str, str, str] | None:
    row = connection.execute(
        sa.text(
            "SELECT name, payout_account_name, payout_last4, account_token "
            "FROM suppliers WHERE id=:id AND registry_status='ACTIVE' AND payout_verified "
            "FOR SHARE"
        ),
        {"id": supplier_id},
    ).one_or_none()
    if row is None or not row.name or not row.account_token or not row.payout_last4:
        return None
    if not row.payout_account_name or normalized_name(row.name) != normalized_name(
        row.payout_account_name
    ):
        return None
    return row.name, f"****{row.payout_last4}", row.account_token


class PaymentProposals:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def create(
        self,
        *,
        merchant: str,
        session: str,
        intake: str,
        supplier: str,
        masked_account: str,
        invoice_key: str,
        decision: PaymentDecision,
    ) -> tuple[PaymentProposal, str] | None:
        option = decision.selected
        economics = decision.economics
        if (
            decision.status not in {"FINANCING_FITS", "PAY_FROM_AVAILABLE_FUNDS"}
            or option is None
            or economics.early_amount is None
            or economics.discount_deadline is None
            or option.net_savings <= 0
            or option.daily_installment > economics.daily_cap
            or option.cash + option.instant_net + option.principal
            != economics.early_amount
        ):
            return None
        with self.engine.begin() as connection:
            owned = connection.execute(
                sa.text(
                    "SELECT 1 FROM invoice_intakes WHERE id=:id AND merchant_id=:merchant AND session_id=:session"
                ),
                {"id": intake, "merchant": merchant, "session": session},
            ).scalar_one_or_none()
            account = payee(connection, supplier)
            if not owned or account is None or account[1] != masked_account:
                return None
            name, masked, token = account
            proposal = PaymentProposal(
                id=str(uuid4()),
                intake_id=intake,
                supplier_id=supplier,
                supplier_name=name,
                masked_account=masked,
                amount_paise=economics.early_amount,
                deadline=economics.discount_deadline,
                tenor_days=economics.tenor_days,
                option=option,
            )
            terms = proposal.model_dump(mode="json")
            digest = hashlib.sha256(
                json.dumps(terms, sort_keys=True).encode()
            ).hexdigest()
            created = connection.execute(
                insert(proposals)
                .values(
                    id=proposal.id,
                    intake_id=intake,
                    merchant_id=merchant,
                    supplier_id=supplier,
                    invoice_key=invoice_key,
                    account_token=token,
                    terms=terms,
                    digest=digest,
                )
                .on_conflict_do_nothing()
                .returning(proposals.c.id)
            ).scalar_one_or_none()
            return (proposal, digest) if created else None

    def execute(
        self,
        merchant: str,
        proposal_id: str,
        consent: PaymentConsent,
        as_of: date,
        *,
        session: str | None = None,
    ) -> SimulatedPayment | None:
        with self.engine.begin() as connection:
            row = (
                connection.execute(
                    sa.select(proposals)
                    .where(
                        proposals.c.id == proposal_id,
                        proposals.c.merchant_id == merchant,
                    )
                    .with_for_update()
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                return None
            if (
                session is not None
                and connection.execute(
                    sa.text(
                        "SELECT 1 FROM invoice_intakes WHERE id=:id AND merchant_id=:merchant AND session_id=:session"
                    ),
                    {"id": row["intake_id"], "merchant": merchant, "session": session},
                ).scalar_one_or_none()
                is None
            ):
                return None
            if not consent.accepted or not compare_digest(
                row["digest"], consent.terms_digest
            ):
                raise ProposalConflict("Confirm the exact proposal terms.")
            if row["receipt"] is not None:
                return SimulatedPayment.model_validate(row["receipt"])
            proposal = PaymentProposal.model_validate(row["terms"])
            digest = hashlib.sha256(
                json.dumps(row["terms"], sort_keys=True).encode()
            ).hexdigest()
            if not compare_digest(digest, row["digest"]) or proposal.deadline < as_of:
                raise ProposalConflict("The proposal changed or expired.")
            account = payee(connection, proposal.supplier_id)
            if account != (
                proposal.supplier_name,
                proposal.masked_account,
                row["account_token"],
            ):
                raise ProposalConflict("The registered payee changed.")
            receipt = simulate_payment(proposal).model_copy(
                update={"scheduled_from": as_of}
            )
            connection.execute(
                proposals.update()
                .where(proposals.c.id == proposal_id)
                .values(
                    consent_at=datetime.now(UTC),
                    receipt=receipt.model_dump(mode="json"),
                )
            )
            return receipt

    def confirmed_receipt(
        self, merchant: str, session: str, proposal_id: str
    ) -> SimulatedPayment | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                sa.select(proposals.c.receipt, proposals.c.consent_at)
                .select_from(
                    proposals.join(intakes, proposals.c.intake_id == intakes.c.id)
                )
                .where(
                    proposals.c.id == proposal_id,
                    proposals.c.merchant_id == merchant,
                    intakes.c.merchant_id == merchant,
                    intakes.c.session_id == session,
                    proposals.c.consent_at.is_not(None),
                )
            ).one_or_none()
        if row is None or row.receipt is None:
            return None
        receipt = SimulatedPayment.model_validate(row.receipt)
        if receipt.scheduled_from is None:
            return receipt.model_copy(
                update={
                    "scheduled_from": row.consent_at.astimezone(
                        ZoneInfo("Asia/Kolkata")
                    ).date()
                }
            )
        return receipt
