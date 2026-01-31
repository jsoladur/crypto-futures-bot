import logging

from aiogram import Dispatcher, html
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from crypto_futures_bot.config.dependencies import get_application_container
from crypto_futures_bot.infrastructure.services.orders_analytics_service import OrdersAnalyticsService
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
orders_analytics_service: OrdersAnalyticsService = (
    application_container.infrastructure_container().services_container().orders_analytics_service()
)


@dp.callback_query(lambda c: c.data == "positions")
async def get_positions_callback_handler(callback_query: CallbackQuery, state: FSMContext):
    is_user_logged = await session_storage_service.is_user_logged(state)
    if is_user_logged:
        try:
            open_position_metrics_list = await orders_analytics_service.get_open_position_metrics()
            if open_position_metrics_list:
                for idx, open_position_metrics in enumerate(open_position_metrics_list):
                    answer_text = messages_formatter.format_position_metrics(open_position_metrics)
                    if idx + 1 >= len(open_position_metrics_list):
                        await callback_query.message.answer(
                            answer_text, reply_markup=keyboards_builder.get_go_back_home_keyboard()
                        )
                    else:
                        await callback_query.message.answer(answer_text)
            else:
                await callback_query.message.answer("✳️ There are no currently opened positions.")
        except Exception as e:
            logger.error(f"Error trying to get positions info: {str(e)}", exc_info=True)
            await callback_query.message.answer(
                f"⚠️ An error occurred while getting positions info. Please try again later:\n\n{html.code(format_exception(e))}"  # noqa: E501
            )
    else:
        await callback_query.message.answer(
            "⚠️ Please log in to get the positions info.", reply_markup=keyboards_builder.get_login_keyboard()
        )
