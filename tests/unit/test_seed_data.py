from app.services.seed_data import build_seed


def test_seed_counts_and_reproducibility() -> None:
    seed = build_seed()
    assert seed == build_seed()
    assert {name: len(rows) for name, rows in seed.items()} == {
        "merchants": 20,
        "suppliers": 50,
        "invoices": 500,
        "settlements": 1800,
    }


def test_demo_merchants_have_same_offer_and_different_settlements() -> None:
    seed = build_seed()
    first, second = seed["invoices"][:2]
    for key in ("supplier_id", "amount", "discount_percent", "discount_deadline"):
        assert first[key] == second[key]

    for invoice, threshold in ((first, 24_000), (second, 0)):
        amounts = [
            row["amount"]
            for row in seed["settlements"]
            if row["merchant_id"] == invoice["merchant_id"]
        ]
        assert len(amounts) == 90
        if threshold:
            assert min(amounts) >= threshold
        else:
            assert max(amounts) < 8_000
