import logging

from aiogram import Dispatcher, html
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from crypto_futures_bot.config.dependencies import get_application_container
from crypto_futures_bot.infrastructure.adapters.futures_exchange.base import AbstractFuturesExchangeService
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
futures_exchange_service: AbstractFuturesExchangeService = (
    application_container.infrastructure_container().adapters_container().futures_exchange_service()
)


@dp.callback_query(lambda c: c.data == "portfolio_balance")
async def get_portfolio_balance_callback(callback_query: CallbackQuery, state: FSMContext) -> None:
    is_user_logged = await session_storage_service.is_user_logged(state)
    if is_user_logged:
        try:
            portfolio_balance = await futures_exchange_service.get_portfolio_balance()
            message = messages_formatter.format_portfolio_balance(portfolio_balance)
            await callback_query.message.answer(text=message)
        except Exception as e:
            logger.error(f"Error fetching get the Portfolio balance: {str(e)}", exc_info=True)
            await callback_query.message.answer(
                "⚠️ An error occurred while fetching the Portfolio balance. "
                + f"Please try again later:\n\n{html.code(format_exception(e))}"
            )
    else:
        await callback_query.message.answer(
            "⚠️ Please log in to get the current the Portfolio balance!",
            reply_markup=keyboards_builder.get_login_keyboard(),
        )
