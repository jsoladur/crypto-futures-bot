from dataclasses import dataclass


@dataclass(kw_only=True, frozen=True)
class PortfolioBalance:
    spot_balance: float
    futures_balance: float
    currency_code: str

    @property
    def total_balance(self) -> float:
        return round(self.spot_balance + self.futures_balance, ndigits=2)
