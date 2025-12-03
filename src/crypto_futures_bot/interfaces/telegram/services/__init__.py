from aiogram import Bot
from aiogram.types import ReplyMarkupUnion
from crypto_futures_bot.infrastructure.services.session_storage_service import SessionStorageService


class TelegramService:
    def __init__(self, telegram_bot: Bot, session_storage_service: SessionStorageService) -> None:
        self._telegram_bot = telegram_bot
        self._session_storage_service = session_storage_service

    async def send_message(
        self,
        chat_id: str | None,
        text: str,
        *,
        reply_to_message_id: int | None = None,
        reply_markup: ReplyMarkupUnion | None = None,
    ) -> None:
        """Sends a message to a specified Telegram chat."""
        await self._telegram_bot.send_message(
            chat_id=chat_id, text=text, reply_to_message_id=reply_to_message_id, reply_markup=reply_markup
        )
