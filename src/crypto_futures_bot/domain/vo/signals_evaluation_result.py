from dataclasses import dataclass

from crypto_futures_bot.domain.types import Timeframe
from crypto_futures_bot.domain.vo.tracked_crypto_currency_item import TrackedCryptoCurrencyItem


@dataclass(frozen=True, kw_only=True)
class SignalsEvaluationResult:
    timestamp: float | int
    crypto_currency: TrackedCryptoCurrencyItem
    timeframe: Timeframe = "15m"

    long_entry: bool
    short_entry: bool

    @property
    def cache_key(self) -> str:
        return f"{self.crypto_currency.currency}_$_{self.timeframe}"
