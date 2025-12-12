from unittest.mock import MagicMock

from dependency_injector import containers, providers

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.infrastructure.adapters.futures_exchange.impl.mexc_futures_exchange import (
    MEXCFuturesExchangeService,
)
from crypto_futures_bot.infrastructure.services.crypto_technical_analysis_service import CryptoTechnicalAnalysisService
from crypto_futures_bot.infrastructure.services.orders_analytics_service import OrdersAnalyticsService
from crypto_futures_bot.infrastructure.tasks.signals_task_service import SignalsTaskService
from crypto_futures_bot.scripts.services import BacktestingService


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(modules=["crypto_futures_bot.scripts.cli"])

    config = providers.Singleton(ConfigurationProperties)

    # Mocks
    telegram_service_mock = providers.Object(MagicMock())
    push_notification_service_mock = providers.Object(MagicMock())
    event_emitter_mock = providers.Object(MagicMock())
    scheduler_mock = providers.Object(MagicMock())
    tracked_crypto_currency_service_mock = providers.Object(MagicMock())

    # Services
    futures_exchange_service = providers.Singleton(MEXCFuturesExchangeService, configuration_properties=config)

    crypto_technical_analysis_service = providers.Singleton(
        CryptoTechnicalAnalysisService,
        tracked_crypto_currency_service=tracked_crypto_currency_service_mock,
        futures_exchange_service=futures_exchange_service,
    )

    orders_analytics_service = providers.Singleton(
        OrdersAnalyticsService,
        configuration_properties=config,
        push_notification_service=push_notification_service_mock,
        telegram_service=telegram_service_mock,
    )

    signals_task_service = providers.Singleton(
        SignalsTaskService,
        configuration_properties=config,
        telegram_service=telegram_service_mock,
        push_notification_service=push_notification_service_mock,
        event_emitter=event_emitter_mock,
        scheduler=scheduler_mock,
        tracked_crypto_currency_service=tracked_crypto_currency_service_mock,
        futures_exchange_service=futures_exchange_service,
        orders_analytics_service=orders_analytics_service,
        crypto_technical_analysis_service=crypto_technical_analysis_service,
    )

    backtesting_service = providers.Singleton(
        BacktestingService,
        configuration_properties=config,
        futures_exchange_service=futures_exchange_service,
        crypto_technical_analysis_service=crypto_technical_analysis_service,
        orders_analytics_service=orders_analytics_service,
        signals_task_service=signals_task_service,
    )
