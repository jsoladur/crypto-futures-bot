from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram_dialog import setup_dialogs
from dependency_injector import containers, providers

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties


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
