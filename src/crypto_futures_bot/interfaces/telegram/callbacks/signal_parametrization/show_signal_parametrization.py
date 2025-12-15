import logging
import re

from aiogram import Dispatcher, F, html
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from crypto_futures_bot.config.dependencies import get_application_container
from crypto_futures_bot.infrastructure.services.signal_parametrization_service import SignalParametrizationService
from crypto_futures_bot.interfaces.telegram.services.session_storage_service import SessionStorageService
from crypto_futures_bot.interfaces.telegram.utils.exceptions_utils import format_exception
from crypto_futures_bot.interfaces.telegram.utils.keyboards_builder import KeyboardsBuilder
from crypto_futures_bot.interfaces.telegram.utils.messages_formatter import MessagesFormatter

logger = logging.getLogger(__name__)

application_container = get_application_container()
dp: Dispatcher = application_container.interfaces_container().telegram_container().dispatcher()
session_storage_service: SessionStorageService = (
    application_container.interfaces_container().telegram_container().session_storage_service()
)
keyboards_builder: KeyboardsBuilder = (
    application_container.interfaces_container().telegram_container().keyboards_builder()
)
messages_formatter: MessagesFormatter = (
    application_container.interfaces_container().telegram_container().messages_formatter()
)
signal_parametrization_service: SignalParametrizationService = (
    application_container.infrastructure_container().services_container().signal_parametrization_service()
)

REGEX = r"^show_signal_parametrization_\$_(.+)$"


@dp.callback_query(F.data.regexp(REGEX))
async def show_signal_parametrization_callback_handler(callback_query: CallbackQuery, state: FSMContext) -> None:
    is_user_logged = await session_storage_service.is_user_logged(state)
    if is_user_logged:
        try:
            match = re.match(REGEX, callback_query.data)
            crypto_currency = match.group(1)
            item = await signal_parametrization_service.find_by_crypto_currency(crypto_currency)
            signal_parametrization_formatted = messages_formatter.format_signal_parametrization_message(item)
            message = (
                f"🧩 Signal parametrization for {html.bold(crypto_currency)} 🧩\n\n"
                + signal_parametrization_formatted
                + "ℹ️️ Would you like to modify these parameters?"
            )
            await callback_query.message.answer(
                message,
                reply_markup=keyboards_builder.get_yes_no_keyboard(
                    yes_button_callback_data=f"edit_signal_parametrization$${crypto_currency}"
                ),
            )
        except Exception as e:
            logger.error(f"Error retrieving signal parametrization: {str(e)}", exc_info=True)
            await callback_query.message.answer(
                f"⚠️ An error occurred while retrieving signal parametrization. Please try again later:\n\n{html.code(format_exception(e))}"  # noqa: E501
            )
    else:
        await callback_query.message.answer(
            "⚠️ Please log in to set signal parametrization.", reply_markup=keyboards_builder.get_login_keyboard(state)
        )
