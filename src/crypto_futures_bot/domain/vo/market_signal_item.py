from dataclasses import dataclass

from crypto_futures_bot.domain.enums import MarketActionTypeEnum, PositionTypeEnum
from crypto_futures_bot.domain.types import Timeframe
from crypto_futures_bot.domain.vo import TrackedCryptoCurrencyItem


@dataclass(kw_only=True, frozen=True)
class MarketSignalItem:
    crypto_currency: TrackedCryptoCurrencyItem
    timeframe: Timeframe
    position_type: PositionTypeEnum
    action_type: MarketActionTypeEnum
    entry_price: float | None
    break_even_price: float | None
    stop_loss_percent_value: float | None
    take_profit_percent_value: float | None
    stop_loss_price: float | None
    take_profit_price: float | None
