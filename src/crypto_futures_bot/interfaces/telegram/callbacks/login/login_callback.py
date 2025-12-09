import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from crypto_futures_bot.config.dependencies import get_application_container
from crypto_futures_bot.interfaces.telegram.callbacks.login.login_form import LoginForm
from crypto_futures_bot.interfaces.telegram.services.session_storage_service import SessionStorageService
from crypto_futures_bot.interfaces.telegram.services.telegram_service import TelegramService

logger = logging.getLogger(__name__)

application_container = get_application_container()
dp: Dispatcher = application_container.interfaces_container().telegram_container().dispatcher()
bot: Bot = application_container.interfaces_container().telegram_container().telegram_bot()
telegram_service: TelegramService = application_container.interfaces_container().telegram_container().telegram_service()
session_storage_service: SessionStorageService = (
    application_container.interfaces_container().telegram_container().session_storage_service()
)


@LoginForm.submit(router=dp)
async def login_form_submit_handler(form: LoginForm, state: FSMContext) -> None:
    try:
        await telegram_service.perform_successful_login(state=state, login=form)
    except Exception as e:
        logger.error(f"Failed to perform login: {e}")


@dp.callback_query(lambda c: c.data == "login")
async def login_callback_handler(callback_query: CallbackQuery, state: FSMContext) -> None:
    await LoginForm.start(bot, state)
