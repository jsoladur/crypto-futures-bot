from dataclasses import dataclass

from crypto_futures_bot.domain.vo.tracked_crypto_currency_item import TrackedCryptoCurrencyItem
from crypto_futures_bot.infrastructure.adapters.futures_exchange.types import Timeframe


@dataclass(frozen=True, kw_only=True)
class SignalsEvaluationResult:
    timestamp: float | int
    crypto_currency: TrackedCryptoCurrencyItem
    timeframe: Timeframe = "15m"

    long_entry: bool
    long_exit: bool

    short_entry: bool
    short_exit: bool

    @property
    def cache_key(self) -> str:
        return f"{self.crypto_currency.currency}_$_{self.timeframe}"
