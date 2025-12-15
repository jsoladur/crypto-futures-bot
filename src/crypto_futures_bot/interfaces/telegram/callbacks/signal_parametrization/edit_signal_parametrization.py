import logging
import re

from aiogram import Bot, Dispatcher, F, html
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from crypto_futures_bot.config.dependencies import get_application_container
from crypto_futures_bot.infrastructure.services.signal_parametrization_service import SignalParametrizationService
from crypto_futures_bot.interfaces.telegram.callbacks.signal_parametrization.signal_parametrization_form import (
    SignalParametrizationForm,
)
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
bot: Bot = application_container.interfaces_container().telegram_container().telegram_bot()
messages_formatter: MessagesFormatter = (
    application_container.interfaces_container().telegram_container().messages_formatter()
)
signal_parametrization_service: SignalParametrizationService = (
    application_container.infrastructure_container().services_container().signal_parametrization_service()
)


@SignalParametrizationForm.submit(router=dp)
async def signal_parametrization_form_submit_handler(form: SignalParametrizationForm):
    try:
        crypto_currency = await session_storage_service.get_signal_parametrization_crypto_currency_form(form.chat_id)
        signal_parametrization = form.to_value_object(crypto_currency)
        await signal_parametrization_service.save_or_update(signal_parametrization)
        message = (
            f"✅ Signal parametrization for {html.bold(crypto_currency)} configuration successfully persisted.\n\n"
        )
        message += messages_formatter.format_signal_parametrization_message(signal_parametrization)
        await form.answer(message, reply_markup=keyboards_builder.get_home_keyboard())
    except Exception as e:
        logger.error(f"Error persisting signal parametrization: {str(e)}", exc_info=True)
        await form.answer(
            "⚠️ An error occurred while persisting an signal parametrization. "
            + f"Please try again later:\n\n{html.code(format_exception(e))}"
        )


REGEX = r"^edit_signal_parametrization_\$_(.+)$"


@dp.callback_query(F.data.regexp(REGEX))
async def persist_signal_parametrization_callback_handler(callback_query: CallbackQuery, state: FSMContext):
    is_user_logged = await session_storage_service.is_user_logged(state)
    if is_user_logged:
        try:
            match = re.match(REGEX, callback_query.data)
            crypto_currency = match.group(1).strip().upper()
            await session_storage_service.set_signal_parametrization_crypto_currency_form(state, crypto_currency)
            await SignalParametrizationForm.start(bot, state)
        except Exception as e:
            logger.error(f"Error persisting signal parametrization: {str(e)}", exc_info=True)
            await callback_query.message.answer(
                "⚠️ An error occurred while persisting an signal parametrization. "
                + f"Please try again later:\n\n{html.code(format_exception(e))}"
            )
    else:
        await callback_query.message.answer(
            "⚠️ Please log in to set the corresponding signal parametrization.",
            reply_markup=keyboards_builder.get_login_keyboard(state),
        )
