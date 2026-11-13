from datetime import date
from unittest.mock import Mock
from uuid import uuid4

import pytest
from google.adk.events import Event
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.workflow import FunctionNode, Workflow
from google.genai import types

from app.agents.playground_payment_review import build_payment_review
from app.models.invoice import ExtractedInvoice
from app.models.payment import SimulatedPayment
from app.services.payment_proposals import PaymentProposals


@pytest.mark.asyncio
async def test_review_routes_offer_and_requires_exact_payment_consent():
    day = date(2026, 11, 13)
    intake_id, proposal_id = str(uuid4()), str(uuid4())
    store = Mock(spec=PaymentProposals)
    store.execute.return_value = SimulatedPayment(
        proposal_id=proposal_id, status="SIMULATED_PAID", installments_paise=[]
    )
    node = FunctionNode(
        func=build_payment_review(store, "merchant", lambda: day, 500),
        name="merchant_payment_review",
    )

    async def invoice(ctx):
        yield Event()

    async def compare(ctx, node_input: dict):
        assert node_input["confirmed_invoice"]["discount"]["amount_paise"] == 120_000
        assert ctx.state["invoice_structured"]["discount"] is None
        yield Event(content=types.ModelContent(parts=[types.Part(text="Compared")]))

    graph = Workflow(
        name="review_test",
        edges=[
            ("START", node),
            (node, {"invoice": invoice, "offer": compare}),
            (invoice, compare),
        ],
    )
    sessions = InMemorySessionService()
    session = await sessions.create_session(
        app_name="test",
        user_id="user",
        state={
            "invoice_intake_result": {"intake_id": intake_id},
            "repayment_capacity": {
                "as_of": day.isoformat(),
                "status": "CAPACITY_AVAILABLE",
            },
            "invoice_structured": ExtractedInvoice(
                supplier_name="Supplier",
                supplier_gstin=None,
                invoice_number="7",
                invoice_date=day,
                due_date=day,
                currency="INR",
                lines=[],
                total_paise=4_000_000,
                tax_added_paise=0,
                adjustment_paise=0,
                discount_status="none",
                discount=None,
            ).model_dump(mode="json"),
        },
    )
    runner = Runner(agent=graph, session_service=sessions, app_name="test")

    async def run(message):
        return [
            part.text
            async for event in runner.run_async(
                user_id="user",
                session_id=session.id,
                new_message=types.UserContent(parts=[types.Part(text=message)]),
            )
            if event.content
            for part in event.content.parts or []
            if part.text
        ]

    assert "Compared" in await run(f"confirm-offer {intake_id} 120000 {day}")
    assert (
        "Review the payment proposal"
        in (await run(f"confirm-payment {proposal_id}"))[0]
    )
    store.execute.assert_not_called()

    from google.adk.events import EventActions

    await sessions.append_event(
        session,
        Event(
            author="review_test",
            actions=EventActions(
                state_delta={
                    "payment_proposal": {
                        "terms": {"id": proposal_id},
                        "terms_digest": "a" * 64,
                    }
                }
            ),
        ),
    )
    await run("yes")
    store.execute.assert_not_called()
    assert (
        "Simulated payment recorded" in (await run(f"confirm-payment {proposal_id}"))[0]
    )
    assert store.execute.call_args.kwargs["session"] == session.id
