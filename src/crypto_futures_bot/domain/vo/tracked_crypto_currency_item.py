from dataclasses import dataclass

from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo import AccountInfo


@dataclass(kw_only=True, frozen=True)
class TrackedCryptoCurrencyItem:
    currency: str

    def to_symbol(self, account_info: AccountInfo) -> str:
        return f"{self.currency}/{account_info.currency_code}:{account_info.currency_code}"
