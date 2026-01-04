import tomllib
from os import getcwd
from pathlib import Path

from dependency_injector import containers, providers

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.infrastructure.config.container import InfrastructureContainer
from crypto_futures_bot.interfaces.config.container import InterfacesContainer


class ApplicationContainer(containers.DeclarativeContainer):
    configuration_properties = providers.Singleton(ConfigurationProperties)

    @staticmethod
    def _project_version() -> str:
        pyproject_path = Path(getcwd()) / "pyproject.toml"
        with pyproject_path.open("rb") as f:
            pyproject = tomllib.load(f)
        ret = pyproject["project"]["version"]
        return ret

    application_version: str = providers.Callable(_project_version)

    interfaces_container = providers.Container(InterfacesContainer, configuration_properties=configuration_properties)
    infrastructure_container = providers.Container(
        InfrastructureContainer,
        configuration_properties=configuration_properties,
        telegram_service=interfaces_container.telegram_container.telegram_service,
        messages_formatter=interfaces_container.telegram_container.messages_formatter,
    )
