"""Multilingual voice script generation and cryptographic decision consent binding."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any


@dataclass
class VoiceScriptPayload:
    language: str
    script: str
    audio_type: str
    decision_hash: str
    amount: int
    tenor_days: int
    daily_edi: int
    net_savings: int
    supplier_name: str


def generate_decision_hash(
    decision_id: str,
    supplier_name: str,
    approved_amount: int,
    tenor_days: int,
    daily_edi: int,
) -> str:
    payload = f"{decision_id}:{supplier_name}:{approved_amount}:{tenor_days}:{daily_edi}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def generate_voice_script(
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
) -> VoiceScriptPayload:
    decision_hash = generate_decision_hash(
        decision_id=decision_id,
        supplier_name=supplier_name,
        approved_amount=approved_amount,
        tenor_days=tenor_days,
        daily_edi=daily_edi,
    )

    # Convert paise to rupees for merchant-friendly readback
    disp_amt = f"₹{approved_amount:,}"
    disp_disc = f"₹{discount_val:,}"
    disp_cost = f"₹{financing_cost:,}"
    disp_net = f"₹{net_benefit:,}"
    disp_edi = f"₹{daily_edi:,}"

    if language == "te":
        script = (
            f"నమస్కారం అన్నా. మీ {supplier_name} సప్లయర్ బిల్లుకు ₹{approved_amount:,} చెల్లించడానికి సిఫార్సు చేస్తున్నాము. "
            f"{discount_pct}% నగదు తగ్గింపు ద్వారా మీరు {disp_disc} ఆదా చేస్తారు. "
            f"{tenor_days} రోజుల ఈడీఐ చార్జీ {disp_cost}. "
            f"మీకు నికర లాభం {disp_net}. "
            f"రోజువారీ చెల్లింపు {disp_edi}. "
            f"ఈ చెల్లింపును ఆమోదించాలా? 'అప్రూవ్' అని చెప్పండి."
        )
    elif language == "hi":
        script = (
            f"नमस्ते भैया। आपके {supplier_name} सप्लायर बिल के लिए ₹{approved_amount:,} के भुगतान का प्रस्ताव है। "
            f"{discount_pct}% कैश डिस्काउंट से आप {disp_disc} की सीधी बचत करेंगे। "
            f"{tenor_days} दिनों का कुल फाइनेंसिंग शुल्क {disp_cost} होगा। "
            f"आपका शुद्ध लाभ {disp_net} है। "
            f"दैनिक ई.डी.आई कटौती {disp_edi} होगी। "
            f"क्या आप इसे मंज़ूर करते हैं? कृपया 'अप्रूव' कहें।"
        )
    else:  # English / Hinglish
        script = (
            f"Hello partner. We propose paying ₹{approved_amount:,} directly to your verified supplier {supplier_name}. "
            f"You save {disp_disc} through a {discount_pct}% early cash discount. "
            f"Total financing cost over {tenor_days} days is {disp_cost}, leaving you with a net profit of {disp_net}. "
            f"Daily deduction from QR settlements is {disp_edi}. "
            f"Do you approve this payment? Say 'Approve' or tap confirm."
        )

    return VoiceScriptPayload(
        language=language,
        script=script,
        audio_type="synthesized",
        decision_hash=decision_hash,
        amount=approved_amount,
        tenor_days=tenor_days,
        daily_edi=daily_edi,
        net_savings=net_benefit,
        supplier_name=supplier_name,
    )


def validate_merchant_voice_response(
    merchant_utterance: str,
) -> tuple[str, bool, str]:
    cleaned = merchant_utterance.strip().lower()
    approvals = [
        "approve",
        "haan",
        "haan approve",
        "ok",
        "yes",
        "cheyyi",
        "avunu",
        "karo",
        "manjoor",
        "theek hai",
        "ha",
        "ha approve",
        "confirm",
    ]
    rejections = [
        "reject",
        "no",
        "vaddhu",
        "ledu",
        "nahi",
        "mat karo",
        "cancel",
        "cash undi",
    ]

    for app in approvals:
        if app in cleaned:
            return (
                "EXPLICIT_APPROVED",
                True,
                "Merchant explicitly approved transaction via voice.",
            )

    for rej in rejections:
        if rej in cleaned:
            return (
                "EXPLICIT_REJECTED",
                False,
                "Merchant declined the financing proposal.",
            )

    return (
        "UNCLEAR",
        False,
        "Voice response was ambiguous. Repeating terms or falling back to on-screen tap.",
    )

