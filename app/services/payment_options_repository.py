"""Merchant-scoped payment inputs from the current funding record."""

from datetime import date

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.models.decision import FinancingOffer, Funding


class PaymentOptionsRepository:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def get(self, merchant: str, as_of: date) -> Funding | None:
        with self.engine.connect() as conn:
            row = (
                conn.execute(
                    text(
                        "SELECT m.available_cash, f.instant_net, f.instant_fee, f.offer_version,"
                        " f.daily_rate_bps, f.fee_paise, f.tenor_days "
                        "FROM merchants m LEFT JOIN merchant_funding f ON f.merchant_id=m.id "
                        "AND :as_of BETWEEN f.valid_from AND f.valid_until WHERE m.id=:id"
                    ),
                    {"id": merchant, "as_of": as_of},
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            return None
        offer = None
        if row["offer_version"] is not None:
            offer = FinancingOffer(
                version=row["offer_version"],
                daily_rate_bps=row["daily_rate_bps"],
                fee_paise=row["fee_paise"],
                tenor_days=row["tenor_days"],
            )
        return Funding(
            cash=int(row["available_cash"] * 100),
            instant_net=row["instant_net"] or 0,
            instant_fee=row["instant_fee"] or 0,
            offer=offer,
        )
