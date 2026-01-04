import logging
from collections.abc import Generator

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties

logger = logging.getLogger(__name__)


def init_sessionmaker(configuration_properties: ConfigurationProperties) -> Generator[async_sessionmaker]:
    """
    Initialize the database: create the async engine.
    """
    engine = create_async_engine(
        str(configuration_properties.database_url),
        echo=False,
        pool_size=1,
        max_overflow=0,
        connect_args={"check_same_thread": False, "timeout": configuration_properties.database_busy_timeout},
    )
    sessionmaker = async_sessionmaker(bind=engine)
    try:
        yield sessionmaker
    finally:
        # Ensure clean shutdown
        logger.debug("Disposing SQLite async engine")
        engine.dispose()
