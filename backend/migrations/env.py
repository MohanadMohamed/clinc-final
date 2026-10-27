from alembic import context

from app.core.config import Settings
from app.core.db import Base, build_engine
from app.models import appointment, auth, billing, patient, visit  # noqa: F401

connection = context.config.attributes.get("connection")
if connection is not None:
    # Local operator tooling supplies its validated target and outer transaction.
    # Normal CLI migrations still use the unchanged runtime Settings validation.
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
elif context.is_offline_mode():
    settings = Settings()
    url = (settings.migration_database_url or settings.database_url).get_secret_value()
    context.configure(url=url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    settings = Settings()
    url = (settings.migration_database_url or settings.database_url).get_secret_value()
    engine = build_engine(url)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=Base.metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()
