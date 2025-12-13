import logging

from aiogram import Dispatcher, html
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from crypto_futures_bot.config.dependencies import get_application_container
from crypto_futures_bot.infrastructure.services.tracked_crypto_currency_service import TrackedCryptoCurrencyService
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
tracked_crypto_currency_service: TrackedCryptoCurrencyService = (
    application_container.infrastructure_container().services_container().tracked_crypto_currency_service()
)


@dp.callback_query(lambda c: c.data == "market_signals_home")
async def market_signals_home_callback_handler(callback_query: CallbackQuery, state: FSMContext) -> None:
    is_user_logged = await session_storage_service.is_user_logged(state)
    if is_user_logged:
        try:
            tracked_crypto_currencies = await tracked_crypto_currency_service.find_all()
            await callback_query.message.answer(
                "ℹ️ Click into a symbol for showing up its market signals",
                reply_markup=keyboards_builder.get_market_signals_keyboard(tracked_crypto_currencies),
            )
        except Exception as e:
            logger.error(f"Error fetching market signals: {str(e)}", exc_info=True)
            await callback_query.message.answer(
                "⚠️ An error occurred while fetching market signals. "
                + f"Please try again later:\n\n{html.code(format_exception(e))}"
            )
    else:
        await callback_query.message.answer(
            "⚠️ Please log in to fetch the market signals.", reply_markup=keyboards_builder.get_login_keyboard(state)
        )
