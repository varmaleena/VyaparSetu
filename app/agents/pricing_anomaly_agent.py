"""Pricing Anomaly and Discount Plausibility Agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PricingAnomalyResult:
    anomaly_score: float
    discount_plausible: bool
    flagged_items: list[str]
    decision: str


class PricingAnomalyAgent:
    @staticmethod
    def evaluate(
        line_items: list[dict[str, Any]],
        cash_discount_percent: float,
        max_discount_auto: float = 5.0,
    ) -> PricingAnomalyResult:
        flagged: list[str] = []

        # Discount plausibility check
        discount_plausible = cash_discount_percent <= max_discount_auto
        if not discount_plausible:
            flagged.append(
                f"Abnormal early discount rate of {cash_discount_percent}% exceeds auto-policy limit ({max_discount_auto}%)."
            )

        for item in line_items:
            unit_price = item.get("unit_price")
            baseline_mean = item.get("baseline_mean")
            baseline_std = item.get("baseline_std", 1.0)
            if unit_price and baseline_mean and baseline_std > 0:
                z_score = abs(unit_price - baseline_mean) / baseline_std
                if z_score > 3.0:
                    flagged.append(
                        f"Price anomaly on {item.get('name', 'item')}: unit price ₹{unit_price} is {z_score:.1f} std devs from baseline."
                    )

        anomaly_score = 0.0 if not flagged else 0.85
        decision = "PROCEED" if not flagged else "FLAG_FOR_POLICY_REVIEW"

        return PricingAnomalyResult(
            anomaly_score=anomaly_score,
            discount_plausible=discount_plausible,
            flagged_items=flagged,
            decision=decision,
        )
