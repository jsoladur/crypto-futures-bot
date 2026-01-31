import logging
import re

from aiogram import Dispatcher, F, html
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from crypto_futures_bot.config.dependencies import get_application_container
from crypto_futures_bot.domain.enums import PositionTypeEnum
from crypto_futures_bot.domain.vo import TrackedCryptoCurrencyItem
from crypto_futures_bot.interfaces.telegram.services.session_storage_service import SessionStorageService
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

REGEX = r"^confirm_position_\$_(.+)_\$_(.+)$"


@dp.callback_query(F.data.regexp(REGEX))
async def confirm_position_callback_handler(callback_query: CallbackQuery, state: FSMContext) -> None:
    is_user_logged = await session_storage_service.is_user_logged(state)
    if is_user_logged:
        match = re.match(REGEX, callback_query.data)
        crypto_currency = TrackedCryptoCurrencyItem.from_currency(match.group(1))
        position_type = PositionTypeEnum(match.group(2).upper())
        position_type_icon = "🟩" if position_type == PositionTypeEnum.LONG else "🟥"
        await callback_query.message.answer(
            f"⚠️ CONFIRM ACTION: This operation CANNOT be undone. "
            f"Are you sure you want to open a {position_type_icon} {html.bold(position_type.value.upper())} position for {html.bold(crypto_currency.currency)}?",  # noqa: E501
            reply_markup=keyboards_builder.get_yes_no_keyboard(
                yes_button_callback_data=f"open_position_$_{crypto_currency.currency}_$_{position_type.value.lower()}"
            ),
        )
    else:
        await callback_query.message.answer(
            "⚠️ Please log in to operate with tracked crypto currencies.",
            reply_markup=keyboards_builder.get_login_keyboard(),
        )
