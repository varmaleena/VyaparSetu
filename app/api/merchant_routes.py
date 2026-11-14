"""Authenticated merchant demo routes using the same ADK graph as Playground."""

import re
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse
from google.adk.apps import App
from google.adk.runners import Runner
from google.genai import types
from pydantic import BaseModel, Field

from app.agents.merchant_workflow import build_merchant_workflow
from app.api.merchant_surfaces import present
from app.app_utils.services import get_session_service
from app.config.settings import get_settings
from app.models.invoice import MAX_INVOICE_BYTES

router = APIRouter(prefix="/merchant")
ASSETS = Path(__file__).resolve().parents[1] / "merchant_ui"
APP_NAME = "merchant_ui"


def merchant_access(request: Request) -> str:
    settings = get_settings()
    if settings.invoice_playground_enabled:
        return settings.invoice_demo_merchant_id
    host = request.headers.get("host", "")
    if (
        request.client is not None
        and request.client.host in {"127.0.0.1", "::1", "localhost"}
    ):
        return settings.invoice_demo_merchant_id
    raise HTTPException(403, "Open the configured local merchant demo.")


Merchant = Annotated[str, Depends(merchant_access)]


@router.get("/", include_in_schema=False)
def merchant_page() -> FileResponse:
    return FileResponse(
        ASSETS / "index.html",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@router.get("/assets/{asset}", include_in_schema=False)
def asset_file(asset: Literal["app.js", "style.css"]) -> FileResponse:
    return FileResponse(
        ASSETS / asset,
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@lru_cache
def get_runner() -> Runner:
    return Runner(
        app=App(
            name=APP_NAME,
            root_agent=build_merchant_workflow(get_settings(), show_json=False),
        ),
        session_service=get_session_service(),
    )


@router.post("/runs", status_code=201)
async def start_run(merchant: Merchant) -> dict[str, str]:
    session = await get_runner().session_service.create_session(
        app_name=APP_NAME, user_id=merchant
    )
    return {"id": session.id}


async def run_state(merchant: str, run_id: str) -> dict:
    session = await get_runner().session_service.get_session(
        app_name=APP_NAME,
        user_id=merchant,
        session_id=run_id,
    )
    if session is None:
        raise HTTPException(404, "Run not found.")
    return session.state


@router.get("/runs/{run_id}")
async def get_run(run_id: UUID, merchant: Merchant, response: Response) -> dict:
    response.headers["Cache-Control"] = "no-store"
    return present(await run_state(merchant, str(run_id)))


@router.get("/runs/{run_id}/operations")
async def operations(run_id: UUID, merchant: Merchant, response: Response) -> dict:
    session = await get_runner().session_service.get_session(
        app_name=APP_NAME, user_id=merchant, session_id=str(run_id)
    )
    if session is None:
        raise HTTPException(404, "Run not found.")
    response.headers["Cache-Control"] = "no-store"
    events = []
    for event in session.events:
        for part in event.content.parts or [] if event.content else []:
            if part.function_call:
                events.append(
                    {
                        "author": event.author,
                        "tool": part.function_call.name,
                        "status": "Called",
                        "time": event.timestamp,
                    }
                )
            if part.function_response:
                result = part.function_response.response or {}
                events.append(
                    {
                        "author": event.author,
                        "tool": part.function_response.name,
                        "status": result.get("status"),
                        "code": result.get("code"),
                        "time": event.timestamp,
                    }
                )
    return {
        "events": events,
        "forecast": session.state.get("cashflow_forecast"),
        "capacity": session.state.get("repayment_capacity"),
        "decision": session.state.get("payment_decision"),
        "graph": present(session.state)["graph"],
    }


async def turn(
    merchant: str, run_id: str, part: types.Part
) -> tuple[dict, bytes | None]:
    await run_state(merchant, run_id)
    messages = []
    audio = None
    async for event in get_runner().run_async(
        user_id=merchant,
        session_id=run_id,
        new_message=types.UserContent(parts=[part]),
    ):
        if not event.content or event.content.role != "model":
            continue
        for value in event.content.parts or []:
            if value.text:
                messages.append(
                    re.sub(r"```json\s.*?```", "", value.text, flags=re.S)
                    .removesuffix("Validated invoice JSON")
                    .strip()
                )
            if value.inline_data and value.inline_data.mime_type == "audio/wav":
                audio = value.inline_data.data
    return {**present(await run_state(merchant, run_id)), "messages": messages}, audio


@router.post("/runs/{run_id}/invoice")
async def upload(run_id: UUID, merchant: Merchant, request: Request) -> dict:
    mime_type = request.headers.get("content-type", "")
    if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(415, "Choose a JPEG, PNG, or WebP invoice photo.")
    content = bytearray()
    async for chunk in request.stream():
        if len(content) + len(chunk) > MAX_INVOICE_BYTES:
            raise HTTPException(413, "Use an image no larger than 10 MiB.")
        content.extend(chunk)
    result, _ = await turn(
        merchant,
        str(run_id),
        types.Part.from_bytes(data=bytes(content), mime_type=mime_type),
    )
    return result


class OfferInput(BaseModel):
    discount_paise: int = Field(gt=0, le=999_999_999_999)
    deadline: str = Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


@router.post("/runs/{run_id}/offer")
async def offer(run_id: UUID, merchant: Merchant, body: OfferInput) -> dict:
    state = await run_state(merchant, str(run_id))
    intake = (state.get("invoice_intake_result") or {}).get("intake_id")
    if not intake:
        raise HTTPException(409, "Upload an invoice first.")
    result, _ = await turn(
        merchant,
        str(run_id),
        types.Part(
            text=f"confirm-offer {intake} {body.discount_paise} {body.deadline}"
        ),
    )
    return result


class ConfirmInput(BaseModel):
    proposal_id: UUID
    accepted: Literal[True]


@router.post("/runs/{run_id}/confirm")
async def confirm(run_id: UUID, merchant: Merchant, body: ConfirmInput) -> dict:
    result, _ = await turn(
        merchant, str(run_id), types.Part(text=f"confirm-payment {body.proposal_id}")
    )
    return result


@router.post("/runs/{run_id}/repayment")
async def repayment(run_id: UUID, merchant: Merchant) -> dict:
    result, _ = await turn(merchant, str(run_id), types.Part(text="repayment-status"))
    return result


@router.post("/runs/{run_id}/voice")
async def voice(run_id: UUID, merchant: Merchant) -> Response:
    result, audio = await turn(merchant, str(run_id), types.Part(text="read-payment"))
    if audio is None:
        raise HTTPException(503, " ".join(result["messages"]) or "Audio unavailable.")
    return Response(
        audio, media_type="audio/wav", headers={"Cache-Control": "no-store"}
    )
