from dependency_injector import containers, providers

from crypto_futures_bot.infrastructure.services.crypto_technical_analysis_service import CryptoTechnicalAnalysisService
from crypto_futures_bot.infrastructure.services.market_signal_service import MarketSignalService
from crypto_futures_bot.infrastructure.services.orders_analytics_service import OrdersAnalyticsService
from crypto_futures_bot.infrastructure.services.push_notification_service import PushNotificationService
from crypto_futures_bot.infrastructure.services.tracked_crypto_currency_service import TrackedCryptoCurrencyService
from crypto_futures_bot.infrastructure.services.trade_now_service import TradeNowService


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
        CryptoTechnicalAnalysisService,
        tracked_crypto_currency_service=tracked_crypto_currency_service,
        futures_exchange_service=futures_exchange_service,
    )
    push_notification_service = providers.Singleton(
        PushNotificationService, configuration_properties=configuration_properties
    )
    orders_analytics_service = providers.Singleton(
        OrdersAnalyticsService,
        configuration_properties=configuration_properties,
        futures_exchange_service=futures_exchange_service,
        push_notification_service=push_notification_service,
        telegram_service=telegram_service,
    )
    trade_now_service = providers.Singleton(
        TradeNowService,
        futures_exchange_service=futures_exchange_service,
        crypto_technical_analysis_service=crypto_technical_analysis_service,
        orders_analytics_service=orders_analytics_service,
    )
    market_signal_service = providers.Singleton(
        MarketSignalService,
        event_emitter=event_emitter,
        push_notification_service=push_notification_service,
        telegram_service=telegram_service,
    )
