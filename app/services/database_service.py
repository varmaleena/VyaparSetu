"""SQLAlchemy connection factory for local persistence commands."""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.config.settings import get_settings


def create_database_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True)
