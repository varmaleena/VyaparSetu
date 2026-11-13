"""PostgreSQL persistence for intake records and their audit events."""

from dataclasses import dataclass
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.engine import Engine

from app.models.invoice import IntakeContext, InvoiceImage, InvoiceIntakeResult
from app.services.storage_service import StoredInvoice

metadata = sa.MetaData()
intakes = sa.Table(
    "invoice_intakes",
    metadata,
    sa.Column("id", sa.String),
    sa.Column("merchant_id", sa.String),
    sa.Column("session_id", sa.String),
    sa.Column("object_uri", sa.Text),
    sa.Column("object_generation", sa.BigInteger),
    sa.Column("media_type", sa.String),
    sa.Column("size_bytes", sa.Integer),
    sa.Column("sha256", sa.String),
)
audit_events = sa.Table(
    "audit_events",
    metadata,
    sa.Column("id", sa.String),
    sa.Column("merchant_id", sa.String),
    sa.Column("session_id", sa.String),
    sa.Column("event_type", sa.String),
    sa.Column("payload", sa.JSON),
)
merchants = sa.table("merchants", sa.column("id"))


@dataclass(frozen=True)
class IntakeObject:
    uri: str
    media_type: str


class InvoiceRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def merchant_exists(self, merchant_id: str) -> bool:
        with self.engine.connect() as connection:
            return (
                connection.scalar(
                    sa.select(merchants.c.id).where(merchants.c.id == merchant_id)
                )
                is not None
            )

    def record(
        self,
        context: IntakeContext,
        result: InvoiceIntakeResult,
        image: InvoiceImage | None = None,
        stored: StoredInvoice | None = None,
    ) -> None:
        with self.engine.begin() as connection:
            if image is not None and stored is not None:
                connection.execute(
                    intakes.insert().values(
                        id=result.intake_id,
                        merchant_id=context.merchant_id,
                        session_id=context.session_id,
                        object_uri=stored.uri,
                        object_generation=stored.generation,
                        media_type=image.media_type,
                        size_bytes=len(image.content),
                        sha256=image.sha256,
                    )
                )
            connection.execute(
                audit_events.insert().values(
                    id=str(uuid4()),
                    merchant_id=context.merchant_id,
                    session_id=context.session_id,
                    event_type="INVOICE_INTAKE",
                    payload={
                        "status": result.status,
                        "code": result.code,
                        "intake_id": result.intake_id,
                    },
                )
            )

    def intake_exists(self, intake_id: str) -> bool:
        with self.engine.connect() as connection:
            return (
                connection.scalar(
                    sa.select(intakes.c.id).where(intakes.c.id == intake_id)
                )
                is not None
            )

    def get_invoice_object(
        self, context: IntakeContext, intake_id: str
    ) -> IntakeObject | None:
        statement = sa.select(intakes.c.object_uri, intakes.c.media_type).where(
            intakes.c.id == intake_id,
            intakes.c.merchant_id == context.merchant_id,
            intakes.c.session_id == context.session_id,
        )
        with self.engine.connect() as connection:
            row = connection.execute(statement).one_or_none()
        if row is None:
            return None
        return IntakeObject(uri=row.object_uri, media_type=row.media_type)
