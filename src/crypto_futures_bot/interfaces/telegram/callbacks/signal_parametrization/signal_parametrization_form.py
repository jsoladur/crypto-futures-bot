from aiogram import F
from aiogram.types import KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram3_form import Form, FormField

from crypto_futures_bot.constants import (
    LONG_ENTRY_OVERSOLD_THRESHOLDS,
    SHORT_ENTRY_OVERBOUGHT_THRESHOLDS,
    SL_MULTIPLIERS,
    TP_MULTIPLIERS,
)
from crypto_futures_bot.domain.vo import SignalParametrizationItem


class SignalParametrizationForm(Form):
    long_entry_oversold_threshold: float = FormField(
        enter_message_text="📉 Select Long Entry Oversold Threshold",
        error_message_text="❌ Invalid Long Entry Oversold Threshold value. Valid values: "
        + f"{', '.join([str(value) for value in LONG_ENTRY_OVERSOLD_THRESHOLDS])}",
        filter=F.text.in_([str(value) for value in LONG_ENTRY_OVERSOLD_THRESHOLDS]) & F.text,
        reply_markup=ReplyKeyboardBuilder()
        .add(*(KeyboardButton(text=str(value)) for value in LONG_ENTRY_OVERSOLD_THRESHOLDS))
        .as_markup(),
    )
    short_entry_overbought_threshold: float = FormField(
        enter_message_text="📈 Select Short Entry Overbought Threshold",
        error_message_text="❌ Invalid Short Entry Overbought Threshold value. Valid values: "
        + f"{', '.join([str(value) for value in SHORT_ENTRY_OVERBOUGHT_THRESHOLDS])}",
        filter=F.text.in_([str(value) for value in SHORT_ENTRY_OVERBOUGHT_THRESHOLDS]) & F.text,
        reply_markup=ReplyKeyboardBuilder()
        .add(*(KeyboardButton(text=str(value)) for value in SHORT_ENTRY_OVERBOUGHT_THRESHOLDS))
        .as_markup(),
    )
    atr_sl_mult: int = FormField(
        enter_message_text="🛡️ Select SL ATR x",
        error_message_text="❌ Invalid SL ATR value. Valid values: "
        + f"{', '.join([str(value) for value in SL_MULTIPLIERS])}",
        filter=F.text.in_([str(value) for value in SL_MULTIPLIERS]) & F.text,
        reply_markup=ReplyKeyboardBuilder()
        .add(*(KeyboardButton(text=str(value)) for value in SL_MULTIPLIERS))
        .as_markup(),
    )
    atr_tp_mult: int = FormField(
        enter_message_text="🏁 Select TP ATR x",
        error_message_text="❌ Invalid TP ATR value. Valid values: "
        + f"{', '.join([str(value) for value in TP_MULTIPLIERS])}",
        filter=F.text.in_([str(value) for value in TP_MULTIPLIERS]) & F.text,
        reply_markup=ReplyKeyboardBuilder()
        .add(*(KeyboardButton(text=str(value)) for value in TP_MULTIPLIERS))
        .as_markup(),
    )

    def to_value_object(self, crypto_currency: str) -> SignalParametrizationItem:
        ret = SignalParametrizationItem(
            crypto_currency=crypto_currency,
            atr_sl_mult=float(self.atr_sl_mult),
            atr_tp_mult=float(self.atr_tp_mult),
            long_entry_oversold_threshold=float(self.long_entry_oversold_threshold),
            short_entry_overbought_threshold=float(self.short_entry_overbought_threshold),
        )
        return ret
