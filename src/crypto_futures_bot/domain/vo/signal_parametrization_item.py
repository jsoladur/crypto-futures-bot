from dataclasses import dataclass

from crypto_futures_bot.constants import (
    DEFAULT_ATR_SL_MULT,
    DEFAULT_ATR_TP_MULT,
    DEFAULT_LONG_ENTRY_OVERSOLD_THRESHOLD,
    DEFAULT_SHORT_ENTRY_OVERBOUGHT_THRESHOLD,
)


@dataclass
class SignalParametrizationItem:
    crypto_currency: str
    long_entry_oversold_threshold: float = DEFAULT_LONG_ENTRY_OVERSOLD_THRESHOLD
    short_entry_overbought_threshold: float = DEFAULT_SHORT_ENTRY_OVERBOUGHT_THRESHOLD
    atr_sl_mult: float = DEFAULT_ATR_SL_MULT
    atr_tp_mult: float = DEFAULT_ATR_TP_MULT
