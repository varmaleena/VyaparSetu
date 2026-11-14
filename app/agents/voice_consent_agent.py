"""Voice Consent Agent for Sarvam and Web Speech consent capturing."""

from __future__ import annotations

from typing import Any

from app.services.voice_soundbox_service import (
    generate_voice_script,
    validate_merchant_voice_response,
)


class VoiceConsentAgent:
    @staticmethod
    def prepare_consent_payload(
        decision_id: str,
        supplier_name: str,
        invoice_amount: int,
        approved_amount: int,
        discount_pct: float,
        discount_val: int,
        tenor_days: int,
        daily_edi: int,
        financing_cost: int,
        net_benefit: int,
        language: str = "te",
    ) -> dict[str, Any]:
        payload = generate_voice_script(
            decision_id=decision_id,
            supplier_name=supplier_name,
            invoice_amount=invoice_amount,
            approved_amount=approved_amount,
            discount_pct=discount_pct,
            discount_val=discount_val,
            tenor_days=tenor_days,
            daily_edi=daily_edi,
            financing_cost=financing_cost,
            net_benefit=net_benefit,
            language=language,
        )
        return {
            "language": payload.language,
            "script": payload.script,
            "decision_hash": payload.decision_hash,
            "amount": payload.amount,
            "tenor_days": payload.tenor_days,
            "daily_edi": payload.daily_edi,
            "net_savings": payload.net_savings,
            "supplier_name": payload.supplier_name,
            "status": "CONSENT_PENDING",
            "cancel_window_seconds": 30,
        }

    @staticmethod
    def process_consent_utterance(
        utterance: str, expected_decision_hash: str, provided_hash: str
    ) -> dict[str, Any]:
        if expected_decision_hash != provided_hash:
            return {
                "status": "DECISION_HASH_MISMATCH",
                "valid": False,
                "message": "Security error: Decision terms modified after presentation. Consent rejected.",
            }

        status, valid, msg = validate_merchant_voice_response(utterance)
        return {
            "status": status,
            "valid": valid,
            "transcript": utterance,
            "decision_hash": expected_decision_hash,
            "message": msg,
        }
