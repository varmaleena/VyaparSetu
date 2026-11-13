"""Authenticate the single-merchant development intake endpoint."""

from hmac import compare_digest
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config.settings import get_settings

bearer = HTTPBearer(auto_error=False)


def get_intake_merchant(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> str:
    settings = get_settings()
    if settings.invoice_demo_token is None or not settings.invoice_bucket:
        raise HTTPException(503, "Invoice intake is not configured.")
    expected = settings.invoice_demo_token.get_secret_value().encode()
    if credentials is None or not compare_digest(
        credentials.credentials.encode(), expected
    ):
        raise HTTPException(
            401, "Invalid intake credentials.", headers={"WWW-Authenticate": "Bearer"}
        )
    return settings.invoice_demo_merchant_id
