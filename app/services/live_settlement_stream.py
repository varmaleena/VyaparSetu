"""Live settlement stream simulator with real-time EDI split and coverage monitoring."""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any


@dataclass
class SettlementEvent:
    event_id: str
    session_id: str
    day_number: int
    date_str: str
    inflow_amount: int
    edi_deduction: int
    merchant_payout: int
    remaining_edi: int
    projected_p20_collections: int
    coverage_ratio: float
    status: str
    alert: str | None


class LiveSettlementEngine:
    _instance: LiveSettlementEngine | None = None

    def __init__(self) -> None:
        self.active_simulations: dict[str, dict[str, Any]] = {}

    @classmethod
    def get_instance(cls) -> LiveSettlementEngine:
        if cls._instance is None:
            cls._instance = LiveSettlementEngine()
        return cls._instance

    def initialize_stream(
        self,
        session_id: str,
        total_loan_amount: int = 38800,
        daily_edi: int = 1953,
        tenor_days: int = 20,
        base_daily_inflow: int = 25000,
        stress_multiplier: float = 1.0,
    ) -> dict[str, Any]:
        """Set up active repayment simulation state."""
        state = {
            "session_id": session_id,
            "total_loan": total_loan_amount,
            "daily_edi": daily_edi,
            "tenor_days": tenor_days,
            "current_day": 0,
            "remaining_edi": total_loan_amount,
            "cumulative_collected_edi": 0,
            "cumulative_merchant_payout": 0,
            "base_inflow": base_daily_inflow,
            "stress_multiplier": stress_multiplier,
            "status": "ACTIVE_REPAYING",
            "events": [],
            "offers_paused": False,
            "shortfall_days": 0,
        }
        self.active_simulations[session_id] = state
        return state

    def set_stress_multiplier(
        self, session_id: str, multiplier: float
    ) -> dict[str, Any]:
        """Adjust sales drop multiplier (e.g. 0.7 for 30% drop)."""
        sim = self.active_simulations.get(session_id)
        if not sim:
            sim = self.initialize_stream(session_id)
        sim["stress_multiplier"] = max(0.1, min(1.5, multiplier))
        # Re-evaluate live coverage
        return self.get_current_status(session_id)

    def step_next_day(self, session_id: str) -> SettlementEvent:
        """Simulate incoming settlement event for the next business day."""
        sim = self.active_simulations.get(session_id)
        if not sim:
            sim = self.initialize_stream(session_id)

        sim["current_day"] += 1
        day_num = sim["current_day"]
        stress = sim["stress_multiplier"]
        base = sim["base_inflow"]

        # Realistic weekday variation + lognormal noise * stress
        weekday = (day_num - 1) % 7
        weekday_factor = 1.25 if weekday in (5, 6) else 0.95
        noise = random.uniform(0.92, 1.08)
        actual_inflow = int(base * weekday_factor * noise * stress)

        # EDI split logic
        daily_target = sim["daily_edi"]
        rem = sim["remaining_edi"]

        if rem <= 0:
            edi_deducted = 0
            merchant_share = actual_inflow
            sim["status"] = "CLOSED_REPAID"
            alert = None
        else:
            edi_deducted = min(rem, min(actual_inflow, daily_target))
            merchant_share = actual_inflow - edi_deducted
            sim["remaining_edi"] -= edi_deducted
            sim["cumulative_collected_edi"] += edi_deducted
            sim["cumulative_merchant_payout"] += merchant_share

            # Coverage ratio calculation: projected P20 over remaining days / remaining obligation
            remaining_days = max(1, sim["tenor_days"] - day_num)
            p20_daily = int(base * 0.74 * stress)
            projected_p20 = p20_daily * remaining_days

            if sim["remaining_edi"] > 0:
                coverage_ratio = round(projected_p20 / sim["remaining_edi"], 2)
            else:
                coverage_ratio = 5.0

            # Alert and policy trigger
            alert = None
            if coverage_ratio < 1.0:
                sim["shortfall_days"] += 1
                sim["offers_paused"] = True
                alert = (
                    f"⚠️ Live coverage ratio dropped to {coverage_ratio}x (< 1.0x). "
                    f"New financing offers automatically PAUSED to protect merchant cashflow."
                )
            elif coverage_ratio < 1.2:
                alert = f"⚡ Caution: Coverage ratio tight at {coverage_ratio}x. Monitoring daily inflows."
            else:
                sim["shortfall_days"] = 0
                sim["offers_paused"] = False

            if sim["remaining_edi"] <= 0:
                sim["status"] = "CLOSED_REPAID"
                alert = "🎉 Loan fully repaid through daily settlements! Supplier payment obligation cleared."

        today = (
            date(2026, 11, 12) + timedelta(days=day_num)
        ).isoformat()  # standard evaluation baseline
        evt = SettlementEvent(
            event_id=f"SETT_{session_id[:8]}_{day_num:02d}",
            session_id=session_id,
            day_number=day_num,
            date_str=today,
            inflow_amount=actual_inflow,
            edi_deduction=edi_deducted,
            merchant_payout=merchant_share,
            remaining_edi=sim["remaining_edi"],
            projected_p20_collections=int(base * 0.74 * stress * max(1, sim["tenor_days"] - day_num)),
            coverage_ratio=coverage_ratio if rem > 0 else 5.0,
            status=sim["status"],
            alert=alert,
        )
        sim["events"].append(asdict(evt))
        return evt

    def get_current_status(self, session_id: str) -> dict[str, Any]:
        sim = self.active_simulations.get(session_id)
        if not sim:
            sim = self.initialize_stream(session_id)
        return sim

