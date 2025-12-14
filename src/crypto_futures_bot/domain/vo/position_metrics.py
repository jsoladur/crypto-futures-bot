from dataclasses import dataclass

from crypto_futures_bot.domain.enums import PositionTypeEnum
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo.position import Position


@dataclass
class PositionMetrics:
    position: Position
    mark_price: float

    def get_unrealised_pnl(self) -> float:
        """
        Unrealised PnL for USDT-margined linear futures.

        Positive = profit
        Negative = loss
        """
        direction = 1 if self.position.position_type is PositionTypeEnum.LONG else -1
        return (
            direction
            * (self.mark_price - self.position.entry_price)
            * self.position.contracts
            * self.position.contract_size
        )

    def get_unrealised_pnl_ratio(self) -> float:
        return self.get_unrealised_pnl() / self.position.initial_margin

    def get_unrealised_net_revenue(self) -> float:
        """
        Unrealised economic result including already-paid fees.
        """
        return self.get_unrealised_pnl() + self.position.fee
