from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from app.core.config import Settings
from app.db.base import Base
from app.db.models import (  # noqa: F401 -- registra os modelos no metadata
    MemberModel,
    SessionModel,
    UserModel,
)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_with_connection(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(
        url=Settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
elif config.attributes.get("connection") is not None:
    run_with_connection(config.attributes["connection"])
else:
    engine = create_engine(Settings().database_url)
    try:
        with engine.connect() as connection:
            run_with_connection(connection)
    finally:
        engine.dispose()
