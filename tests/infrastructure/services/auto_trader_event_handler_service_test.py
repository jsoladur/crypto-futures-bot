import asyncio
import logging
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from dependency_injector.containers import Container
from faker import Faker
from pyee.asyncio import AsyncIOEventEmitter

from crypto_futures_bot.constants import MARKET_SIGNAL_EVENT_NAME
from crypto_futures_bot.domain.enums import (
    MarketActionTypeEnum,
    OpenPositionResultTypeEnum,
    PositionTypeEnum,
    PushNotificationTypeEnum,
)
from crypto_futures_bot.domain.vo import MarketSignalItem, OpenPositionResult, TrackedCryptoCurrencyItem
from crypto_futures_bot.infrastructure.services.auto_trader_crypto_currency_service import (
    AutoTraderCryptoCurrencyService,
)
from crypto_futures_bot.infrastructure.services.auto_trader_event_handler_service import AutoTraderEventHandlerService
from crypto_futures_bot.infrastructure.services.push_notification_service import PushNotificationService
from crypto_futures_bot.infrastructure.services.tracked_crypto_currency_service import TrackedCryptoCurrencyService
from crypto_futures_bot.infrastructure.services.trade_now_service import TradeNowService
from crypto_futures_bot.interfaces.telegram.services.telegram_service import TelegramService
from tests.helpers.constants import MOCK_CRYPTO_CURRENCIES

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def should_open_a_position_when_a_market_signal_is_received_and_the_crypto_is_enabled_for_auto_trading(
    faker: Faker, test_environment: tuple[Container, ...]
) -> None:
    application_container, *_ = test_environment

    event_emitter: AsyncIOEventEmitter = application_container.infrastructure_container().event_emitter()
    auto_trader_crypto_currency_service: AutoTraderCryptoCurrencyService = (
        application_container.infrastructure_container().services_container().auto_trader_crypto_currency_service()
    )
    tracked_crypto_currency_service: TrackedCryptoCurrencyService = (
        application_container.infrastructure_container().services_container().tracked_crypto_currency_service()
    )
    trade_now_service: TradeNowService = (
        application_container.infrastructure_container().services_container().trade_now_service()
    )
    telegram_service: TelegramService = (
        application_container.interfaces_container().telegram_container().telegram_service()
    )
    push_notification_service: PushNotificationService = (
        application_container.infrastructure_container().services_container().push_notification_service()
    )

    # Configure the event handler to listen for events
    auto_trader_event_handler_service: AutoTraderEventHandlerService = (
        application_container.infrastructure_container().services_container().auto_trader_event_handler_service()
    )
    auto_trader_event_handler_service.configure()

    currency_str = faker.random_element(MOCK_CRYPTO_CURRENCIES)
    crypto_currency = TrackedCryptoCurrencyItem(currency=currency_str)
    position_type = PositionTypeEnum.LONG

    open_position_result = OpenPositionResult(
        result_type=OpenPositionResultTypeEnum.SUCCESS, crypto_currency=crypto_currency, position_type=position_type
    )
    mock_open_position = AsyncMock(return_value=open_position_result)
    mock_send_message = AsyncMock()

    messages_formatter = auto_trader_event_handler_service._messages_formatter

    with (
        patch.object(trade_now_service, "open_position", mock_open_position),
        patch.object(telegram_service, "send_message", mock_send_message),
        patch.object(messages_formatter, "format_open_position_result", return_value="Mocked message"),
    ):
        await tracked_crypto_currency_service.add(currency_str)
        await auto_trader_crypto_currency_service.toggle_for(currency_str)

        # Activate push notifications for trades for a random user
        chat_id = faker.pystr()
        await push_notification_service.toggle_push_notification_by_type(chat_id, PushNotificationTypeEnum.TRADES)

        market_signal = MarketSignalItem(
            timestamp=datetime.now(UTC),
            crypto_currency=crypto_currency,
            timeframe="1h",
            position_type=position_type,
            action_type=MarketActionTypeEnum.ENTRY,
            entry_price=faker.pyfloat(),
            break_even_price=faker.pyfloat(),
            stop_loss_percent_value=faker.pyfloat(min_value=0.1, max_value=0.5),
            take_profit_percent_value=faker.pyfloat(min_value=0.1, max_value=0.5),
            stop_loss_price=faker.pyfloat(),
            take_profit_price=faker.pyfloat(),
        )
        event_emitter.emit(MARKET_SIGNAL_EVENT_NAME, market_signal)

        # Give some time for the event to be processed
        await asyncio.sleep(0.1)

        mock_open_position.assert_called_once_with(
            crypto_currency=market_signal.crypto_currency, position_type=market_signal.position_type
        )
        mock_send_message.assert_called_once()

        await tracked_crypto_currency_service.remove(currency_str)
        await auto_trader_crypto_currency_service.toggle_for(currency_str)  # Deactivate again
        await push_notification_service.toggle_push_notification_by_type(
            chat_id, PushNotificationTypeEnum.TRADES
        )  # Deactivate again
