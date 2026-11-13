from datetime import date

import pytest

from app.models.decision import FinancingOffer, Funding
from app.models.invoice import EarlyPaymentTerms, ExtractedInvoice
from app.tools.payment_decision_tools import (
    apply_payment_policy,
    calculate_payment_economics,
)

DAY = date(2026, 11, 12)


@pytest.mark.parametrize(
    ("funding", "cap", "status", "principal", "savings"),
    [
        (
            Funding(
                cash=1_680_000,
                offer=FinancingOffer(
                    version="test", daily_rate_bps=6, fee_paise=0, tenor_days=10
                ),
            ),
            240_420,
            "FINANCING_FITS",
            2_200_000,
            106_800,
        ),
        (Funding(cash=50_000, instant_net=500_000), 0, "WAIT", None, None),
        (Funding(cash=3_880_000), 0, "PAY_FROM_AVAILABLE_FUNDS", 0, 120_000),
        (
            Funding(cash=3_800_000, instant_net=100_000, instant_fee=100),
            0,
            "PAY_FROM_AVAILABLE_FUNDS",
            0,
            119_900,
        ),
    ],
)
def test_payment_decision(funding, cap, status, principal, savings):
    invoice = ExtractedInvoice(
        supplier_name="Synthetic supplier",
        supplier_gstin=None,
        invoice_number="42",
        invoice_date=DAY,
        due_date=DAY,
        currency="INR",
        lines=[],
        total_paise=4_000_000,
        tax_added_paise=0,
        adjustment_paise=0,
        discount_status="offered",
        discount=EarlyPaymentTerms(
            rate_bps=300,
            amount_paise=120_000,
            deadline=DAY,
            requires_full_payment=True,
        ),
    )
    decision = apply_payment_policy(
        calculate_payment_economics(invoice, funding, cap, DAY)
    )
    assert decision.status == status
    if principal is None:
        assert decision.selected is None
    else:
        option = decision.selected
        assert option is not None
        assert (option.principal, option.net_savings) == (principal, savings)
        assert option.cash + option.instant_net + option.principal == 3_880_000
        if principal:
            assert option.daily_installment == 221_320
