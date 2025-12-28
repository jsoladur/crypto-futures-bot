from dataclasses import dataclass

from crypto_futures_bot.constants import DEFAULT_RISK_MANAGEMENT_PERCENTAGE


@dataclass(kw_only=True, frozen=True)
class RiskManagementItem:
    percent_value: float = DEFAULT_RISK_MANAGEMENT_PERCENTAGE
