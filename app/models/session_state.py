"""Reserved for the session state implementation."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PaymentDecision:
    invoice: dict[str, Any]
    expires_at: float
    state: str = "AWAITING_MERCHANT_SELECTION"
    options: list[dict[str, Any]] = field(default_factory=list)
    selected: str | None = None
    approval: str | None = None
    qr_savings: dict[str, Any] | None = None
    receipt: dict[str, Any] | None = None
    policy_version: str = "demo-1"
    calculation_version: str = "paise-1"
