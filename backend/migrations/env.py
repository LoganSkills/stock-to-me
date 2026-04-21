from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

from app.models.models import Base
from app.core.config import get_settings

settings = get_settings()
config = context.config
config.set_main_option("database_url", settings.DATABASE_URL.replace("+asyncpg", ""))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("database_url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


if __name__ == "__main__":
    from alembic.config import AlembicConfig
    AlembicConfig("/home/ubuntu/stock-to-me/backend/alembic.ini").run_migrations()
