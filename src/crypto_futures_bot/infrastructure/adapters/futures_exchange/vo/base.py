from abc import ABC
from dataclasses import dataclass

from crypto_futures_bot.domain.enums import PositionOpenTypeEnum, PositionTypeEnum


@dataclass(kw_only=True, frozen=True)
class AbstractPosition(ABC):
    symbol: str
    initial_margin: float
    leverage: int
    # Margin & risk
    open_type: PositionOpenTypeEnum
    # Direction
    position_type: PositionTypeEnum
    # Stop Loss and Take profit
    stop_loss_price: float | None = None
    take_profit_price: float | None = None
