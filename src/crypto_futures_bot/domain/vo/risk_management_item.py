from dataclasses import dataclass

from crypto_futures_bot.constants import (
    DEFAULT_RISK_MANAGEMENT_NUMBER_OF_CONCURRENT_TRADES,
    DEFAULT_RISK_MANAGEMENT_OPEN_TRADES_ON_WEEKENDS,
    DEFAULT_RISK_MANAGEMENT_PERCENTAGE,
)


@dataclass(kw_only=True, frozen=True)
class RiskManagementItem:
    percent_value: float = DEFAULT_RISK_MANAGEMENT_PERCENTAGE
    number_of_concurrent_trades: int = DEFAULT_RISK_MANAGEMENT_NUMBER_OF_CONCURRENT_TRADES
    open_trades_on_weekends: bool = DEFAULT_RISK_MANAGEMENT_OPEN_TRADES_ON_WEEKENDS
