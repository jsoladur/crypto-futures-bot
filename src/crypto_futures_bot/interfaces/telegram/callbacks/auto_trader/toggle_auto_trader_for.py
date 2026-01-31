import logging
import re

from aiogram import Dispatcher, F, html
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from crypto_futures_bot.config.dependencies import get_application_container
from crypto_futures_bot.infrastructure.services.auto_trader_crypto_currency_service import (
    AutoTraderCryptoCurrencyService,
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
auto_trader_crypto_currency_service: AutoTraderCryptoCurrencyService = (
    application_container.infrastructure_container().services_container().auto_trader_crypto_currency_service()
)

REGEX = r"^toggle_auto_trader_for_\$_(.+)$"


@dp.callback_query(F.data.regexp(REGEX))
async def perform_remove_tracked_crypto_currency_callback_handler(
    callback_query: CallbackQuery, state: FSMContext
) -> None:
    is_user_logged = await session_storage_service.is_user_logged(state)
    if is_user_logged:
        try:
            match = re.match(REGEX, callback_query.data)
            currency = match.group(1)
            item = await auto_trader_crypto_currency_service.toggle_for(currency)
            await callback_query.message.answer(
                f"ℹ️ Auto Trading for '{html.bold(currency)}'"
                + f" has been {('🟢 ' + html.bold('ENABLED')) if item.activated else ('🟥 ' + html.bold('DISABLED'))}!",  # noqa: E501
                reply_markup=keyboards_builder.get_home_keyboard(),
            )
        except Exception as e:
            logger.error(f"Error toggling auto trader crypto currency: {str(e)}", exc_info=True)
            await callback_query.message.answer(
                f"⚠️ An error occurred while toggling auto trader crypto currency. Please try again later:\n\n{html.code(format_exception(e))}"  # noqa: E501
            )
    else:
        await callback_query.message.answer(
            "⚠️ Please log in to operate with auto trader crypto currencies.",
            reply_markup=keyboards_builder.get_login_keyboard(),
        )
