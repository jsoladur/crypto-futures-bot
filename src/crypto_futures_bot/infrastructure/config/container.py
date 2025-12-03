from dependency_injector import containers, providers
from pyee.asyncio import AsyncIOEventEmitter


class InfrastructureContainer(containers.DeclarativeContainer):
    configuration_properties = providers.Dependency()

    event_emitter = providers.Singleton(AsyncIOEventEmitter)
