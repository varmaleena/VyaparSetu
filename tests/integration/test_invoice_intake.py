"""Independent intake and API contract tests with synthetic bill images."""

import asyncio
from io import BytesIO
from unittest.mock import Mock

import httpx
import pytest
from PIL import Image, ImageDraw
from sqlalchemy.exc import SQLAlchemyError

from app.agents.intake_runner import IntakeRunner
from app.api.invoice_routes import get_intake_runner
from app.config.settings import get_settings
from app.fast_api_app import app
from app.models.invoice import MAX_INVOICE_BYTES, IntakeContext
from app.services.invoice_intake import InvoiceIntake
from app.services.invoice_repository import InvoiceRepository
from app.services.storage_service import InvoiceStorage, StoredInvoice
from app.tools.invoice_tools import InvoiceImageError, validate_invoice_image


def bill_image(*, blank: bool = False, image_format: str = "PNG") -> bytes:
    image = Image.new("RGB", (800, 600), "white")
    if not blank:
        draw = ImageDraw.Draw(image)
        for row in range(40, 560, 24):
            draw.text((45, row), "DEMO INVOICE   ITEM 42    INR 1,000.00", fill="black")
            draw.line((40, row + 14, 760, row + 14), fill="black", width=2)
    output = BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()


@pytest.mark.parametrize(
    ("content", "code"),
    [
        (b"not an image", "UNREADABLE_IMAGE"),
        (bill_image(image_format="GIF"), "UNSUPPORTED_IMAGE"),
        (bill_image(blank=True), "LOW_IMAGE_DETAIL"),
        (b"x" * (MAX_INVOICE_BYTES + 1), "FILE_TOO_LARGE"),
    ],
)
def test_invalid_images(content: bytes, code: str) -> None:
    with pytest.raises(InvoiceImageError) as caught:
        validate_invoice_image(content)
    assert caught.value.code == code


def test_failed_db_write_cleans_up_exact_generation() -> None:
    storage = Mock(spec=InvoiceStorage)
    repository = Mock(spec=InvoiceRepository)
    stored = StoredInvoice("intake/test", "gs://private/intake/test", 5)
    storage.upload.return_value = stored
    repository.record.side_effect = [SQLAlchemyError(), None]
    repository.intake_exists.return_value = False
    result = InvoiceIntake(storage, repository).process(
        IntakeContext(merchant_id="merchant", session_id="session"), bill_image()
    )
    assert result.status == "UNAVAILABLE"
    storage.delete.assert_called_once_with(stored)


def test_ambiguous_commit_preserves_committed_object() -> None:
    storage = Mock(spec=InvoiceStorage)
    repository = Mock(spec=InvoiceRepository)
    storage.upload.return_value = StoredInvoice(
        "intake/test", "gs://private/intake/test", 5
    )
    repository.record.side_effect = SQLAlchemyError()
    repository.intake_exists.return_value = True
    result = InvoiceIntake(storage, repository).process(
        IntakeContext(merchant_id="merchant", session_id="session"), bill_image()
    )
    assert result.status == "ACCEPTED"
    storage.delete.assert_not_called()


def test_intake_session_ownership_and_state(monkeypatch: pytest.MonkeyPatch) -> None:
    from pydantic import SecretStr

    settings = get_settings()
    monkeypatch.setattr(settings, "invoice_bucket", "private")
    monkeypatch.setattr(settings, "invoice_demo_token", SecretStr("test-token"))
    monkeypatch.setattr(settings, "invoice_demo_merchant_id", "merchant-a")
    storage = Mock(spec=InvoiceStorage)
    storage.upload.return_value = StoredInvoice(
        "intake/test", "gs://private/intake/test", 5
    )
    repository = Mock(spec=InvoiceRepository)
    repository.merchant_exists.return_value = True
    runner = IntakeRunner(InvoiceIntake(storage, repository))
    monkeypatch.setitem(app.dependency_overrides, get_intake_runner, lambda: runner)

    async def check() -> None:
        other = await runner.create_session("merchant-b")
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client,
        ):
            assert (await client.post("/invoice-intake/sessions")).status_code == 401
            client.headers["Authorization"] = "Bearer test-token"
            rejected = await client.post(
                f"/invoice-intake/sessions/{other.id}/image", content=bill_image()
            )
            assert rejected.status_code == 404
            response = await client.post("/invoice-intake/sessions")
            assert response.status_code == 201
            session_id = response.json()["session_id"]
            response = await client.post(
                f"/invoice-intake/sessions/{session_id}/image", content=bill_image()
            )
            assert response.status_code == 201
            assert response.json()["status"] == "ACCEPTED"
            assert response.json()["invoice_image_ref"] == "gs://private/intake/test"
            session = await runner.get_session("merchant-a", session_id)
            assert session is not None
            assert session.state["invoice_image_ref"] == "gs://private/intake/test"
            assert session.state["invoice_intake_result"]["status"] == "ACCEPTED"
            assert all(
                part.inline_data is None
                for event in session.events
                if event.content
                for part in event.content.parts or []
            )
        storage.upload.assert_called_once()

    asyncio.run(check())
