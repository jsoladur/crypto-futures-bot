import asyncio
import logging
from typing import override

from pyee.asyncio import AsyncIOEventEmitter

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.constants import MARKET_SIGNAL_EVENT_NAME
from crypto_futures_bot.domain.vo import MarketSignalItem
from crypto_futures_bot.infrastructure.services.base import AbstractEventHandlerService
from crypto_futures_bot.infrastructure.services.push_notification_service import PushNotificationService
from crypto_futures_bot.infrastructure.services.trade_now_service import TradeNowService
from crypto_futures_bot.interfaces.telegram.services.telegram_service import TelegramService

logger = logging.getLogger(__name__)


class AutoTraderEventHandlerService(AbstractEventHandlerService):
    def __init__(
        self,
        configuration_properties: ConfigurationProperties,
        push_notification_service: PushNotificationService,
        telegram_service: TelegramService,
        event_emitter: AsyncIOEventEmitter,
        trade_now_service: TradeNowService,
    ) -> None:
        super().__init__(push_notification_service, telegram_service, event_emitter)
        self._configuration_properties = configuration_properties
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
        raise NotImplementedError("To be implemented!")
