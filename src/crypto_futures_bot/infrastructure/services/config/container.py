from dependency_injector import containers, providers

from crypto_futures_bot.infrastructure.services.tracked_crypto_currency_service import TrackedCryptoCurrencyService


class ServicesContainer(containers.DeclarativeContainer):
    configuration_properties = providers.Dependency()
    event_emitter = providers.Dependency()
    telegram_service = providers.Dependency()
    database_sessionmaker = providers.Dependency()
    futures_exchange_service = providers.Dependency()

    tracked_crypto_currency_service = providers.Singleton(
        TrackedCryptoCurrencyService, futures_exchange_service=futures_exchange_service
    )
