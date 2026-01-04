from dependency_injector import containers, providers

from crypto_futures_bot.infrastructure.adapters.futures_exchange.enums.futures_exchange_enum import FuturesExchangeEnum
from crypto_futures_bot.infrastructure.adapters.futures_exchange.impl.mexc_futures_exchange import (
    MEXCFuturesExchangeService,
)
from crypto_futures_bot.infrastructure.adapters.remote.config.container import RemoteServicesContainer


class AdaptersContainer(containers.DeclarativeContainer):
    configuration_properties = providers.Dependency()

    _remote_services_container = providers.Container(
        RemoteServicesContainer, configuration_properties=configuration_properties
    )
    _mexc_futures_exchange_service = providers.Singleton(
        MEXCFuturesExchangeService,
        configuration_properties=configuration_properties,
        mexc_remote_service=_remote_services_container.mexc_remote_service,
    )
    futures_exchange_service = providers.Selector(
        configuration_properties.provided.futures_exchange, **{FuturesExchangeEnum.MEXC: _mexc_futures_exchange_service}
    )
