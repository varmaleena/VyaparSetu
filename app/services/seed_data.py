"""Seed reproducible synthetic records into the migrated local database."""

from datetime import date, timedelta
from random import Random

from sqlalchemy import MetaData, Table
from sqlalchemy.dialects.postgresql import insert

from app.services.database_service import create_database_engine
from app.services.purchase_order_repository import purchase_order_prices
from app.tools.supplier_verification import gstin_checksum

AS_OF = date(2026, 11, 12)


def build_seed() -> dict[str, list[dict]]:
    random = Random(42)
    merchants = [
        {
            "id": f"demo-merchant-{i:02}",
            "name": f"Demo shop {i:02}",
            "language": ("te", "hi", "hinglish")[i % 3],
            "available_cash": 16_800 if i == 0 else 500,
            "existing_edi_daily": 1_200,
        }
        for i in range(20)
    ]
    suppliers: list[dict] = [
        {
            "id": f"demo-supplier-{i:02}",
            "name": f"Demo distributor {i:02}",
            "gstin": f"DEMO-GST-{i:02}",
            "account_token": f"demo-account-{i:02}",
        }
        for i in range(50)
    ]
    for i, (name, account_name, status) in enumerate(
        (
            ("Sri Lakshmi Kirana Wholesale", "Sri Lakshmi Kirana Wholesale", "ACTIVE"),
            ("Demo Blocked Supplier", "Demo Blocked Supplier", "BLOCKED"),
            ("Demo Payee Mismatch Supplier", "Different Demo Account Holder", "ACTIVE"),
        )
    ):
        gstin_prefix = f"36AAAAA{i:04}A1Z"
        suppliers[i].update(
            name=name,
            gstin=gstin_prefix + gstin_checksum(gstin_prefix),
            registry_status=status,
            payout_account_name=account_name,
            payout_last4=f"{4200 + i:04}",
            payout_verified=True,
        )
    for supplier in suppliers[3:]:
        supplier.update(
            registry_status="UNVERIFIED",
            payout_account_name=None,
            payout_last4=None,
            payout_verified=False,
        )
    invoices = [
        {
            "id": f"demo-invoice-{i:03}",
            "merchant_id": merchants[i % len(merchants)]["id"],
            "supplier_id": suppliers[0 if i < 2 else i % len(suppliers)]["id"],
            "invoice_number": "DEMO-OFFER" if i < 2 else f"DEMO-{i:03}",
            "amount": 40_000 if i < 2 else random.randint(2_000, 60_000),
            "discount_percent": 3 if i < 2 else random.randint(1, 4),
            "discount_requires_full_payment": True,
            "discount_deadline": AS_OF,
            "due_date": AS_OF + timedelta(days=15),
        }
        for i in range(500)
    ]
    settlements = []
    for i, merchant in enumerate(merchants):
        daily_base = (
            6_000 if i == 0 else 4_500 if i == 1 else random.randint(6_000, 28_000)
        )
        for offset in range(1, 91):
            day = AS_OF - timedelta(days=offset)
            amount = daily_base + random.randint(-1_000, 1_000)
            if day.weekday() == 5:
                amount += 1_000
            settlements.append(
                {
                    "id": f"demo-settlement-{i:02}-{offset:02}",
                    "merchant_id": merchant["id"],
                    "settlement_date": day,
                    "amount": amount,
                }
            )
    return {
        "merchants": merchants,
        "suppliers": suppliers,
        "invoices": invoices,
        "settlements": settlements,
    }


def demo_purchase_order_prices(gstin: str) -> list[dict]:
    products = [
        ("Packaged wheat atta, 10 kg", "1101", "bags", 35_000),
        ("Refined sunflower oil, 1 L", "1512", "pcs", 18_000),
        ("Packaged toor dal, 1 kg", "0713", "packs", 16_600),
    ]
    return [
        {
            "id": f"demo-po-slw-0042-{number}",
            "merchant_id": "demo-merchant-00",
            "supplier_gstin": gstin,
            "purchase_order_number": "PO-SLW-0042",
            "description": description,
            "hsn": hsn,
            "unit": unit,
            "unit_price_paise": price,
        }
        for number, (description, hsn, unit, price) in enumerate(products, 1)
    ]


def main() -> None:
    engine = create_database_engine()
    seed = build_seed()
    try:
        with engine.begin() as connection:
            metadata = MetaData()
            for name, rows in seed.items():
                table = Table(name, metadata, autoload_with=connection)
                statement = insert(table)
                if name == "suppliers":
                    statement = statement.on_conflict_do_update(
                        index_elements=["id"],
                        set_={
                            column: statement.excluded[column]
                            for column in rows[0]
                            if column != "id"
                        },
                        where=table.c.gstin.like("DEMO-GST-%"),
                    )
                else:
                    statement = statement.on_conflict_do_nothing(index_elements=["id"])
                connection.execute(statement, rows)
            connection.execute(
                insert(purchase_order_prices).on_conflict_do_nothing(
                    index_elements=["id"]
                ),
                demo_purchase_order_prices(seed["suppliers"][0]["gstin"]),
            )
            funding = Table("merchant_funding", metadata, autoload_with=connection)
            connection.execute(
                insert(funding).on_conflict_do_nothing(index_elements=["merchant_id"]),
                [
                    {
                        "merchant_id": f"demo-merchant-0{i}",
                        "valid_from": AS_OF,
                        "valid_until": AS_OF + timedelta(days=7),
                        "instant_net": 500_000 if i == 1 else 0,
                        "instant_fee": 0,
                        "offer_version": "scenario-2026-11-v1",
                        "daily_rate_bps": 6,
                        "fee_paise": 0,
                        "tenor_days": 10,
                    }
                    for i in range(2)
                ],
            )
    finally:
        engine.dispose()
    print(
        "Synthetic records available: "
        + ", ".join(f"{len(rows)} {name}" for name, rows in seed.items())
    )


if __name__ == "__main__":
    main()
