"""Read supplier identity and payout verification from the registry."""

import sqlalchemy as sa
from sqlalchemy.engine import Engine

from app.models.supplier import SupplierRegistryRecord

suppliers = sa.table(
    "suppliers",
    sa.column("id"),
    sa.column("name"),
    sa.column("gstin"),
    sa.column("registry_status"),
    sa.column("payout_account_name"),
    sa.column("payout_last4"),
    sa.column("payout_verified"),
)


class SupplierRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def find_by_gstin(self, gstin: str) -> SupplierRegistryRecord | None:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    sa.select(suppliers).where(suppliers.c.gstin == gstin)
                )
                .mappings()
                .one_or_none()
            )
        return SupplierRegistryRecord.model_validate(row) if row is not None else None
