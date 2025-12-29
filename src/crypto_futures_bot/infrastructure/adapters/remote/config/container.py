from dependency_injector import containers, providers

from crypto_futures_bot.infrastructure.adapters.remote.mexc_remote_service import MEXCRemoteService


class RemoteServicesContainer(containers.DeclarativeContainer):
    configuration_properties = providers.Dependency()

    mexc_remote_service = providers.Singleton(MEXCRemoteService, configuration_properties=configuration_properties)
