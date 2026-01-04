from dataclasses import dataclass

from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo.base import AbstractPosition


@dataclass(kw_only=True, frozen=True)
class Position(AbstractPosition):
    # Identification
    position_id: str
    # Margin & risk
    liquidation_price: float
    # Pricing
    entry_price: float
    # Size
    contracts: float
    contract_size: float
    # Costs
    fee: float
