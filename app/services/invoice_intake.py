"""Coordinate image validation, object storage, and intake persistence."""

import logging
from uuid import uuid4

from google.api_core.exceptions import GoogleAPICallError, RetryError
from google.cloud import storage as gcs
from sqlalchemy.exc import SQLAlchemyError

from app.config.settings import Settings
from app.models.invoice import IntakeContext, InvoiceIntakeResult
from app.services.database_service import create_database_engine
from app.services.invoice_repository import InvoiceRepository
from app.services.storage_service import InvoiceStorage
from app.tools.invoice_tools import InvoiceImageError, validate_invoice_image

logger = logging.getLogger(__name__)


class InvoiceIntake:
    def __init__(self, storage: InvoiceStorage, repository: InvoiceRepository) -> None:
        self.storage = storage
        self.repository = repository

    def process(self, context: IntakeContext, content: bytes) -> InvoiceIntakeResult:
        try:
            image = validate_invoice_image(content)
        except InvoiceImageError as exc:
            return self.record_outcome(
                context,
                InvoiceIntakeResult(
                    status="RETRY_CAPTURE", code=exc.code, message=str(exc)
                ),
            )

        intake_id = str(uuid4())
        try:
            stored = self.storage.upload(intake_id, image)
        except (GoogleAPICallError, RetryError, RuntimeError):
            logger.warning("invoice_object_upload_failed intake_id=%s", intake_id)
            return self.record_outcome(context, unavailable("OBJECT_UPLOAD_FAILED"))

        result = InvoiceIntakeResult(
            status="ACCEPTED",
            code="IMAGE_STORED",
            message="Invoice photo received.",
            intake_id=intake_id,
            invoice_image_ref=stored.uri,
        )
        try:
            self.repository.record(context, result, image, stored)
        except SQLAlchemyError:
            try:
                # A connection can fail after the database commits. Check before deleting.
                if self.repository.intake_exists(intake_id):
                    return result
                self.storage.delete(stored)
            except (SQLAlchemyError, GoogleAPICallError, RetryError):
                logger.error(
                    "invoice_object_needs_reconciliation intake_id=%s", intake_id
                )
            logger.warning("invoice_intake_write_failed intake_id=%s", intake_id)
            return self.record_outcome(context, unavailable("INTAKE_WRITE_FAILED"))
        return result

    def record_outcome(
        self, context: IntakeContext, result: InvoiceIntakeResult
    ) -> InvoiceIntakeResult:
        try:
            self.repository.record(context, result)
        except SQLAlchemyError:
            logger.warning("invoice_audit_write_failed")
            return unavailable("AUDIT_WRITE_FAILED")
        return result


def unavailable(code: str) -> InvoiceIntakeResult:
    return InvoiceIntakeResult(
        status="UNAVAILABLE",
        code=code,
        message="Invoice intake is temporarily unavailable. Try again.",
    )


def create_invoice_intake(settings: Settings) -> InvoiceIntake:
    bucket = None
    try:
        if settings.invoice_bucket:
            bucket = gcs.Client(project=settings.invoice_gcp_project).bucket(
                settings.invoice_bucket
            )
    except Exception:
        logger.info("Using local invoice storage adapter for sandbox/demo.")
    return InvoiceIntake(
        InvoiceStorage(bucket), InvoiceRepository(create_database_engine())
    )
