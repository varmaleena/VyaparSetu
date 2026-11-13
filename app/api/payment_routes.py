"""Authenticated confirmation for the simulated payment rail."""

from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from app.api.intake_auth import get_intake_merchant
from app.config.settings import get_settings
from app.models.payment import PaymentConsent, SimulatedPayment
from app.services.database_service import create_database_engine
from app.services.payment_proposals import PaymentProposals, ProposalConflict

router = APIRouter(prefix="/simulated-payments", tags=["simulated payments"])


@router.post("/{proposal_id}/confirm")
async def confirm_payment(
    proposal_id: str,
    consent: PaymentConsent,
    merchant: Annotated[str, Depends(get_intake_merchant)],
) -> SimulatedPayment:
    settings = get_settings()
    as_of = settings.scenario_date or datetime.now(ZoneInfo("Asia/Kolkata")).date()
    engine = create_database_engine()
    try:
        receipt = await run_in_threadpool(
            PaymentProposals(engine).execute, merchant, proposal_id, consent, as_of
        )
    except ProposalConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except (SQLAlchemyError, ValueError) as exc:
        raise HTTPException(503, "Simulated payment unavailable.") from exc
    finally:
        engine.dispose()
    if receipt is None:
        raise HTTPException(404, "Payment proposal not found.")
    return receipt
