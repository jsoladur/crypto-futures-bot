from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyMarkupUnion

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.interfaces.telegram.callbacks.login.login_form import LoginForm
from crypto_futures_bot.interfaces.telegram.services.session_storage_service import SessionStorageService
from crypto_futures_bot.interfaces.telegram.utils.keyboards_builder import KeyboardsBuilder


class TelegramService:
    def __init__(
        self,
        configuration_properties: ConfigurationProperties,
        telegram_bot: Bot,
        session_storage_service: SessionStorageService,
        keyboards_builder: KeyboardsBuilder,
    ) -> None:
        self._configuration_properties = configuration_properties
        self._telegram_bot = telegram_bot
        self._session_storage_service = session_storage_service
        self._keyboards_builder = keyboards_builder

    async def perform_successful_login(self, *, state: FSMContext, login: LoginForm) -> None:
        """Sets the user as logged in by storing their information in the session."""
        if (
            login.username != self._configuration_properties.root_user
            or login.password != self._configuration_properties.root_password
        ):
            await self.send_message(
                chat_id=state.key.chat_id,
                text="Username or password is incorrect! Try again!",
                reply_markup=self._keyboards_builder.get_login_keyboard(),
            )
        else:
            await self._session_storage_service.set_user_logged(state=state, userinfo=login.fields)
            await self.send_message(
                chat_id=state.key.chat_id,
                text="You have successfully logged in to Crypto Futures Bot.",
                reply_markup=self._keyboards_builder.get_home_keyboard(),
            )

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_to_message_id: int | None = None,
        reply_markup: ReplyMarkupUnion | None = None,
    ) -> None:
        """Sends a message to a specified Telegram chat."""
        await self._telegram_bot.send_message(
            chat_id=chat_id, text=text, reply_to_message_id=reply_to_message_id, reply_markup=reply_markup
        )
