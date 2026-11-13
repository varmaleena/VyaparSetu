"""Opt-in checks against the migrated local PostgreSQL development database."""

import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from uuid import uuid4

import pytest

from app.models.invoice import IntakeContext
from app.services.database_service import create_database_engine
from app.services.invoice_duplicate_repository import InvoiceDuplicateRepository
from app.services.invoice_repository import intakes


@pytest.mark.skipif(
    os.getenv("VYAPARSETU_TEST_POSTGRES") != "1",
    reason="requires migrated and seeded development PostgreSQL",
)
def test_duplicate_checks_in_postgresql() -> None:
    engine = create_database_engine()
    repository = InvoiceDuplicateRepository(engine)
    context = IntakeContext(
        merchant_id="demo-merchant-00", session_id=f"duplicate-test-{uuid4()}"
    )
    intake_ids = [str(uuid4()) for _ in range(7)]
    stamp = uuid4().hex
    gstin = "36AAAAA0000A1Z3"
    invoice_date = date(2080, 1, 1)

    def check(index, number, total, fingerprint, supplier=gstin, day=invoice_date):
        return repository.check(
            context,
            intake_id=intake_ids[index],
            gstin=supplier,
            invoice_number=f"{stamp}-{number}",
            invoice_date=day,
            total_paise=total,
            fingerprint=hashlib.sha256(f"{stamp}-{fingerprint}".encode()).hexdigest(),
        )

    try:
        with engine.begin() as connection:
            connection.execute(
                intakes.insert(),
                [
                    {
                        "id": identifier,
                        "merchant_id": context.merchant_id,
                        "session_id": context.session_id,
                        "object_uri": f"gs://fixture-only/{identifier}",
                        "object_generation": 1,
                        "media_type": "image/png",
                        "size_bytes": 1,
                        "sha256": hashlib.sha256(f"{stamp}-{i}".encode()).hexdigest(),
                    }
                    for i, identifier in enumerate(intake_ids)
                ],
            )
        first = check(0, "one", 4_000_000, "one")
        assert first.status == "CLEAR"
        assert check(0, "one", 4_000_000, "one") == first
        duplicate = check(1, "one", 4_000_000, "one")
        assert (duplicate.status, duplicate.matched_intake_id) == (
            "EXACT_DUPLICATE",
            intake_ids[0],
        )
        near = check(2, "two", 4_039_000, "two")
        assert (near.status, near.matched_intake_id) == ("NEEDS_REVIEW", intake_ids[0])
        assert (
            check(3, "one", 4_000_000, "one", supplier="36AAAAA0001A1Z2").status
            == "CLEAR"
        )
        assert check(4, "one", 4_000_000, "old", day=date(2080, 1, 2)).status == "CLEAR"

        with ThreadPoolExecutor(max_workers=2) as pool:
            simultaneous = list(
                pool.map(lambda i: check(i, "race", 8_000_000, "race"), (5, 6))
            )
        assert sorted(result.status for result in simultaneous) == [
            "CLEAR",
            "EXACT_DUPLICATE",
        ]
    finally:
        with engine.begin() as connection:
            connection.execute(intakes.delete().where(intakes.c.id.in_(intake_ids)))
        engine.dispose()
