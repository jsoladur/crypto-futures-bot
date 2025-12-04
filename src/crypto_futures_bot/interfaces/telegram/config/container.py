from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram_dialog import setup_dialogs
from dependency_injector import containers, providers

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.interfaces.telegram.services.session_storage_service import SessionStorageService
from crypto_futures_bot.interfaces.telegram.services.telegram_service import TelegramService
from crypto_futures_bot.interfaces.telegram.utils.keyboards_builder import KeyboardsBuilder
from crypto_futures_bot.interfaces.telegram.utils.messages_formatter import MessagesFormatter


class TelegramContainer(containers.DeclarativeContainer):
    configuration_properties = providers.Dependency()

    @staticmethod
    def _dispacher() -> Dispatcher:
        dispacher = Dispatcher(storage=MemoryStorage())
        setup_dialogs(dispacher)
        return dispacher

    @staticmethod
    def _telegram_bot(configuration_properties: ConfigurationProperties) -> Bot:
        bot = Bot(
            token=configuration_properties.telegram_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        return bot

    dispatcher = providers.Singleton(_dispacher)
    telegram_bot = providers.Singleton(_telegram_bot, configuration_properties=configuration_properties)

    keyboards_builder = providers.Singleton(KeyboardsBuilder, configuration_properties=configuration_properties)
    messages_formatter = providers.Singleton(MessagesFormatter, configuration_properties=configuration_properties)

    session_storage_service = providers.Singleton(
        SessionStorageService, configuration_properties=configuration_properties, dispatcher=dispatcher
    )

    telegram_service = providers.Singleton(
        TelegramService, telegram_bot=telegram_bot, keyboards_builder=keyboards_builder
    )
