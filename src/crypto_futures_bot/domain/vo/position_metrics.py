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

    @property
    def initial_margin(self) -> float:
        return round(self.position.initial_margin, ndigits=self.symbol_market_config.price_precision)

    @property
    def unrealised_pnl(self) -> float:
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

    @property
    def unrealised_pnl_ratio(self) -> float:
        return round(self.unrealised_pnl / self.initial_margin, ndigits=2)

    @property
    def unrealised_net_revenue(self) -> float:
        """
        Unrealised economic result including already-paid fees.
        """
        return round(self.unrealised_pnl - self.position.fee, ndigits=self.symbol_market_config.price_precision)

    @property
    def profit_factor(self) -> float | None:
        if self.position.take_profit_price is None or self.position.stop_loss_price is None:
            return None
        potential_profit = self.potential_profit_at_tp
        potential_loss = abs(self.potential_loss_at_sl)
        if potential_loss == 0:  # pragma: no cover (defensive)
            return None
        return round(potential_profit / potential_loss, ndigits=2)

    @property
    def potential_profit_at_tp(self) -> float | None:
        """
        Theoretical unrealised PnL if Take Profit is hit.
        """
        if self.position.take_profit_price is None:
            return None

        direction = 1 if self.position.position_type is PositionTypeEnum.LONG else -1

        profit = (
            direction
            * (self.position.take_profit_price - self.position.entry_price)
            * self.position.contracts
            * self.position.contract_size
        )

        return round(profit, ndigits=self.symbol_market_config.price_precision)

    @property
    def potential_loss_at_sl(self) -> float | None:
        """
        Theoretical unrealised PnL if Stop Loss is hit.
        Negative value by definition.
        """
        if self.position.stop_loss_price is None:
            return None

        direction = 1 if self.position.position_type is PositionTypeEnum.LONG else -1

        loss = (
            direction
            * (self.position.stop_loss_price - self.position.entry_price)
            * self.position.contracts
            * self.position.contract_size
        )

        return round(loss, ndigits=self.symbol_market_config.price_precision)
