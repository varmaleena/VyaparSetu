"""SQLAlchemy connection factory for local persistence commands."""

import logging
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.config.settings import get_settings

logger = logging.getLogger(__name__)

_CACHED_ENGINE: Engine | None = None


def create_database_engine() -> Engine:
    global _CACHED_ENGINE
    if _CACHED_ENGINE is not None:
        return _CACHED_ENGINE

    url = get_settings().database_url
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            pass
        _CACHED_ENGINE = engine
        return engine
    except Exception as exc:
        logger.info(
            "Primary database (%s) unavailable. Using robust local SQLite engine for demo/sandbox.",
            url,
        )
        _CACHED_ENGINE = create_engine(
            "sqlite:///./vyaparsetu_local.db",
            connect_args={"check_same_thread": False},
        )
        return _CACHED_ENGINE
