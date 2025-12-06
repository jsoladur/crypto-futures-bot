from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.infrastructure.database.alembic import run_migrations_async


async def init_database(config: ConfigurationProperties) -> AsyncEngine:
    """
    Initialize the database: run migrations and create the async engine.
    """
    await run_migrations_async(config)

    engine = create_async_engine(str(config.database_url), echo=False)
    return engine
