import logging
from typing import Any

from aiogram import Dispatcher, html
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import ScrollingGroup, Select
from aiogram_dialog.widgets.text import Format

from crypto_futures_bot.config.dependencies import get_application_container
from crypto_futures_bot.infrastructure.services.tracked_crypto_currency_service import TrackedCryptoCurrencyService
from crypto_futures_bot.interfaces.telegram.callbacks.tracked_crypto_currencies.dialog.states import (
    TrackedCryptoCurrencyStates,
)
from crypto_futures_bot.interfaces.telegram.utils.exceptions_utils import format_exception
from crypto_futures_bot.interfaces.telegram.utils.keyboards_builder import KeyboardsBuilder

logger = logging.getLogger(__name__)

application_container = get_application_container()
dp: Dispatcher = application_container.interfaces_container().telegram_container().dispatcher()
keyboards_builder: KeyboardsBuilder = (
    application_container.interfaces_container().telegram_container().keyboards_builder()
)
tracked_crypto_currency_service: TrackedCryptoCurrencyService = (
    application_container.infrastructure_container().services_container().tracked_crypto_currency_service()
)


async def _on_crypto_currency_selected(callback_query: CallbackQuery, _: Any, __: DialogManager, currency: str) -> None:
    try:
        await tracked_crypto_currency_service.add(currency=currency)
        await callback_query.message.answer(
            f"✅ {currency} added to tracked crypto currencies", reply_markup=keyboards_builder.get_home_keyboard()
        )
    except Exception as e:
        logger.error(f"Error adding {currency} as tracked crypto currencies: {str(e)}", exc_info=True)
        await callback_query.message.answer(
            f"⚠️ An error occurred while adding {currency} as tracked crypto currencies. Please try again later:\n\n{html.code(format_exception(e))}"  # noqa: E501
        )


async def _get_items(*_, **__) -> dict[str, Any]:
    items = await tracked_crypto_currency_service.get_non_tracked_crypto_currencies()
    return {"items": items}


_dialog = Dialog(
    # Window 1: scrolling list to choose from
    Window(
        Format("ℹ️ Select a crypto currency to add as tracked:"),
        ScrollingGroup(
            Select(
                Format("{item}"),
                id="select_item",
                item_id_getter=lambda x: x,
                items="items",
                on_click=_on_crypto_currency_selected,
            ),
            id="scroll",
            width=3,
            height=9,
        ),
        getter=_get_items,
        state=TrackedCryptoCurrencyStates.main,
    )
)

dp.include_router(_dialog)
