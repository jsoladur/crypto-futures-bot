from typing import Any

from aiogram import Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.interfaces.telegram.enums import SessionKeysEnum


class SessionStorageService:
    def __init__(self, configuration_properties: ConfigurationProperties, dispatcher: Dispatcher) -> None:
        self._configuration_properties = configuration_properties
        self._dispatcher = dispatcher
        self._in_memory_storage_by_chat_id: dict[str, dict[str, Any]] = {}

    async def get_or_create_fsm_context(self, *, bot_id: int, chat_id: int, user_id: int) -> FSMContext:
        return FSMContext(
            storage=self._dispatcher.storage,
            key=StorageKey(bot_id=int(bot_id), chat_id=int(chat_id), user_id=int(user_id)),
        )

    async def is_user_logged(self, state: FSMContext) -> bool:
        if not self._configuration_properties.login_enabled:
            return True
        data = await state.get_data()
        return SessionKeysEnum.USER_CONTEXT.value in data

    async def set_user_logged(self, state: FSMContext, userinfo: dict[str, Any]) -> None:
        data = await state.get_data()
        data[SessionKeysEnum.USER_CONTEXT.value] = userinfo
        await state.set_data(data)

    async def get_signal_parametrization_crypto_currency_form(self, chat_id: int) -> str:
        data = self._in_memory_storage_by_chat_id.setdefault(chat_id, {})
        if SessionKeysEnum.SIGNAL_PARAMETRIZATION_CRYPTO_CURRENCY_FORM.value not in data:
            return ValueError("Missing signal parametrization crypto currency form")
        crypto_currency = data.pop(SessionKeysEnum.SIGNAL_PARAMETRIZATION_CRYPTO_CURRENCY_FORM.value)
        return crypto_currency

    async def set_signal_parametrization_crypto_currency_form(self, state: FSMContext, crypto_currency: str) -> None:
        data = self._in_memory_storage_by_chat_id.setdefault(state.key.chat_id, {})
        data[SessionKeysEnum.SIGNAL_PARAMETRIZATION_CRYPTO_CURRENCY_FORM.value] = crypto_currency

    async def perform_logout(self, state: FSMContext) -> bool:
        data = await state.get_data()
        if SessionKeysEnum.USER_CONTEXT.value in data:
            await state.clear()
