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

    # Stop Loss and Take profit
    stop_loss_price: float | None = None
    take_profit_price: float | None = None

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
