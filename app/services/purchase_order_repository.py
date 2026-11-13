"""Read pre-tax PO line prices for one merchant and supplier."""

import sqlalchemy as sa
from sqlalchemy.engine import Engine

from app.models.pricing import PurchaseOrderPrice

purchase_order_prices = sa.table(
    "purchase_order_prices",
    *(
        sa.column(name)
        for name in (
            "id",
            "merchant_id",
            "supplier_gstin",
            "purchase_order_number",
            "description",
            "hsn",
            "unit",
            "unit_price_paise",
        )
    ),
)


class PurchaseOrderRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def find_prices(
        self,
        merchant_id: str,
        gstin: str,
        purchase_order_number: str,
    ) -> list[PurchaseOrderPrice]:
        table = purchase_order_prices
        statement = sa.select(
            table.c.id,
            table.c.description,
            table.c.hsn,
            table.c.unit,
            table.c.unit_price_paise,
        ).where(
            table.c.merchant_id == merchant_id,
            table.c.supplier_gstin == gstin,
            table.c.purchase_order_number == purchase_order_number,
        )
        with self.engine.connect() as connection:
            return [
                PurchaseOrderPrice.model_validate(row)
                for row in connection.execute(statement).mappings()
            ]
