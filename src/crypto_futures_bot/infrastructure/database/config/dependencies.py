import logging

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties

logger = logging.getLogger(__name__)


def init_sessionmaker(configuration_properties: ConfigurationProperties) -> async_sessionmaker:
    """
    Initialize the database: create the async engine.
    """
    engine = create_async_engine(str(configuration_properties.database_url), echo=False)
    sessionmaker = async_sessionmaker(bind=engine)
    yield sessionmaker
    engine.dispose()
