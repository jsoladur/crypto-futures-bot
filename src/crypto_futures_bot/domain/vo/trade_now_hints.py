from dataclasses import dataclass

from crypto_futures_bot.domain.vo import CandleStickIndicators
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo import SymbolTicker


@dataclass(frozen=True)
class PositionHints:
    is_long: bool
    entry_price: float
    break_even_price: float
    stop_loss_price: float
    move_sl_to_break_even_price: float
    move_sl_to_first_target_profit_price: float
    take_profit_price: float


@dataclass(frozen=True)
class TradeNowHints:
    ticker: SymbolTicker
    candlestick_indicators: CandleStickIndicators
    # Technical Parameters
    stop_loss_percent_value: float
    take_profit_percent_value: float
    # Position Calculations
    long: PositionHints
    short: PositionHints
