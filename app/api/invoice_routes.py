"""HTTP entry points for authenticated invoice intake."""

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from starlette.concurrency import run_in_threadpool

from app.agents.intake_runner import IntakeRunner
from app.api.intake_auth import get_intake_merchant
from app.config.settings import get_settings
from app.models.invoice import MAX_INVOICE_BYTES, InvoiceIntakeResult
from app.services.invoice_intake import create_invoice_intake

router = APIRouter(prefix="/invoice-intake", tags=["invoice intake"])
Merchant = Annotated[str, Depends(get_intake_merchant)]


@lru_cache
def get_intake_runner() -> IntakeRunner:
    return IntakeRunner(create_invoice_intake(get_settings()))


RunnerDependency = Annotated[IntakeRunner, Depends(get_intake_runner)]


@router.post("/sessions", status_code=201)
async def create_intake_session(
    merchant: Merchant, runner: RunnerDependency
) -> dict[str, str]:
    if not await run_in_threadpool(runner.repository.merchant_exists, merchant):
        raise HTTPException(404, "Merchant not found.")
    session = await runner.create_session(merchant)
    return {"session_id": session.id}


@router.post("/sessions/{session_id}/image", status_code=201)
async def upload_invoice_image(
    session_id: str,
    request: Request,
    response: Response,
    merchant: Merchant,
    runner: RunnerDependency,
) -> InvoiceIntakeResult:
    if await runner.get_session(merchant, session_id) is None:
        raise HTTPException(404, "Intake session not found.")
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk[: MAX_INVOICE_BYTES + 1 - len(content)])
        if len(content) > MAX_INVOICE_BYTES:
            break
    result = await runner.run(merchant, session_id, bytes(content))
    if result.status == "UNAVAILABLE":
        response.status_code = 503
    elif result.status == "RETRY_CAPTURE":
        response.status_code = 413 if result.code == "FILE_TOO_LARGE" else 422
    return result
