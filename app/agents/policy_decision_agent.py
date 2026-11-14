"""Deterministic Policy Decision Engine following versioned YAML credit rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

PolicyOutcome = Literal[
    "APPROVE_FULL",
    "APPROVE_PARTIAL",
    "DECLINE_LOW_CAPACITY",
    "DECLINE_HIGH_RISK",
    "DECLINE_FRAUD",
    "MANUAL_REVIEW",
]


@dataclass
class PolicyDecisionResult:
    decision: PolicyOutcome
    approved_amount: int
    tenor_days: int
    daily_edi: int
    reason_codes: list[str]
    why_not_explanation: str
    merchant_explanation: str
    safe_edi_cap: int
    policy_version: str = "2026-11-v1"


def evaluate_credit_policy(
    invoice_amount: int,
    net_payable_after_discount: int,
    p20_daily_settlement: int,
    existing_edi_daily: int,
    tenor_days: int = 20,
    daily_interest_rate: float = 0.0006,  # 24% p.a. / 365
    max_edi_share_of_p20: float = 0.25,  # Lender dial
    supplier_status: str = "VERIFIED",
    duplicate_detected: bool = False,
    pricing_anomaly_flag: bool = False,
    discount_expired: bool = False,
) -> PolicyDecisionResult:
    reasons: list[str] = []

    # Hard rules
    if duplicate_detected:
        return PolicyDecisionResult(
            decision="DECLINE_FRAUD",
            approved_amount=0,
            tenor_days=0,
            daily_edi=0,
            reason_codes=["DUPLICATE_INVOICE_FINGERPRINT_EXISTS"],
            why_not_explanation="Duplicate invoice identified in registry. Double financing is blocked.",
            merchant_explanation="Ee invoice mundhe record cheyyabadindhi. Double financing allowed kadhu.",
            safe_edi_cap=0,
        )

    if supplier_status == "BLOCKED" or supplier_status == "INVALID_GSTIN":
        return PolicyDecisionResult(
            decision="DECLINE_HIGH_RISK",
            approved_amount=0,
            tenor_days=0,
            daily_edi=0,
            reason_codes=["SUPPLIER_RISK_BLOCKED"],
            why_not_explanation="Supplier verification failed or supplier is blacklisted.",
            merchant_explanation="Supplier verification fail ayyindi. Safe payment kudharadhu.",
            safe_edi_cap=0,
        )

    if discount_expired:
        return PolicyDecisionResult(
            decision="DECLINE_LOW_CAPACITY",
            approved_amount=0,
            tenor_days=0,
            daily_edi=0,
            reason_codes=["DISCOUNT_EXPIRED"],
            why_not_explanation="Cash discount offer has expired.",
            merchant_explanation="Supplier discount deadline ayipoyindi. Normal due date lo pay cheyyandi.",
            safe_edi_cap=0,
        )

    # Calculate safe EDI deduction cap
    safe_edi_cap = max(
        0, int(p20_daily_settlement * max_edi_share_of_p20 - existing_edi_daily)
    )

    if safe_edi_cap <= 0:
        return PolicyDecisionResult(
            decision="DECLINE_LOW_CAPACITY",
            approved_amount=0,
            tenor_days=0,
            daily_edi=0,
            reason_codes=["SAFE_EDI_CAP_ZERO", "EXISTING_OBLIGATIONS_CONSUME_CAPACITY"],
            why_not_explanation="Existing daily EDI obligations fully consume conservative settlement capacity.",
            merchant_explanation="Mee unna EDI obligations valla kotha loan ippude safe kadhu.",
            safe_edi_cap=0,
        )

    # Interest & EDI required for full amount
    interest = int(
        net_payable_after_discount * daily_interest_rate * (tenor_days + 1) / 2
    )
    full_daily_edi = int((net_payable_after_discount + interest) / tenor_days)

    if full_daily_edi <= safe_edi_cap:
        # Full approval
        return PolicyDecisionResult(
            decision="APPROVE_FULL",
            approved_amount=net_payable_after_discount,
            tenor_days=tenor_days,
            daily_edi=full_daily_edi,
            reason_codes=[
                "SUPPLIER_VERIFIED",
                "P20_CAPACITY_SUFFICIENT",
                "DISCOUNT_PROFITABLE",
            ],
            why_not_explanation="Full financing approved. Exposure is within conservative capacity limits.",
            merchant_explanation="Mee collections stable ga unnai. Full amount safe ga finance cheyyavachu.",
            safe_edi_cap=safe_edi_cap,
        )

    # Partial approval sizing
    max_safe_total_repayment = safe_edi_cap * tenor_days
    # Solve for principal: P + P * rate * (T+1)/2 = Total
    approx_principal = int(
        max_safe_total_repayment / (1 + daily_interest_rate * (tenor_days + 1) / 2)
    )
    # Round down to nearest 100
    safe_approved_principal = max(0, (approx_principal // 100) * 100)

    if safe_approved_principal < 5000:
        return PolicyDecisionResult(
            decision="DECLINE_LOW_CAPACITY",
            approved_amount=0,
            tenor_days=0,
            daily_edi=0,
            reason_codes=["BELOW_MINIMUM_TICKET"],
            why_not_explanation="Safe financing capacity is below minimum loan ticket (₹5,000).",
            merchant_explanation="Safe capacity chala takkuva ga undhi. Ee bill ki financing safe kadhu.",
            safe_edi_cap=safe_edi_cap,
        )

    partial_interest = int(
        safe_approved_principal * daily_interest_rate * (tenor_days + 1) / 2
    )
    partial_daily_edi = int((safe_approved_principal + partial_interest) / tenor_days)
    needed_p20_for_full = int(
        (full_daily_edi + existing_edi_daily) / max_edi_share_of_p20
    )

    return PolicyDecisionResult(
        decision="APPROVE_PARTIAL",
        approved_amount=safe_approved_principal,
        tenor_days=tenor_days,
        daily_edi=partial_daily_edi,
        reason_codes=[
            "P20_FORECAST_BELOW_FULL_INVOICE_REQUIREMENT",
            "SAFE_EDI_CAP_APPLIED",
            "SUPPLIER_VERIFIED",
        ],
        why_not_explanation=f"Full approval requires at least ₹{needed_p20_for_full:,}/day conservative P20 inflow (currently ₹{p20_daily_settlement:,}/day). ₹{safe_approved_principal:,} is the safe limit.",
        merchant_explanation=f"Mee QR collections conservative estimate prakaram, full amount safe ga repay cheyyalem. ₹{safe_approved_principal:,} finance cheyyadam safe.",
        safe_edi_cap=safe_edi_cap,
    )
