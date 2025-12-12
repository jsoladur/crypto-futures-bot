import asyncio
import logging
import math
from abc import ABC
from html import escape as html_escape

import pydash
from aiogram import html

from crypto_futures_bot.constants import TELEGRAM_REPLY_EXCEPTION_MESSAGE_MAX_LENGTH
from crypto_futures_bot.domain.enums import PushNotificationTypeEnum
from crypto_futures_bot.infrastructure.services.push_notification_service import PushNotificationService
from crypto_futures_bot.interfaces.telegram.services.telegram_service import TelegramService

logger = logging.getLogger(__name__)


class AbstractService(ABC):
    def __init__(self, push_notification_service: PushNotificationService, telegram_service: TelegramService) -> None:
        self._push_notification_service = push_notification_service
        self._telegram_service = telegram_service

    async def _notify_alert_by_type(self, notification_type: PushNotificationTypeEnum, message: str) -> None:
        chat_ids = await self._push_notification_service.get_actived_subscription_by_type(
            notification_type=notification_type
        )
        if chat_ids:
            await asyncio.gather(
                *[self._telegram_service.send_message(chat_id=tg_chat_id, text=message) for tg_chat_id in chat_ids]
            )

    async def _notify_fatal_error_via_telegram(self, e: Exception) -> None:
        exception_message = (
            pydash.truncate(str(e), length=TELEGRAM_REPLY_EXCEPTION_MESSAGE_MAX_LENGTH) if str(e) else ""
        )
        exception_text = f"{e.__class__.__name__} :: {exception_message}" if exception_message else e.__class__.__name__
        try:
            chat_ids = await self._push_notification_service.get_actived_subscription_by_type(
                notification_type=PushNotificationTypeEnum.FATAL_ERRORS
            )
            for chat_id in chat_ids:
                await self._telegram_service.send_message(
                    chat_id=chat_id,
                    text=f"⚠️ [{self.__class__.__name__}] FATAL ERROR occurred! "
                    + f"Error message:\n\n{html.code(html_escape(exception_text))}",
                )
        except Exception as e:
            logger.warning(f"Unexpected error, notifying fatal error via Telegram: {exception_text}", exc_info=True)

    def _floor_round(self, value: float, *, ndigits: int) -> float:
        factor = 10**ndigits
        return math.floor(value * factor) / factor
