"""Deterministic Discount Arbitrage Agent."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ArbitrageResult:
    invoice_amount: int
    discount_percent: float
    discount_value: int
    net_payable_to_supplier: int
    tenor_days: int
    apr_percent: float
    financing_interest_cost: int
    net_benefit_savings: int
    daily_edi: int
    recommendation: str
    annualized_return_percent: float


def calculate_discount_arbitrage(
    invoice_amount: int,
    discount_percent: float,
    tenor_days: int = 20,
    annual_apr: float = 0.24,  # 24% p.a.
) -> ArbitrageResult:
    discount_value = int(invoice_amount * discount_percent / 100)
    pay = invoice_amount - discount_value

    # Daily EDI repays principal daily, so interest accrues on the declining balance
    interest = int(pay * annual_apr * (tenor_days + 1) / (2 * 365))
    net_benefit = discount_value - interest
    daily_edi = int((pay + interest) / tenor_days)

    # Annualized return of supplier discount: (disc / (100 - disc)) * (365 / tenor)
    if 100 - discount_percent > 0:
        annualized = round(
            (discount_percent / (100 - discount_percent)) * (365 / tenor_days) * 100, 1
        )
    else:
        annualized = 0.0

    if net_benefit > 0:
        rec = "PROFITABLE_EARLY_PAYMENT"
    elif net_benefit == 0:
        rec = "BREAK_EVEN"
    else:
        rec = "NOT_PROFITABLE_PAY_ON_DUE_DATE"

    return ArbitrageResult(
        invoice_amount=invoice_amount,
        discount_percent=discount_percent,
        discount_value=discount_value,
        net_payable_to_supplier=pay,
        tenor_days=tenor_days,
        apr_percent=round(annual_apr * 100, 1),
        financing_interest_cost=interest,
        net_benefit_savings=net_benefit,
        daily_edi=daily_edi,
        recommendation=rec,
        annualized_return_percent=annualized,
    )
