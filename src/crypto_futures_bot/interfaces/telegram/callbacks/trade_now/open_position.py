import logging
import re

from aiogram import Dispatcher, F, html
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from crypto_futures_bot.config.dependencies import get_application_container
from crypto_futures_bot.domain.enums import PositionTypeEnum
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

REGEX = r"^open_position_\$_(.+)_\$_(.+)$"


@dp.callback_query(F.data.regexp(REGEX))
async def open_position_callback_handler(callback_query: CallbackQuery, state: FSMContext) -> None:
    is_user_logged = await session_storage_service.is_user_logged(state)
    if is_user_logged:
        try:
            match = re.match(REGEX, callback_query.data)
            crypto_currency = TrackedCryptoCurrencyItem.from_currency(match.group(1))
            position_type = PositionTypeEnum(match.group(2).upper())
            await callback_query.message.answer(
                f"ℹ️ Opening a {position_type.value.lower()} position for {crypto_currency.currency}..."
            )
            await trade_now_service.open_position(crypto_currency, position_type)
        except Exception as e:
            logger.error(f"Error removing the selected crypto currency: {str(e)}", exc_info=True)
            await callback_query.message.answer(
                f"⚠️ An error occurred while removing the selected crypto currency. Please try again later:\n\n{html.code(format_exception(e))}"  # noqa: E501
            )
    else:
        await callback_query.message.answer(
            "⚠️ Please log in to operate with tracked crypto currencies.",
            reply_markup=keyboards_builder.get_login_keyboard(state),
        )
