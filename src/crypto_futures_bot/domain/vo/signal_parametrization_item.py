from dataclasses import dataclass

from crypto_futures_bot.constants import DEFAULT_ATR_SL_MULT, DEFAULT_ATR_TP_MULT


@dataclass
class SignalParametrizationItem:
    crypto_currency: str
    atr_sl_mult: float = DEFAULT_ATR_SL_MULT
    atr_tp_mult: float = DEFAULT_ATR_TP_MULT
