import logging

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.infrastructure.database.alembic import run_migrations_async

logger = logging.getLogger(__name__)


async def init_sessionmaker(configuration_properties: ConfigurationProperties) -> async_sessionmaker:
    """
    Initialize the database: run migrations and create the async engine.
    """
    await run_migrations_async(configuration_properties)
    engine = create_async_engine(str(configuration_properties.database_url), echo=False)
    sessionmaker = async_sessionmaker(bind=engine)
    return sessionmaker
