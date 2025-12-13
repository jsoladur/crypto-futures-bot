import logging
import re

from aiogram import Dispatcher, F, html
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from crypto_futures_bot.config.dependencies import get_application_container
from crypto_futures_bot.domain.vo import TrackedCryptoCurrencyItem
from crypto_futures_bot.infrastructure.adapters.futures_exchange.base import AbstractFuturesExchangeService
from crypto_futures_bot.infrastructure.services.market_signal_service import MarketSignalService
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
market_signal_service: MarketSignalService = (
    application_container.infrastructure_container().services_container().market_signal_service()
)

REGEX = r"^show_market_signals_\$_(.+)$"


@dp.callback_query(F.data.regexp(REGEX))
async def show_last_market_signals_callback_handler(callback_query: CallbackQuery, state: FSMContext) -> None:
    is_user_logged = await session_storage_service.is_user_logged(state)
    if is_user_logged:
        try:
            match = re.match(REGEX, callback_query.data)
            currency = match.group(1)
            market_signals = await market_signal_service.find_all_market_signals(
                TrackedCryptoCurrencyItem.from_currency(currency)
            )
            account_info = await futures_exchange_service.get_account_info()
            symbol_market_config = await futures_exchange_service.get_symbol_market_config(currency)
            message = messages_formatter.format_market_signals_message(
                currency=currency,
                account_info=account_info,
                symbol_market_config=symbol_market_config,
                market_signals=market_signals,
            )
            await callback_query.message.answer(message, reply_markup=keyboards_builder.get_go_back_home_keyboard())
        except Exception as e:
            logger.error(f"Error fetching last market signals: {str(e)}", exc_info=True)
            await callback_query.message.answer(
                "⚠️ An error occurred while fetching last market signals. "
                + f"Please try again later:\n\n{html.code(format_exception(e))}"
            )
    else:
        await callback_query.message.answer(
            "⚠️ Please log in to fetch the last market signals.",
            reply_markup=keyboards_builder.get_login_keyboard(state),
        )
