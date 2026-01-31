import logging
import re

from aiogram import Dispatcher, F, html
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from crypto_futures_bot.config.dependencies import get_application_container
from crypto_futures_bot.domain.vo import TrackedCryptoCurrencyItem
from crypto_futures_bot.infrastructure.services.trade_now_service import TradeNowService
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
trade_now_service: TradeNowService = (
    application_container.infrastructure_container().services_container().trade_now_service()
)

REGEX = r"^trade_now_result_\$_(.+)$"


@dp.callback_query(F.data.regexp(REGEX))
async def trade_now_result_callback_handler(callback_query: CallbackQuery, state: FSMContext) -> None:
    is_user_logged = await session_storage_service.is_user_logged(state)
    if is_user_logged:
        try:
            match = re.match(REGEX, callback_query.data)
            crypto_currency = match.group(1).strip().upper()
            trade_now_hints = await trade_now_service.get_trade_now_hints(
                TrackedCryptoCurrencyItem.from_currency(crypto_currency)
            )
            message = messages_formatter.format_trade_now_hints(trade_now_hints)
            message += "\n\n" + "Would you like to open a trade based on these hints?"
            await callback_query.message.answer(
                message, reply_markup=keyboards_builder.get_open_new_position_keyboard(crypto_currency)
            )
        except Exception as e:
            logger.error(f"Error calculating trade now hints: {str(e)}", exc_info=True)
            await callback_query.message.answer(
                f"⚠️ An error occurred while calculating trade now hints. Please try again later:\n\n{html.code(format_exception(e))}"  # noqa: E501
            )
    else:
        await callback_query.message.answer(
            "⚠️ Please log in to use trade now hints features.", reply_markup=keyboards_builder.get_login_keyboard()
        )
