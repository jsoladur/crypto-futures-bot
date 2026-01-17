from dataclasses import dataclass

from crypto_futures_bot.constants import (
    DEFAULT_RISK_MANAGEMENT_NUMBER_OF_CONCURRENT_TRADES,
    DEFAULT_RISK_MANAGEMENT_PERCENTAGE,
)


@dataclass(kw_only=True, frozen=True)
class RiskManagementItem:
    percent_value: float = DEFAULT_RISK_MANAGEMENT_PERCENTAGE
    number_of_concurrent_trades: int = DEFAULT_RISK_MANAGEMENT_NUMBER_OF_CONCURRENT_TRADES
