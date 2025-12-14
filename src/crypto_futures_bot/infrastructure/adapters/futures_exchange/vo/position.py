from dataclasses import dataclass

from crypto_futures_bot.domain.enums import PositionOpenTypeEnum, PositionTypeEnum


@dataclass
class Position:
    # Identification
    position_id: str
    symbol: str

    # Margin & risk
    initial_margin: float
    leverage: int
    liquidation_price: float
    open_type: PositionOpenTypeEnum

    # Direction
    position_type: PositionTypeEnum

    # Pricing
    entry_price: float

    # Size
    contracts: float
    contract_size: float

    # Costs
    fee: float

    @property
    def base_asset(self) -> str:
        return self.symbol.split("/")[0]

    @property
    def quote_asset(self) -> str:
        base_and_contract = self.symbol.split("/")[1]
        quote_asset = base_and_contract.split(":")[0]
        return quote_asset

    def get_unrealised_pnl(self, mark_price: float) -> float:
        """
        Unrealised PnL for USDT-margined linear futures.

        Positive = profit
        Negative = loss
        """
        direction = 1 if self.position_type is PositionTypeEnum.LONG else -1
        return direction * (mark_price - self.entry_price) * self.contracts * self.contract_size

    def get_unrealised_pnl_ratio(self, mark_price: float) -> float:
        return self.get_unrealised_pnl(mark_price) / self.initial_margin

    def get_unrealised_net_revenue(self, mark_price: float) -> float:
        """
        Unrealised economic result including already-paid fees.
        """
        return self.get_unrealised_pnl(mark_price) + self.fee
