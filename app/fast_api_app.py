# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import contextlib
import os
from collections.abc import AsyncIterator

from a2a.server.tasks import InMemoryTaskStore
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.runners import Runner
from starlette.middleware.base import RequestResponseEndpoint

from app.api.invoice_routes import router as invoice_router
from app.api.routes import router
from app.app_utils import services
from app.app_utils.a2a import attach_a2a_routes
from app.config.settings import get_settings
from app.observability.logging import log_request
from app.observability.tracing import create_console_provider, request_tracer

load_dotenv()
settings = get_settings()
allow_origins = [
    value.strip() for value in settings.allow_origins.split(",") if value.strip()
]

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from app.agent import app as adk_app
    from app.agent import root_agent

    runner = Runner(
        app=adk_app,
        session_service=services.get_session_service(),
        artifact_service=services.get_artifact_service(),
        auto_create_session=True,
    )
    app.state.runner = runner
    app.state.agent_app_name = adk_app.name
    await attach_a2a_routes(
        app,
        agent=root_agent,
        runner=runner,
        task_store=InMemoryTaskStore(),
        rpc_path=f"/a2a/{adk_app.name}",
    )
    console_provider = create_console_provider() if settings.otel_console else None
    app.state.request_tracer = request_tracer(console_provider)
    try:
        yield
    finally:
        if console_provider is not None:
            console_provider.shutdown()


app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=settings.adk_web,
    artifact_service_uri=services.ARTIFACT_SERVICE_URI,
    allow_origins=allow_origins or None,
    session_service_uri=services.SESSION_SERVICE_URI,
    otel_to_cloud=settings.otel_to_cloud,
    lifespan=lifespan,
)
app.include_router(router)
app.include_router(invoice_router)
app.title = "vyaparsetu"
app.description = "API for interacting with the Agent vyaparsetu"


@app.middleware("http")
async def observe_request(
    request: Request, call_next: RequestResponseEndpoint
) -> Response:
    tracer = request.app.state.request_tracer
    status = 500
    with tracer.start_as_current_span("vyaparsetu.http.request") as span:
        span.set_attribute("http.request.method", request.method)
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            span.set_attribute("http.response.status_code", status)
            context = span.get_span_context()
            trace_id = f"{context.trace_id:032x}" if context.is_valid else None
            log_request(request.method, status, trace_id)


# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
