from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from crypto_futures_bot.config.dependencies import get_application_container

application_container = get_application_container()
dp: Dispatcher = application_container.interfaces_container().telegram_container().dispatcher()
application_version = application_container.application_version()


@dp.message(Command("info"))
async def command_info_handler(message: Message) -> None:
    await message.answer(f"Crypto Futures Bot v{application_version}")
