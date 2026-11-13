"""Read one merchant's daily net settlements and existing demo EDI."""

from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.engine import Engine


class SettlementRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def history(self, merchant: str, as_of: date) -> tuple[dict[date, int], int]:
        with self.engine.connect() as connection:
            edi = connection.execute(
                text("SELECT existing_edi_daily FROM merchants WHERE id=:merchant"),
                {"merchant": merchant},
            ).scalar_one_or_none()
            if edi is None:
                raise ValueError("Merchant history unavailable")
            rows = connection.execute(
                text(
                    "SELECT settlement_date, amount FROM settlements "
                    "WHERE merchant_id=:merchant AND settlement_date>=:start "
                    "AND settlement_date<:end ORDER BY settlement_date"
                ),
                {
                    "merchant": merchant,
                    "start": as_of - timedelta(days=90),
                    "end": as_of,
                },
            )
            return {day: int(amount * 100) for day, amount in rows}, int(edi * 100)
