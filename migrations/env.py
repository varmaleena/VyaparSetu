"""Run migrations against the configured database."""

from alembic import context

from app.config.settings import get_settings
from app.services.database_service import create_database_engine

if context.is_offline_mode():
    context.configure(url=get_settings().database_url, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_database_engine()
    try:
        with engine.connect() as connection:
            context.configure(connection=connection)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()
