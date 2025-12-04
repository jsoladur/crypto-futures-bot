from dependency_injector import containers, providers

from crypto_futures_bot.interfaces.telegram.config.container import TelegramContainer


class InterfacesContainer(containers.DeclarativeContainer):
    configuration_properties = providers.Dependency()

    telegram_container = providers.Container(TelegramContainer, configuration_properties=configuration_properties)
