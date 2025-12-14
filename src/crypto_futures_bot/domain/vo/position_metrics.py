from dataclasses import dataclass

from crypto_futures_bot.domain.enums import PositionTypeEnum
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo import Position, SymbolMarketConfig, SymbolTicker


@dataclass
class PositionMetrics:
    position: Position
    symbol_market_config: SymbolMarketConfig
    ticker: SymbolTicker

    @property
    def notional(self) -> float:
        return round(
            self.position.contracts * self.position.contract_size * self.position.entry_price,
            ndigits=self.symbol_market_config.price_precision,
        )

    def get_unrealised_pnl(self) -> float:
        """
        Unrealised PnL for USDT-margined linear futures.

        Positive = profit
        Negative = loss
        """
        direction = 1 if self.position.position_type is PositionTypeEnum.LONG else -1
        return round(
            direction
            * (self.ticker.mark_price - self.position.entry_price)
            * self.position.contracts
            * self.position.contract_size,
            ndigits=self.symbol_market_config.price_precision,
        )

    def get_unrealised_pnl_ratio(self) -> float:
        return round(self.get_unrealised_pnl() / self.position.initial_margin, ndigits=2)

    def get_unrealised_net_revenue(self) -> float:
        """
        Unrealised economic result including already-paid fees.
        """
        return round(self.get_unrealised_pnl() - self.position.fee, ndigits=self.symbol_market_config.price_precision)
