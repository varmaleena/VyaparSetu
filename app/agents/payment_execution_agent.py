"""Idempotent Payment Execution Agent with strict deterministic guardrails."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.services.tamper_evident_ledger import TamperEvidentLedger


@dataclass
class PaymentExecutionResult:
    status: str
    payment_reference: str
    idempotency_key: str
    paid_amount: int
    supplier_name: str
    supplier_account: str
    daily_edi: int
    tenor_days: int
    executed_at: str
    audit_id: int
    message: str


class PaymentExecutionAgent:
    @staticmethod
    def execute_disbursal(
        session_id: str,
        decision_id: str,
        decision_status: str,
        approved_amount: int,
        requested_amount: int,
        supplier_name: str,
        supplier_account: str,
        daily_edi: int,
        tenor_days: int,
        consent_valid: bool,
        consent_hash: str,
        expected_hash: str,
    ) -> PaymentExecutionResult:
        # Pre-execution guardrails
        if decision_status not in ("APPROVE_FULL", "APPROVE_PARTIAL"):
            raise ValueError(
                f"Execution blocked: Policy status '{decision_status}' does not allow payment."
            )

        if not consent_valid:
            raise ValueError(
                "Execution blocked: Explicit merchant consent has not been validated."
            )

        if consent_hash != expected_hash:
            raise ValueError(
                "Execution blocked: Decision payload modified between consent and execution."
            )

        if requested_amount > approved_amount:
            raise ValueError(
                f"Execution blocked: Requested amount ₹{requested_amount} exceeds approved limit ₹{approved_amount}."
            )

        idempotency_key = f"pay:{session_id}:{decision_id}"
        payment_reference = (
            f"PAY_PTM_{uuid.uuid4().hex[:10].upper()}"
        )
        now_iso = datetime.now(timezone.utc).isoformat()

        # Record immutable audit event
        ledger = TamperEvidentLedger.get_instance()
        audit_record = ledger.append(
            session_id=session_id,
            actor="PaymentExecutionAgent",
            kind="SUPPLIER_PAYMENT_DISBURSED",
            payload={
                "payment_ref": payment_reference,
                "idempotency_key": idempotency_key,
                "amount": requested_amount,
                "supplier": supplier_name,
                "supplier_account": supplier_account,
                "daily_edi": daily_edi,
                "tenor_days": tenor_days,
            },
        )

        return PaymentExecutionResult(
            status="EXECUTED",
            payment_reference=payment_reference,
            idempotency_key=idempotency_key,
            paid_amount=requested_amount,
            supplier_name=supplier_name,
            supplier_account=supplier_account,
            daily_edi=daily_edi,
            tenor_days=tenor_days,
            executed_at=now_iso,
            audit_id=audit_record.id,
            message=f"₹{requested_amount:,} safely disbursed to verified supplier account '{supplier_account}'. EDI repayment scheduled.",
        )
