import logging
import re
from dataclasses import replace

from aiogram import Dispatcher, F, html
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from crypto_futures_bot.config.dependencies import get_application_container
from crypto_futures_bot.domain.vo.risk_management_item import RiskManagementItem
from crypto_futures_bot.infrastructure.services.risk_management_service import RiskManagementService
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
risk_management_service: RiskManagementService = (
    application_container.infrastructure_container().services_container().risk_management_service()
)

REGEX = r"^persist_risk_max_trades_\$_(.+?)$"


@dp.callback_query(F.data.regexp(REGEX))
async def handle_persist_risk_max_trades_callback(callback_query: CallbackQuery, state: FSMContext):
    is_user_logged = await session_storage_service.is_user_logged(state)
    if is_user_logged:
        try:
            match = re.match(REGEX, callback_query.data)
            max_trades_value = int(match.group(1).strip())
            item: RiskManagementItem = await risk_management_service.get()
            updated_item = replace(item, number_of_concurrent_trades=max_trades_value)
            await risk_management_service.update(updated_item)
            await callback_query.message.answer(
                f"🛡️ Risk Management max trades changed to {html.code(str(max_trades_value))}",
                reply_markup=keyboards_builder.get_home_keyboard(),
            )
        except Exception as e:
            logger.error(f"Error persisting risk management max trades value: {str(e)}", exc_info=True)
            await callback_query.message.answer(
                f"⚠️ An error occurred while persisting risk management max trades value. Please try again later:\n\n{html.code(format_exception(e))}"  # noqa: E501
            )
    else:
        await callback_query.message.answer(
            "⚠️ Please log in to set the risk management max trades value.",
            reply_markup=keyboards_builder.get_login_keyboard(),
        )
