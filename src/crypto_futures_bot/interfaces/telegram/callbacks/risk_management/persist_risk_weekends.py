import logging
from dataclasses import replace

from aiogram import Dispatcher, html
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from crypto_futures_bot.config.dependencies import get_application_container
from crypto_futures_bot.domain.vo.risk_management_item import RiskManagementItem
from crypto_futures_bot.infrastructure.services.risk_management_service import RiskManagementService
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
risk_management_service: RiskManagementService = (
    application_container.infrastructure_container().services_container().risk_management_service()
)


@dp.callback_query(lambda c: c.data == "persist_risk_weekends_yes")
async def handle_persist_risk_weekends_yes_callback(callback_query: CallbackQuery, state: FSMContext) -> None:
    is_user_logged = await session_storage_service.is_user_logged(state)
    if is_user_logged:
        try:
            item: RiskManagementItem = await risk_management_service.get()
            updated_item = replace(item, open_trades_on_weekends=True)
            await risk_management_service.update(updated_item)
            await callback_query.message.answer(
                "📅 Weekend trading has been enabled ✅", reply_markup=keyboards_builder.get_home_keyboard()
            )
        except Exception as e:
            logger.error(f"Error persisting risk management weekend setting (yes): {str(e)}", exc_info=True)
            await callback_query.message.answer(
                f"⚠️ An error occurred while persisting risk management weekend setting. Please try again later:\n\n{html.code(format_exception(e))}"  # noqa: E501
            )
    else:
        await callback_query.message.answer(
            "⚠️ Please log in to set the weekend trading preference.",
            reply_markup=keyboards_builder.get_login_keyboard(),
        )


@dp.callback_query(lambda c: c.data == "persist_risk_weekends_no")
async def handle_persist_risk_weekends_no_callback(callback_query: CallbackQuery, state: FSMContext) -> None:
    is_user_logged = await session_storage_service.is_user_logged(state)
    if is_user_logged:
        try:
            item: RiskManagementItem = await risk_management_service.get()
            updated_item = replace(item, open_trades_on_weekends=False)
            await risk_management_service.update(updated_item)
            await callback_query.message.answer(
                "📅 Weekend trading has been disabled ❌", reply_markup=keyboards_builder.get_home_keyboard()
            )
        except Exception as e:
            logger.error(f"Error persisting risk management weekend setting (no): {str(e)}", exc_info=True)
            await callback_query.message.answer(
                f"⚠️ An error occurred while persisting risk management weekend setting. Please try again later:\n\n{html.code(format_exception(e))}"  # noqa: E501
            )
    else:
        await callback_query.message.answer(
            "⚠️ Please log in to set the weekend trading preference.",
            reply_markup=keyboards_builder.get_login_keyboard(),
        )
