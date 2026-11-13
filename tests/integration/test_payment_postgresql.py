"""Verify the consent transaction against a migrated PostgreSQL database."""

import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from unittest.mock import Mock
from uuid import uuid4

import pytest
import sqlalchemy as sa
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.workflow import FunctionNode, Workflow
from google.genai import types

from app.agents.playground_payment_review import build_payment_review
from app.models.decision import PaymentDecision, PaymentEconomics, PaymentOption
from app.models.payment import PaymentConsent
from app.services import payment_proposals as payments
from app.services.database_service import create_database_engine
from app.services.invoice_repository import intakes


@pytest.mark.skipif(
    os.getenv("VYAPARSETU_TEST_POSTGRES") != "1",
    reason="requires migrated development PostgreSQL",
)
@pytest.mark.parametrize(
    "scenario", ["concurrent", "changed_payee", "simulator_failure"]
)
def test_payment_confirmation(scenario, monkeypatch):
    engine = create_database_engine()
    store = payments.PaymentProposals(engine)
    merchant, supplier, intake, session = (str(uuid4()) for _ in range(4))
    day = date(2026, 11, 13)
    option = PaymentOption(
        method="FINANCING",
        principal=9_000,
        cost=100,
        net_savings=900,
        repayment_total=9_100,
        daily_installment=3_034,
    )
    decision = PaymentDecision(
        status="FINANCING_FITS",
        code="TEST",
        selected=option,
        economics=PaymentEconomics(
            code="OPTIONS_COMPARED",
            due_date=day,
            invoice_total=10_000,
            early_amount=9_000,
            discount=1_000,
            discount_deadline=day,
            tenor_days=3,
            daily_cap=3_034,
            options=[option],
        ),
    )
    try:
        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    "INSERT INTO merchants (id, name, language, available_cash, existing_edi_daily) "
                    "VALUES (:id, 'Payment test merchant', 'en', 0, 0)"
                ),
                {"id": merchant},
            )
            connection.execute(
                sa.text(
                    "INSERT INTO suppliers (id, name, gstin, account_token, registry_status, "
                    "payout_account_name, payout_last4, payout_verified) VALUES "
                    "(:id, 'Payment test supplier', :id, 'original', 'ACTIVE', "
                    "'Payment test supplier', '4200', true)"
                ),
                {"id": supplier},
            )
            connection.execute(
                intakes.insert().values(
                    id=intake,
                    merchant_id=merchant,
                    session_id=session,
                    object_uri=f"gs://fixture-only/{intake}",
                    object_generation=1,
                    media_type="image/png",
                    size_bytes=1,
                    sha256=uuid4().hex * 2,
                )
            )
        created = store.create(
            merchant=merchant,
            session=session,
            intake=intake,
            supplier=supplier,
            masked_account="****4200",
            invoice_key=intake,
            decision=decision,
        )
        assert created is not None
        proposal, digest = created
        consent = PaymentConsent(terms_digest=digest, accepted=True)

        def confirm():
            return store.execute(merchant, proposal.id, consent, day, session=session)

        def persisted():
            with engine.connect() as connection:
                return connection.execute(
                    sa.select(
                        payments.proposals.c.consent_at, payments.proposals.c.receipt
                    ).where(payments.proposals.c.id == proposal.id)
                ).one()

        assert (
            store.execute(merchant, proposal.id, consent, day, session="other") is None
        )
        simulator = Mock(wraps=payments.simulate_payment)
        monkeypatch.setattr(payments, "simulate_payment", simulator)
        if scenario == "changed_payee":
            with engine.begin() as connection:
                connection.execute(
                    sa.text(
                        "UPDATE suppliers SET account_token='changed' WHERE id=:id"
                    ),
                    {"id": supplier},
                )
            with pytest.raises(
                payments.ProposalConflict, match="registered payee changed"
            ):
                confirm()
            assert persisted() == (None, None)
            simulator.assert_not_called()
            return
        if scenario == "simulator_failure":
            simulator.side_effect = ValueError("injected simulator failure")
            with pytest.raises(ValueError, match="injected simulator failure"):
                confirm()
            assert persisted() == (None, None)
            simulator.reset_mock(side_effect=True)
            receipt = confirm()
        else:
            start = Barrier(2)

            def simultaneous():
                start.wait(timeout=5)
                return confirm()

            with ThreadPoolExecutor(max_workers=2) as pool:
                requests = [pool.submit(simultaneous) for _ in range(2)]
                receipt, retry = (request.result(timeout=10) for request in requests)
            assert receipt == retry

        simulator.assert_called_once()
        assert receipt is not None
        assert receipt.installments_paise == [3_034, 3_034, 3_032]
        consent_at, saved = persisted()
        assert consent_at is not None
        assert saved == receipt.model_dump(mode="json")
        assert store.confirmed_receipt(merchant, session, proposal.id) == receipt
        assert store.confirmed_receipt(merchant, "other", proposal.id) is None

        if scenario == "concurrent":
            sessions = InMemorySessionService()
            sessions.create_session_sync(
                app_name="test",
                user_id=merchant,
                session_id=session,
                state={
                    "payment_proposal": {
                        "terms": proposal.model_dump(mode="json"),
                        "terms_digest": digest,
                    }
                },
            )
            review = FunctionNode(
                func=build_payment_review(store, merchant, lambda: day, 500),
                name="merchant_payment_review",
            )
            runner = Runner(
                agent=Workflow(name="payment_test", edges=[("START", review)]),
                app_name="test",
                session_service=sessions,
            )

            def send(text):
                return list(
                    runner.run(
                        user_id=merchant,
                        session_id=session,
                        new_message=types.UserContent(parts=[types.Part(text=text)]),
                    )
                )

            if (
                sys.platform == "win32"
                and os.getenv("VYAPARSETU_TEST_WINDOWS_AUDIO") == "1"
            ):
                audio_events = send("read-payment")
                assert any(
                    part.inline_data
                    and part.inline_data.mime_type == "audio/wav"
                    and part.inline_data.data.startswith(b"RIFF")
                    for event in audio_events
                    if event.content
                    for part in event.content.parts or []
                )
            assert any(
                event.actions.state_delta.get("simulated_payment_receipt") == saved
                for event in send(f"confirm-payment {proposal.id}")
            )
            simulator.assert_called_once()

    finally:
        with engine.begin() as connection:
            connection.execute(
                payments.proposals.delete().where(
                    payments.proposals.c.intake_id == intake
                )
            )
            connection.execute(intakes.delete().where(intakes.c.id == intake))
            connection.execute(
                sa.text("DELETE FROM suppliers WHERE id=:id"), {"id": supplier}
            )
            connection.execute(
                sa.text("DELETE FROM merchants WHERE id=:id"), {"id": merchant}
            )
        engine.dispose()
