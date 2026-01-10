from typing import Any

import pydash
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.constants import RISK_MANAGEMENT_ALLOWED_VALUES_LIST
from crypto_futures_bot.domain.vo import AutoTraderCryptoCurrencyItem, TrackedCryptoCurrencyItem
from crypto_futures_bot.domain.vo.push_notification_item import PushNotificationItem
from crypto_futures_bot.domain.vo.risk_management_item import RiskManagementItem


class KeyboardsBuilder:
    def __init__(self, configuration_properties: ConfigurationProperties) -> None:
        self._configuration_properties = configuration_properties

    def get_home_keyboard(self) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="💰 Portfolio Balance", callback_data="portfolio_balance"))
        builder.row(
            InlineKeyboardButton(text="🔍 Tracker", callback_data="tracked_crypto_currencies_home"),
            InlineKeyboardButton(text="🎯 Auto-Trader", callback_data="auto_trader_home"),
        )
        builder.row(
            InlineKeyboardButton(text="💹 Prices", callback_data="prices"),
            InlineKeyboardButton(text="🔥 Positions", callback_data="positions"),
        )
        builder.row(
            InlineKeyboardButton(text="🧩 Parametrization", callback_data="signal_parametrization_home"),
            InlineKeyboardButton(text="🛡️ Risk", callback_data="risk_management_home"),
        )
        builder.row(
            InlineKeyboardButton(text="🚦 Market Signals", callback_data="market_signals_home"),
            InlineKeyboardButton(text="🚀 Trade Now", callback_data="trade_now_home"),
        )
        builder.row(InlineKeyboardButton(text="🔔 Notifications", callback_data="push_notifications_home"))

        builder.row(InlineKeyboardButton(text="🚪 Logout", callback_data="logout"))
        return builder.as_markup()

    def get_go_back_home_keyboard(self) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="🔙 Back", callback_data="go_back_home"))
        return builder.as_markup()

    def get_login_keyboard(self) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="Login", callback_data="login"))
        return builder.as_markup()

    def get_market_signals_keyboard(self, crypto_currencies: list[TrackedCryptoCurrencyItem]) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for crypto_currency in crypto_currencies:
            builder.row(
                InlineKeyboardButton(
                    text=f"🚦 {crypto_currency.currency}",
                    callback_data=f"show_market_signals_$_{crypto_currency.currency}",
                )
            )
        builder.row(InlineKeyboardButton(text="🔙 Back", callback_data="go_back_home"))
        return builder.as_markup()

    def get_signal_parametrization_keyboard(
        self, crypto_currencies: list[TrackedCryptoCurrencyItem]
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for crypto_currency in crypto_currencies:
            builder.row(
                InlineKeyboardButton(
                    text=f"🧩 {crypto_currency.currency}",
                    callback_data=f"show_signal_parametrization_$_{crypto_currency.currency}",
                )
            )
        builder.row(InlineKeyboardButton(text="🔙 Back", callback_data="go_back_home"))
        return builder.as_markup()

    def get_tracked_crypto_currencies_keyboard(
        self, tracked_crypto_currencies: list[TrackedCryptoCurrencyItem]
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for tracked_crypto_currency in tracked_crypto_currencies:
            builder.row(
                InlineKeyboardButton(
                    text=f"🔍 {tracked_crypto_currency.currency}",
                    callback_data=f"remove_tracked_crypto_currency_$_{tracked_crypto_currency.currency}",
                )
            )
        builder.row(InlineKeyboardButton(text="➕ Add", callback_data="add_tracker_crypto_currency"))
        builder.row(InlineKeyboardButton(text="🔙 Back", callback_data="go_back_home"))
        return builder.as_markup()

    def get_auto_trader_currencies_keyboard(self, items: list[AutoTraderCryptoCurrencyItem]) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for item in items:
            state_icon = "🟢" if item.activated else "🟥"
            action_icon = "⏸️" if item.activated else "▶️"
            builder.row(
                InlineKeyboardButton(
                    text=f"🎯 :: {state_icon} {action_icon} {item.currency}",
                    callback_data=f"toggle_auto_trader_for_$_{item.currency}",
                )
            )
        builder.row(InlineKeyboardButton(text="🔙 Back", callback_data="go_back_home"))
        return builder.as_markup()

    def get_trade_now_keyboard(
        self, tracked_crypto_currencies: list[TrackedCryptoCurrencyItem]
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for tracked_crypto_currency in tracked_crypto_currencies:
            builder.row(
                InlineKeyboardButton(
                    text=f"🚀 {tracked_crypto_currency.currency}",
                    callback_data=f"trade_now_result_$_{tracked_crypto_currency.currency}",
                )
            )
        builder.row(InlineKeyboardButton(text="🔙 Back", callback_data="go_back_home"))
        return builder.as_markup()

    def get_open_new_position_keyboard(self, crypto_currency: str) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="🟩 Open LONG", callback_data=f"confirm_position_$_{crypto_currency}_$_long"),
            InlineKeyboardButton(text="🟥 Open SHORT", callback_data=f"confirm_position_$_{crypto_currency}_$_short"),
        )
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

    def get_risk_management_home_keyboard(self, risk_management_item: RiskManagementItem) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text=f"🛡️ Current Risk :: {risk_management_item.percent_value} %", callback_data="set_risk_management"
            )
        )
        builder.row(InlineKeyboardButton(text="🔙 Back", callback_data="go_back_home"))
        return builder.as_markup()

    def get_risk_percent_values(self) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        buttons = [
            InlineKeyboardButton(text=f"{percent_value}%", callback_data=f"persist_risk_management_$_{percent_value}")
            for percent_value in RISK_MANAGEMENT_ALLOWED_VALUES_LIST
            if percent_value >= 1.0
        ]
        # Add buttons in rows of 5
        for buttons_chunk in pydash.chunk(buttons, size=4):
            builder.row(*buttons_chunk)
        builder.row(InlineKeyboardButton(text="🔙 Back", callback_data="go_back_home"))
        return builder.as_markup()

    def get_yes_no_keyboard(self, *, yes_button_callback_data: str) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="☑️ Yes", callback_data=yes_button_callback_data),
            InlineKeyboardButton(text="🔙 No", callback_data="go_back_home"),
        )
        return builder.as_markup()

    @staticmethod
    def get_signal_parametrization_keyboard_for(values: list[Any]) -> ReplyKeyboardMarkup:
        builder = ReplyKeyboardBuilder()
        keyboard_buttons = [KeyboardButton(text=str(value)) for value in values]
        for buttons_chunk in pydash.chunk(keyboard_buttons, size=2):
            builder.row(*buttons_chunk)
        return builder.as_markup()
