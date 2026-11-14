"""Cashflow Affordability Agent using empirical P20 quantile regression."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CashflowAffordabilityResult:
    history_days: int
    p50_daily_settlement: int
    p20_daily_settlement: int
    p20_total_settlement: int
    existing_edi_daily: int
    safe_edi_cap: int
    coverage_ratio: float
    decision: str
    recommended_action: str


def compute_cashflow_affordability(
    p50_daily: int,
    p20_daily: int,
    existing_edi_daily: int,
    tenor_days: int = 20,
    max_edi_share_of_p20: float = 0.25,
    required_daily_edi: int = 1953,
) -> CashflowAffordabilityResult:
    safe_edi_cap = max(
        0, int(p20_daily * max_edi_share_of_p20 - existing_edi_daily)
    )
    p20_total = p20_daily * tenor_days

    total_daily_obligations = existing_edi_daily + required_daily_edi
    coverage_ratio = (
        round(p20_daily / total_daily_obligations, 2)
        if total_daily_obligations > 0
        else 5.0
    )

    if safe_edi_cap >= required_daily_edi:
        decision = "SUFFICIENT_CAPACITY"
        action = "APPROVE_FULL_CAPACITY"
    elif safe_edi_cap > 250:
        decision = "TIGHT_CAPACITY"
        action = "PARTIAL_FUNDING_RECOMMENDED"
    else:
        decision = "INSUFFICIENT_CAPACITY"
        action = "DECLINE_OR_CASH_PAYMENT"

    return CashflowAffordabilityResult(
        history_days=90,
        p50_daily_settlement=p50_daily,
        p20_daily_settlement=p20_daily,
        p20_total_settlement=p20_total,
        existing_edi_daily=existing_edi_daily,
        safe_edi_cap=safe_edi_cap,
        coverage_ratio=coverage_ratio,
        decision=decision,
        recommended_action=action,
    )
