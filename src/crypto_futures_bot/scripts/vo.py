from dataclasses import dataclass
from typing import Any

from crypto_futures_bot.domain.vo import SignalParametrizationItem


@dataclass(frozen=True, kw_only=True)
class BacktestingResult:
    signal_parametrization_item: SignalParametrizationItem
    stats: dict[str, Any]
