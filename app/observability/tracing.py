"""Opt-in console export for local HTTP request spans."""

import sys

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor


def create_console_provider() -> TracerProvider:
    provider = TracerProvider(resource=Resource.create({"service.name": "vyaparsetu"}))
    provider.add_span_processor(
        SimpleSpanProcessor(ConsoleSpanExporter(out=sys.stdout))
    )
    return provider


def request_tracer(provider: TracerProvider | None) -> trace.Tracer:
    return trace.get_tracer("vyaparsetu.http", tracer_provider=provider)
