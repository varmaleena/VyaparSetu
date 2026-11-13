"""Deterministic merchant review commands for the local Playground."""

import re
from collections.abc import AsyncGenerator, Callable
from datetime import date
from subprocess import SubprocessError

from google.adk.agents.context import Context
from google.adk.events import Event, EventActions
from google.genai import types
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from app.agents.tool_events import reply
from app.models.invoice import EarlyPaymentTerms, ExtractedInvoice
from app.models.payment import PaymentConsent, PaymentProposal
from app.services.payment_proposals import PaymentProposals, ProposalConflict
from app.services.payment_readback import payment_readback, synthesize_readback
from app.tools.pricing_anomaly_check import discount_needs_confirmation

OFFER = "confirm-offer INTAKE_ID DISCOUNT_PAISE YYYY-MM-DD"


def build_payment_review(
    proposals: PaymentProposals,
    merchant: str,
    today: Callable[[], date],
    discount_threshold_bps: int,
) -> Callable[[Context], AsyncGenerator[Event, None]]:
    async def review(ctx: Context) -> AsyncGenerator[Event, None]:
        parts = ctx.user_content.parts or [] if ctx.user_content else []
        if any(part.inline_data or part.file_data for part in parts):
            yield Event(actions=EventActions(route="invoice"))
            return
        text = " ".join(part.text or "" for part in parts).strip()
        if text.casefold().rstrip("?") in {"repayment-status", "what's due next"}:
            pending = ctx.state.get("payment_proposal") or {}
            yield Event(
                output={"proposal_id": pending.get("terms", {}).get("id")},
                actions=EventActions(route="repayment"),
            )
            return
        if text == "read-payment":
            pending = ctx.state.get("payment_proposal") or {}
            if not pending.get("terms"):
                yield Event(
                    content=reply("Review a payment proposal in this session first.")
                )
                return
            proposal = PaymentProposal.model_validate(pending["terms"])
            readback = payment_readback(proposal)
            try:
                audio = await run_in_threadpool(synthesize_readback, readback)
            except (OSError, SubprocessError, ValueError):
                yield Event(content=reply(f"{readback} Audio is unavailable."))
                return
            yield Event(
                content=types.ModelContent(
                    parts=[
                        types.Part(text=readback),
                        types.Part.from_bytes(data=audio, mime_type="audio/wav"),
                    ]
                )
            )
            return
        if match := re.fullmatch(r"confirm-payment ([0-9a-f-]{36})", text):
            pending = ctx.state.get("payment_proposal") or {}
            proposal_id = match[1]
            if pending.get("terms", {}).get("id") != proposal_id:
                yield Event(
                    content=reply("Review the payment proposal in this session first.")
                )
                return
            try:
                receipt = await run_in_threadpool(
                    proposals.execute,
                    merchant,
                    proposal_id,
                    PaymentConsent(accepted=True, terms_digest=pending["terms_digest"]),
                    today(),
                    session=ctx.session.id,
                )
            except ProposalConflict as exc:
                yield Event(content=reply(str(exc)))
                return
            except (SQLAlchemyError, ValueError):
                yield Event(
                    content=reply(
                        "Simulated payment unavailable. Retry the same command."
                    )
                )
                return
            if receipt is None:
                yield Event(content=reply("Payment proposal unavailable."))
                return
            yield Event(
                content=reply(
                    f"Simulated payment recorded. Proposal ID {receipt.proposal_id}. "
                    "Type `repayment-status` to view the schedule."
                ),
                actions=EventActions(
                    state_delta={
                        "simulated_payment_receipt": receipt.model_dump(mode="json")
                    }
                ),
            )
            return
        if match := re.fullmatch(
            r"confirm-offer ([0-9a-f-]{36}) ([0-9]{1,12}) ([0-9]{4}-[0-9]{2}-[0-9]{2})",
            text,
        ):
            intake = ctx.state.get("invoice_intake_result") or {}
            capacity = ctx.state.get("repayment_capacity") or {}
            raw_invoice = ctx.state.get("invoice_structured")
            if (
                intake.get("intake_id") != match[1]
                or not raw_invoice
                or capacity.get("status") not in {"CAPACITY_AVAILABLE", "NO_CAPACITY"}
                or capacity.get("as_of") != today().isoformat()
                or ctx.state.get("payment_proposal")
            ):
                yield Event(
                    content=reply(
                        "This offer requires a current, cleared invoice in this session."
                    )
                )
                return
            invoice = ExtractedInvoice.model_validate(raw_invoice)
            try:
                terms = EarlyPaymentTerms(
                    rate_bps=None,
                    amount_paise=int(match[2]),
                    deadline=date.fromisoformat(match[3]),
                    requires_full_payment=True,
                )
            except ValueError:
                yield Event(
                    content=reply("Enter a valid discount amount and deadline.")
                )
                return
            if (
                invoice.discount_status != "none"
                or invoice.total_paise is None
                or int(match[2]) >= invoice.total_paise
                or terms.deadline is None
                or terms.deadline < today()
                or (invoice.due_date is not None and terms.deadline > invoice.due_date)
            ):
                yield Event(
                    content=reply(
                        "The offer does not fit this invoice or payment deadline."
                    )
                )
                return
            offered = invoice.model_copy(
                update={"discount_status": "offered", "discount": terms}
            )
            if discount_needs_confirmation(offered, discount_threshold_bps):
                yield Event(
                    content=reply(
                        "This discount exceeds the configured review threshold."
                    )
                )
                return
            yield Event(
                output={
                    **capacity,
                    "confirmed_invoice": offered.model_dump(mode="json"),
                    "confirmed_offer": {
                        "intake_id": match[1],
                        "terms": terms.model_dump(mode="json"),
                        "source": "merchant_attestation",
                    },
                },
                actions=EventActions(route="offer"),
            )
            return
        yield Event(
            content=reply(
                f"Upload one invoice photo. To attest that the supplier offered a full-payment "
                f"discount separately, type `{OFFER}`. To consent to a reviewed simulation, "
                "type `confirm-payment PROPOSAL_ID`."
            )
        )

    return review
