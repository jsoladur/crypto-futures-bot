from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.domain.vo.push_notification_item import PushNotificationItem
from crypto_futures_bot.interfaces.telegram.services.vo.tracked_crypto_currency_item import TrackedCryptoCurrencyItem


class KeyboardsBuilder:
    def __init__(self, configuration_properties: ConfigurationProperties) -> None:
        self._configuration_properties = configuration_properties

    def get_home_keyboard(self) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="💰 Portfolio Balance", callback_data="portfolio_balance"))
        builder.row(InlineKeyboardButton(text="🛰️ Tracker", callback_data="tracked_crypto_currencies_home"))
        builder.row(InlineKeyboardButton(text="🔔 Push Notifications", callback_data="push_notifications_home"))
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
            builder.row(
                InlineKeyboardButton(
                    text=f"🛰️ {tracked_crypto_currency.currency}",
                    callback_data=f"remove_tracked_crypto_currency_$_{tracked_crypto_currency.currency}",
                )
            )
        builder.row(InlineKeyboardButton(text="➕ Add", callback_data="add_tracker_crypto_currency"))
        builder.row(InlineKeyboardButton(text="🔙 Back", callback_data="go_back_home"))
        return builder.as_markup()

    def get_push_notifications_home_keyboard(
        self, push_notification_items: list[PushNotificationItem]
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for item in push_notification_items:
            action_icon = "⏸️" if item.activated else "▶️"
            state_icon = "🔔" if item.activated else "🔕"
            builder.row(
                InlineKeyboardButton(
                    text=f"{state_icon} {action_icon} {item.notification_type.description}",
                    callback_data=f"toggle_push_notification_$_{item.notification_type.value}",
                )
            )
        builder.row(InlineKeyboardButton(text="🔙 Back", callback_data="go_back_home"))
        return builder.as_markup()

    def get_yes_no_keyboard(self, *, yes_button_callback_data: str) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="☑️ Yes", callback_data=yes_button_callback_data),
            InlineKeyboardButton(text="🔙 No", callback_data="go_back_home"),
        )
        return builder.as_markup()
