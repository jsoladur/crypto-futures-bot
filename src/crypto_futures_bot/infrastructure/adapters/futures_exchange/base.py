from abc import ABC, abstractmethod
from typing import Any

from crypto_futures_bot.infrastructure.adapters.futures_exchange.types import Timeframe
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo import AccountInfo, PortfolioBalance


class AbstractFuturesExchangeService(ABC):
    def __init__(self):
        pass

    @abstractmethod
    async def get_account_info(self, *, client: Any | None = None) -> AccountInfo:
        """Get the account info from the futures exchange.

        Returns:
            AccountInfo: The account info."""

    @abstractmethod
    def get_portfolio_balance(self) -> PortfolioBalance:
        """Get the portfolio balance from the futures exchange.

        Returns:
            PortfolioBalance: The portfolio balance.
        """

    @abstractmethod
    async def get_crypto_currencies(self) -> list[str]:
        """Get the list of trading crypto currencies from the futures exchange.

        Returns:
            list[str]: The list of trading crypto currencies.
        """

    @abstractmethod
    async def fetch_ohlcv(self, symbol: str, *, timeframe: Timeframe = "15m", limit: int = 251) -> list[list[Any]]:
        """Fetches OHLCV (Open, High, Low, Close, Volume) data for a given symbol and timeframe.

        Args:
            symbol (str): The trading pair symbol (e.g., 'BTC/USDT').
            timeframe (Timeframe, optional): The timeframe for the OHLCV data. Defaults to "15m".
            limit (int, optional): The maximum number of data points to fetch. Defaults to 251.

        Returns:
            list[list[Any]]: A list of OHLCV data points.
        """
