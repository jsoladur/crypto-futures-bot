import logging

from aiogram import Dispatcher, html
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, StartMode

from crypto_futures_bot.config.dependencies import get_application_container
from crypto_futures_bot.interfaces.telegram.callbacks.tracked_crypto_currencies.dialog import (
    TrackedCryptoCurrencyStates,
)
from crypto_futures_bot.interfaces.telegram.services.session_storage_service import SessionStorageService
from crypto_futures_bot.interfaces.telegram.utils.exceptions_utils import format_exception
from crypto_futures_bot.interfaces.telegram.utils.keyboards_builder import KeyboardsBuilder

logger = logging.getLogger(__name__)

application_container = get_application_container()
dp: Dispatcher = application_container.interfaces_container().telegram_container().dispatcher()
session_storage_service: SessionStorageService = (
    application_container.interfaces_container().telegram_container().session_storage_service()
)
keyboards_builder: KeyboardsBuilder = (
    application_container.interfaces_container().telegram_container().keyboards_builder()
)


@dp.callback_query(lambda c: c.data == "add_tracker_crypto_currency")
async def add_tracker_crypto_currency_callback_handler(
    callback_query: CallbackQuery, state: FSMContext, dialog_manager: DialogManager
) -> None:
    is_user_logged = await session_storage_service.is_user_logged(state)
    if is_user_logged:
        try:
            await dialog_manager.start(TrackedCryptoCurrencyStates.main, mode=StartMode.RESET_STACK)
        except Exception as e:
            logger.error(f"Error retrieving non favourites crypto currencies: {str(e)}", exc_info=True)
            await callback_query.message.answer(
                f"⚠️ An error occurred while retrieving non favourites crypto currencies. Please try again later:\n\n{html.code(format_exception(e))}"  # noqa: E501
            )
    else:
        await callback_query.message.answer(
            "⚠️ Please log in to operate with favourites crypto currencies.",
            reply_markup=keyboards_builder.get_login_keyboard(state),
        )
