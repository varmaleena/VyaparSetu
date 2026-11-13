from datetime import date, timedelta
from unittest.mock import Mock

import pytest
from google.adk.events import Event, EventActions
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.workflow import Workflow
from google.genai import types

from app.agents.repayment_monitoring_agent import build_repayment_monitoring_workflow
from app.models.payment import SimulatedPayment
from app.services.payment_proposals import PaymentProposals
from app.services.settlement_repository import SettlementRepository


@pytest.mark.parametrize(
    ("installments", "history_amount", "status", "shortfall"),
    [
        ([100, 100], 1_000, "ON_TRACK", 0),
        ([100, 100], 500, "PROJECTED_SHORTFALL", 70),
        ([100, 100], None, "UNKNOWN", None),
        ([], None, "NO_INSTALLMENTS", None),
    ],
)
def test_repayment_monitoring(installments, history_amount, status, shortfall):
    day = date(2026, 11, 13)
    proposals = Mock(spec=PaymentProposals)
    proposals.confirmed_receipt.return_value = SimulatedPayment(
        proposal_id="proposal",
        status="SIMULATED_PAID",
        installments_paise=installments,
        scheduled_from=day,
    )
    settlements = Mock(spec=SettlementRepository)
    settlements.history.return_value = (
        {day - timedelta(days=i): history_amount for i in range(1, 57)}
        if history_amount is not None
        else {},
        10,
    )

    async def start(ctx):
        yield Event(output={"proposal_id": "proposal"}, actions=EventActions())

    agent = Workflow(
        name="test_repayment",
        edges=[
            (
                "START",
                start,
                build_repayment_monitoring_workflow(
                    proposals, settlements, "merchant", lambda: day, 1500
                ),
            )
        ],
    )
    sessions = InMemorySessionService()
    session = sessions.create_session_sync(app_name="test", user_id="user")
    runner = Runner(agent=agent, session_service=sessions, app_name="test")
    events = list(
        runner.run(
            user_id="user",
            session_id=session.id,
            new_message=types.UserContent(parts=[types.Part(text="repayment-status")]),
        )
    )
    result = next(
        event.actions.state_delta["repayment_monitoring"]
        for event in events
        if "repayment_monitoring" in event.actions.state_delta
    )
    proposals.confirmed_receipt.assert_called_once_with(
        "merchant", session.id, "proposal"
    )
    assert result["status"] == status
    assert result.get("projected_shortfall_paise") == shortfall
    if installments:
        assert result["next_date"] == (day + timedelta(days=1)).isoformat()
        assert result["next_paise"] == 100
        assert result["upcoming_paise"] == 200
    else:
        settlements.history.assert_not_called()
