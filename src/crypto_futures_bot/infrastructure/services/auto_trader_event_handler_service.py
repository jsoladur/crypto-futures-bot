import asyncio
import logging
from typing import override

from pyee.asyncio import AsyncIOEventEmitter

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.constants import MARKET_SIGNAL_EVENT_NAME
from crypto_futures_bot.domain.enums import PushNotificationTypeEnum
from crypto_futures_bot.domain.vo import MarketSignalItem
from crypto_futures_bot.infrastructure.services.auto_trader_crypto_currency_service import (
    AutoTraderCryptoCurrencyService,
)
from crypto_futures_bot.infrastructure.services.base import AbstractEventHandlerService
from crypto_futures_bot.infrastructure.services.push_notification_service import PushNotificationService
from crypto_futures_bot.infrastructure.services.trade_now_service import TradeNowService
from crypto_futures_bot.interfaces.telegram.services.telegram_service import TelegramService
from crypto_futures_bot.interfaces.telegram.utils.messages_formatter import MessagesFormatter

logger = logging.getLogger(__name__)


class AutoTraderEventHandlerService(AbstractEventHandlerService):
    def __init__(
        self,
        configuration_properties: ConfigurationProperties,
        push_notification_service: PushNotificationService,
        telegram_service: TelegramService,
        messages_formatter: MessagesFormatter,
        event_emitter: AsyncIOEventEmitter,
        auto_trader_crypto_currency_service: AutoTraderCryptoCurrencyService,
        trade_now_service: TradeNowService,
    ) -> None:
        super().__init__(push_notification_service, telegram_service, event_emitter)
        self._configuration_properties = configuration_properties
        self._messages_formatter = messages_formatter
        self._auto_trader_crypto_currency_service = auto_trader_crypto_currency_service
        self._trade_now_service = trade_now_service
        self._lock = asyncio.Lock()

    @override
    def configure(self) -> None:
        self._event_emitter.add_listener(MARKET_SIGNAL_EVENT_NAME, self._handle_market_signal)

    async def _handle_market_signal(self, market_signal_item: MarketSignalItem) -> None:
        async with self._lock:
            try:
                await self._internal_handle_market_signal(market_signal_item)
            except Exception as e:  # pragma: no cover
                logger.error(str(e), exc_info=True)
                await self._notify_fatal_error_via_telegram(e)

    async def _internal_handle_market_signal(self, market_signal_item: MarketSignalItem) -> None:
        is_enabled_for = await self._auto_trader_crypto_currency_service.is_enabled_for(
            market_signal_item.crypto_currency.currency
        )
        if is_enabled_for:
            open_position_result = await self._trade_now_service.open_position(
                crypto_currency=market_signal_item.crypto_currency, position_type=market_signal_item.position_type
            )
            chat_ids = await self._push_notification_service.get_actived_subscription_by_type(
                notification_type=PushNotificationTypeEnum.TRADES
            )
            answer_text = self._messages_formatter.format_open_position_result(open_position_result)
            await self._notify_alert(telegram_chat_ids=chat_ids, body_message=answer_text)

    async def _notify_alert(self, telegram_chat_ids: list[str], body_message: str) -> None:
        await asyncio.gather(
            *[
                self._telegram_service.send_message(chat_id=tg_chat_id, text=body_message)
                for tg_chat_id in telegram_chat_ids
            ]
        )
