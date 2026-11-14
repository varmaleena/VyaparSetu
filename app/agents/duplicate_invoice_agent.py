"""Deterministic Duplicate Invoice Screening Agent."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


@dataclass
class DuplicateScreeningResult:
    fingerprint: str
    is_duplicate: bool
    similarity_score: float
    matched_invoice_id: str | None
    decision: str


class DuplicateInvoiceAgent:
    _known_fingerprints: dict[str, str] = {}

    @classmethod
    def generate_fingerprint(
        cls,
        supplier_gstin: str,
        invoice_number: str,
        invoice_date: str,
        total_amount: int,
        line_items: list[dict[str, Any]] | None = None,
    ) -> str:
        lines_norm = sorted(
            [f"{item.get('name', '')}:{item.get('amount', 0)}" for item in (line_items or [])]
        )
        raw = f"{supplier_gstin.strip().upper()}:{invoice_number.strip().upper()}:{invoice_date}:{total_amount}:{'|'.join(lines_norm)}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    def check_duplicate(
        cls,
        fingerprint: str,
        current_session_id: str,
    ) -> DuplicateScreeningResult:
        if fingerprint in cls._known_fingerprints:
            prior_session = cls._known_fingerprints[fingerprint]
            if prior_session != current_session_id:
                return DuplicateScreeningResult(
                    fingerprint=fingerprint,
                    is_duplicate=True,
                    similarity_score=1.0,
                    matched_invoice_id=prior_session,
                    decision="BLOCK_DUPLICATE_FINANCING",
                )

        cls._known_fingerprints[fingerprint] = current_session_id
        return DuplicateScreeningResult(
            fingerprint=fingerprint,
            is_duplicate=False,
            similarity_score=0.0,
            matched_invoice_id=None,
            decision="PROCEED_CLEAR",
        )
