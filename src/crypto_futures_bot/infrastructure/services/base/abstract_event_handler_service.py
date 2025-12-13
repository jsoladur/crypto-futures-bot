import logging
from abc import ABCMeta, abstractmethod

from pyee.asyncio import AsyncIOEventEmitter

from crypto_futures_bot.infrastructure.services.base.abstract_service import AbstractService
from crypto_futures_bot.infrastructure.services.push_notification_service import PushNotificationService
from crypto_futures_bot.interfaces.telegram.services.telegram_service import TelegramService

logger = logging.getLogger(__name__)


class AbstractEventHandlerService(AbstractService, metaclass=ABCMeta):
    def __init__(
        self,
        push_notification_service: PushNotificationService,
        telegram_service: TelegramService,
        event_emitter: AsyncIOEventEmitter,
    ) -> None:
        super().__init__(push_notification_service, telegram_service)
        self._event_emitter = event_emitter

    @abstractmethod
    def configure(self) -> None:
        """
        Configure event emitter handler
        """
