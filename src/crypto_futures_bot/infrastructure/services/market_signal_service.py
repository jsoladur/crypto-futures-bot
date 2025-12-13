import logging
from asyncio import Lock
from typing import override

from pyee.asyncio import AsyncIOEventEmitter

from crypto_futures_bot.constants import SIGNALS_EVALUATION_RESULT_EVENT_NAME
from crypto_futures_bot.domain.vo import SignalsEvaluationResult
from crypto_futures_bot.infrastructure.services.base import AbstractEventHandlerService
from crypto_futures_bot.infrastructure.services.push_notification_service import PushNotificationService
from crypto_futures_bot.infrastructure.services.trade_now_service import TradeNowService
from crypto_futures_bot.interfaces.telegram.services.telegram_service import TelegramService

logger = logging.getLogger(__name__)


class MarketSignalService(AbstractEventHandlerService):
    def __init__(
        self,
        push_notification_service: PushNotificationService,
        telegram_service: TelegramService,
        event_emitter: AsyncIOEventEmitter,
        trade_now_service: TradeNowService,
    ) -> None:
        super().__init__(push_notification_service, telegram_service, event_emitter)
        self._trade_now_service = trade_now_service
        self._lock = Lock()

    @override
    def configure(self) -> None:
        self._event_emitter.add_listener(SIGNALS_EVALUATION_RESULT_EVENT_NAME, self.handle_signals_evaluation_result)

    async def handle_signals_evaluation_result(self, signals_evaluation_result: SignalsEvaluationResult) -> None:
        async with self._lock:
            trade_now_hints = await self._trade_now_service.get_trade_now_hints(
                signals_evaluation_result.crypto_currency
            )
            logger.info(trade_now_hints)
