"""ADK tools for the invoice workflow's two operations."""

import logging
from contextvars import ContextVar
from typing import Any

from google.adk.tools import FunctionTool, ToolContext
from google.genai import errors
from httpx import HTTPError
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from app.models.invoice import (
    IntakeContext,
    InvoiceIntakeResult,
    InvoiceUnderstandingResult,
)
from app.services.gemini_service import GeminiInvoiceExtractor
from app.services.invoice_intake import InvoiceIntake
from app.services.invoice_repository import InvoiceRepository
from app.tools.invoice_extraction_validation import validate_extraction

logger = logging.getLogger(__name__)


def build_intake_tool(
    service: InvoiceIntake,
    *,
    content: ContextVar[bytes] | None = None,
    demo_merchant: str | None = None,
) -> FunctionTool:
    async def invoice_intake(tool_context: ToolContext) -> dict[str, Any]:
        """Validate and store the single invoice image attached to this request."""
        session = tool_context.session
        context = IntakeContext(
            merchant_id=demo_merchant or session.user_id, session_id=session.id
        )
        image: bytes | None
        if content is not None:
            image = content.get()
        else:
            message = tool_context.user_content
            blobs = (
                [part.inline_data for part in (message.parts or []) if part.inline_data]
                if message
                else []
            )
            image = blobs[0].data if len(blobs) == 1 else None

        if image:
            result = await run_in_threadpool(service.process, context, image)
        else:
            result = await run_in_threadpool(
                service.record_outcome,
                context,
                InvoiceIntakeResult(
                    status="RETRY_CAPTURE",
                    code="IMAGE_REQUIRED",
                    message="Upload one invoice photo.",
                ),
            )
        return result.model_dump(mode="json")

    return FunctionTool(invoice_intake)


def build_understanding_tool(
    repository: InvoiceRepository,
    extractor: GeminiInvoiceExtractor,
    *,
    demo_merchant: str | None = None,
) -> FunctionTool:
    async def invoice_understanding(
        intake_id: str, tool_context: ToolContext
    ) -> dict[str, Any]:
        """Extract and validate the invoice stored under the given intake ID."""
        session = tool_context.session
        context = IntakeContext(
            merchant_id=demo_merchant or session.user_id, session_id=session.id
        )
        try:
            stored = await run_in_threadpool(
                repository.get_invoice_object, context, intake_id
            )
            if stored is None:
                result = InvoiceUnderstandingResult(
                    status="UNAVAILABLE",
                    code="INTAKE_NOT_FOUND",
                    message="The saved invoice is unavailable. Please upload it again.",
                )
            else:
                result = validate_extraction(await extractor.extract(stored))
        except (SQLAlchemyError, errors.APIError, HTTPError, ValueError) as exc:
            logger.warning(
                "invoice_extraction_failed intake_id=%s error_type=%s provider_code=%s",
                intake_id,
                type(exc).__name__,
                getattr(exc, "code", None),
            )
            result = InvoiceUnderstandingResult(
                status="UNAVAILABLE",
                code="EXTRACTION_FAILED",
                message="Invoice extraction is temporarily unavailable. Try again.",
            )
        return result.model_dump(mode="json")

    return FunctionTool(invoice_understanding)
