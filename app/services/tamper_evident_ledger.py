"""Tamper-evident SHA-256 hash-chained audit ledger with verification and tamper testing."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class AuditRecord:
    id: int
    session_id: str
    actor: str
    kind: str
    payload: dict[str, Any]
    prev_hash: str
    hash: str
    created_at: str


class TamperEvidentLedger:
    _instance: TamperEvidentLedger | None = None

    def __init__(self) -> None:
        self._events: dict[str, list[AuditRecord]] = {}
        self._auto_id: int = 1

    @classmethod
    def get_instance(cls) -> TamperEvidentLedger:
        if cls._instance is None:
            cls._instance = TamperEvidentLedger()
        return cls._instance

    def append(
        self, session_id: str, actor: str, kind: str, payload: dict[str, Any]
    ) -> AuditRecord:
        records = self._events.setdefault(session_id, [])
        prev_hash = records[-1].hash if records else "0" * 64
        now_iso = datetime.now(timezone.utc).isoformat()
        body = json.dumps(
            {"s": session_id, "a": actor, "k": kind, "p": payload, "t": now_iso},
            sort_keys=True,
        )
        h = hashlib.sha256((prev_hash + body).encode("utf-8")).hexdigest()
        record = AuditRecord(
            id=self._auto_id,
            session_id=session_id,
            actor=actor,
            kind=kind,
            payload=payload,
            prev_hash=prev_hash,
            hash=h,
            created_at=now_iso,
        )
        self._auto_id += 1
        records.append(record)
        return record

    def get_events(self, session_id: str) -> list[dict[str, Any]]:
        return [asdict(record) for record in self._events.get(session_id, [])]

    def verify(self, session_id: str) -> tuple[bool, int | None, str]:
        records = self._events.get(session_id, [])
        if not records:
            return True, None, "Ledger is empty (valid)."

        prev_hash = "0" * 64
        for idx, record in enumerate(records):
            if record.prev_hash != prev_hash:
                return (
                    False,
                    record.id,
                    f"Chain broken at record #{record.id}: prev_hash mismatch.",
                )
            body = json.dumps(
                {
                    "s": record.session_id,
                    "a": record.actor,
                    "k": record.kind,
                    "p": record.payload,
                    "t": record.created_at,
                },
                sort_keys=True,
            )
            expected_hash = hashlib.sha256(
                (prev_hash + body).encode("utf-8")
            ).hexdigest()
            if record.hash != expected_hash:
                return (
                    False,
                    record.id,
                    f"Cryptographic hash invalid at record #{record.id}! Content was maliciously modified.",
                )
            prev_hash = record.hash

        return True, None, f"All {len(records)} audit records cryptographically verified."

    def simulate_tamper(
        self, session_id: str, target_id: int | None = None
    ) -> dict[str, Any]:
        """Tamper with a record's payload to demo fraud detection live to judges."""
        records = self._events.get(session_id, [])
        if not records:
            raise ValueError("No records to tamper with.")

        target = None
        if target_id is not None:
            for r in records:
                if r.id == target_id:
                    target = r
                    break
        if target is None:
            target = records[len(records) // 2]  # Tamper with middle record

        original_payload = dict(target.payload)
        # Malicious modification: change amount or status
        target.payload["TAMPERED_BY_ATTACKER"] = True
        if "approved_amount" in target.payload:
            target.payload["approved_amount"] = 999999
        if "amount" in target.payload:
            target.payload["amount"] = 999999

        return {
            "tampered_id": target.id,
            "original_payload": original_payload,
            "modified_payload": target.payload,
            "message": f"Record #{target.id} maliciously altered in memory. Run ledger verification to see cryptographic alert.",
        }

    def reset_session(self, session_id: str) -> None:
        if session_id in self._events:
            del self._events[session_id]

