from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.interfaces.telegram.services.vo.tracked_crypto_currency_item import TrackedCryptoCurrencyItem


class KeyboardsBuilder:
    def __init__(self, configuration_properties: ConfigurationProperties) -> None:
        self._configuration_properties = configuration_properties

    def get_home_keyboard(self) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="🛰️ Tracker", callback_data="tracked_crypto_currencies_home"))
        return builder.as_markup()

    def get_login_keyboard(self) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="Login", callback_data="login"))
        return builder.as_markup()

    def get_tracked_crypto_currencies_keyboard(
        self, tracked_crypto_currencies: list[TrackedCryptoCurrencyItem]
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for tracked_crypto_currency in tracked_crypto_currencies:
            builder.add(
                InlineKeyboardButton(
                    text=f"🛰️ {tracked_crypto_currency.currency}",
                    callback_data=f"tracked_crypto_currency_{tracked_crypto_currency.currency}",
                )
            )
        return builder.as_markup()
