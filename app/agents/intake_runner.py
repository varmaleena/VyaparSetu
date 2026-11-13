"""An isolated ADK runner for the independently tested intake cycle."""

from contextvars import ContextVar

from google.adk.apps import App
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.sessions.session import Session
from google.genai import types

from app.agents.invoice_workflow import InvoiceWorkflow
from app.models.invoice import InvoiceIntakeResult
from app.services.invoice_intake import InvoiceIntake
from app.tools.invoice_workflow_tools import build_intake_tool

APP_NAME = "vyaparsetu_intake"


class IntakeRunner:
    def __init__(self, service: InvoiceIntake) -> None:
        self.repository = service.repository
        self.content: ContextVar[bytes] = ContextVar("invoice_content", default=b"")
        self.sessions = InMemorySessionService()
        self.runner = Runner(
            app=App(
                name=APP_NAME,
                root_agent=InvoiceWorkflow(
                    build_intake_tool(service, content=self.content)
                ),
            ),
            session_service=self.sessions,
        )

    async def create_session(self, merchant_id: str) -> Session:
        return await self.sessions.create_session(
            app_name=APP_NAME, user_id=merchant_id
        )

    async def get_session(self, merchant_id: str, session_id: str) -> Session | None:
        return await self.sessions.get_session(
            app_name=APP_NAME, user_id=merchant_id, session_id=session_id
        )

    async def run(
        self, merchant_id: str, session_id: str, content: bytes
    ) -> InvoiceIntakeResult:
        token = self.content.set(content)
        result = None
        try:
            async for event in self.runner.run_async(
                user_id=merchant_id,
                session_id=session_id,
                new_message=types.Content(
                    role="user", parts=[types.Part(text="Submit invoice image")]
                ),
            ):
                if event.actions and (
                    value := event.actions.state_delta.get("invoice_intake_result")
                ):
                    result = InvoiceIntakeResult.model_validate(value)
        finally:
            self.content.reset(token)
        if result is None:
            raise RuntimeError("Invoice intake completed without a result")
        return result
