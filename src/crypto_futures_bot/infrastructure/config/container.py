from dependency_injector import containers, providers
from pyee.asyncio import AsyncIOEventEmitter

from crypto_futures_bot.infrastructure.database.config.container import DatabaseContainer
from crypto_futures_bot.infrastructure.services.config.container import ServicesContainer
from crypto_futures_bot.infrastructure.tasks.config.container import TasksContainer


class InfrastructureContainer(containers.DeclarativeContainer):
    configuration_properties = providers.Dependency()
    telegram_service = providers.Dependency()

    event_emitter = providers.Singleton(AsyncIOEventEmitter)

    database_container = providers.Container(DatabaseContainer, configuration_properties=configuration_properties)

    services_container = providers.Container(
        ServicesContainer,
        configuration_properties=configuration_properties,
        database_sessionmaker=database_container.sessionmaker,
        event_emitter=event_emitter,
        telegram_service=telegram_service,
    )
    tasks_container = providers.Container(
        TasksContainer, configuration_properties=configuration_properties, event_emitter=event_emitter
    )
