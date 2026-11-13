from datetime import date

import pytest
from pydantic import ValidationError

from app.models.decision import PaymentOption
from app.models.payment import PaymentConsent, PaymentProposal
from app.services.payment_simulator import simulate_payment


def test_simulated_schedule_reconciles_to_exact_paise() -> None:
    proposal = PaymentProposal(
        id="proposal",
        intake_id="intake",
        supplier_id="supplier",
        supplier_name="Demo Supplier",
        masked_account="****4200",
        amount_paise=3_880_000,
        deadline=date(2026, 11, 30),
        tenor_days=10,
        option=PaymentOption(
            method="FINANCING",
            cash=1_680_000,
            principal=2_200_000,
            repayment_total=2_213_197,
            daily_installment=221_320,
        ),
    )
    receipt = simulate_payment(proposal)
    assert receipt.status == "SIMULATED_PAID"
    assert receipt.installments_paise == [221_320] * 9 + [221_317]
    assert sum(receipt.installments_paise) == proposal.option.repayment_total


def test_consent_requires_explicit_true() -> None:
    with pytest.raises(ValidationError):
        PaymentConsent.model_validate({"terms_digest": "a" * 64, "accepted": False})
