from crypto_trailing_stop.interfaces.telegram.config.telegram_container import TelegramContainer
from dependency_injector import containers, providers


class InterfacesContainer(containers.DeclarativeContainer):
    configuration_properties = providers.Dependency()

    telegram_container = providers.Container(TelegramContainer, configuration_properties=configuration_properties)
