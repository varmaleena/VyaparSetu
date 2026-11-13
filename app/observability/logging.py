"""Structured request logs with trace correlation."""

import json
import logging

logger = logging.getLogger("uvicorn.error")


def log_request(method: str, status: int, trace_id: str | None) -> None:
    logger.info(
        json.dumps(
            {
                "event": "http_request",
                "method": method,
                "status": status,
                "trace_id": trace_id,
            }
        )
    )
