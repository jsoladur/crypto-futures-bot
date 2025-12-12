from dependency_injector import containers, providers

from crypto_futures_bot.infrastructure.services.crypto_technical_analysis_service import CryptoTechnicalAnalysisService
from crypto_futures_bot.infrastructure.services.orders_analytics_service import OrdersAnalyticsService
from crypto_futures_bot.infrastructure.services.push_notification_service import PushNotificationService
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
    crypto_technical_analysis_service = providers.Singleton(
        CryptoTechnicalAnalysisService, futures_exchange_service=futures_exchange_service
    )
    push_notification_service = providers.Singleton(
        PushNotificationService, configuration_properties=configuration_properties
    )
    orders_analytics_service = providers.Singleton(
        OrdersAnalyticsService,
        configuration_properties=configuration_properties,
        push_notification_service=push_notification_service,
        telegram_service=telegram_service,
    )
