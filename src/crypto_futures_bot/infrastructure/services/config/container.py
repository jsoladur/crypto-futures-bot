from dependency_injector import containers, providers


class ServicesContainer(containers.DeclarativeContainer):
    configuration_properties = providers.Dependency()
    event_emitter = providers.Dependency()
    telegram_service = providers.Dependency()
