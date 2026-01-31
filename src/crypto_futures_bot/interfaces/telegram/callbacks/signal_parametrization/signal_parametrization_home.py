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


@dp.callback_query(lambda c: c.data == "signal_parametrization_home")
async def signal_parametrization_home_callback_handler(callback_query: CallbackQuery, state: FSMContext) -> None:
    is_user_logged = await session_storage_service.is_user_logged(state)
    if is_user_logged:
        try:
            tracked_crypto_currencies = await tracked_crypto_currency_service.find_all()
            await callback_query.message.answer(
                "ℹ️ Click into a symbol for showing up its signal parametrization",
                reply_markup=keyboards_builder.get_signal_parametrization_keyboard(tracked_crypto_currencies),
            )
        except Exception as e:
            logger.error(f"Error fetching signal parametrization: {str(e)}", exc_info=True)
            await callback_query.message.answer(
                "⚠️ An error occurred while fetching signal parametrization. "
                + f"Please try again later:\n\n{html.code(format_exception(e))}"
            )
    else:
        await callback_query.message.answer(
            "⚠️ Please log in to fetch the signal parametrization.", reply_markup=keyboards_builder.get_login_keyboard()
        )
