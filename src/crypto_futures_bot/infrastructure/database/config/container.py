import logging

from dependency_injector import containers, providers

from crypto_futures_bot.infrastructure.database.config.dependencies import init_sessionmaker

logger = logging.getLogger(__name__)


class DatabaseContainer(containers.DeclarativeContainer):
    configuration_properties = providers.Dependency()

    sessionmaker = providers.Resource(init_sessionmaker, configuration_properties=configuration_properties)
