"""Configuration for the local API and infrastructure commands."""

from datetime import date
from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", env_ignore_empty=True
    )

    database_url: str = (
        "postgresql+psycopg://vyaparsetu:vyaparsetu@127.0.0.1:5432/vyaparsetu"
    )
    redis_url: str = "redis://127.0.0.1:6379/0"
    allow_origins: str = ""
    adk_web: bool = False
    otel_to_cloud: bool = False
    otel_console: bool = False
    scenario_date: date | None = None
    repayment_share_bps: int = Field(default=1500, ge=0, le=10000)
    settlement_stress_bps: int = Field(default=3000, ge=0, le=10000)
    invoice_playground_enabled: bool = True
    invoice_bucket: str = "work-511514-vyaparsetu-invoices"
    invoice_demo_token: SecretStr | None = None
    invoice_demo_merchant_id: str = "demo-merchant-00"
    invoice_gemini_model: str = "gemini-2.5-flash"
    invoice_gemini_location: str = "global"
    pricing_po_tolerance_bps: int = Field(default=1000, ge=0, le=10_000)
    pricing_discount_review_bps: int = Field(default=500, ge=0, le=10_000)
    invoice_gcp_project: str = "work-511514"
    sarvam_api_key: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
