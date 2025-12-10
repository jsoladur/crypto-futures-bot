from dataclasses import dataclass

from crypto_futures_bot.infrastructure.adapters.futures_exchange.types import Timeframe


@dataclass(frozen=True, kw_only=True)
class SignalsEvaluationResult:
    timestamp: float | int
    symbol: str
    timeframe: Timeframe

    long_entry: bool
    long_exit: bool

    short_entry: bool
    short_exit: bool
