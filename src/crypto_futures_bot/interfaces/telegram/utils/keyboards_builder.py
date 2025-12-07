from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties


class KeyboardsBuilder:
    def __init__(self, configuration_properties: ConfigurationProperties) -> None:
        self._configuration_properties = configuration_properties

    def get_home_keyboard(self) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="Home", callback_data="home"))
        return builder.as_markup()

    def get_login_keyboard(self) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="Login", callback_data="login"))
        return builder.as_markup()
