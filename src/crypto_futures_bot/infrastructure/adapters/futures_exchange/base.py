from abc import ABC, abstractmethod
from typing import Any

import ccxt.async_support as ccxt

from crypto_futures_bot.infrastructure.adapters.futures_exchange.types import Timeframe
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo.portfolio_balance import PortfolioBalance


class AbstractFuturesExchangeService(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def get_portfolio_balance(self) -> PortfolioBalance:
        """Get the portfolio balance from the futures exchange.

        Returns:
            PortfolioBalance: The portfolio balance.
        """

    @abstractmethod
    async def get_trading_crypto_currencies(self, *, client: ccxt.Exchange | None = None) -> list[str]:
        """Get the list of trading crypto currencies from the futures exchange.

        Args:
            client (Any | None, optional): Client to connect with the exchange. Defaults to None.

        Returns:
            list[str]: The list of trading crypto currencies.
        """

    @abstractmethod
    async def fetch_ohlcv(
        self, symbol: str, timeframe: Timeframe, limit: int = 251, *, client: ccxt.Exchange | None = None
    ) -> list[list[Any]]:
        """Fetches OHLCV (Open, High, Low, Close, Volume) data for a given symbol and timeframe.

        Args:
            symbol (str): The trading pair symbol (e.g., 'BTC/USDT').
            timeframe (Timeframe): The timeframe for the OHLCV data.
            limit (int, optional): The maximum number of data points to fetch. Defaults to 251.
            client (Any | None, optional): Client to connect with the exchange. Defaults to None.

        Returns:
            list[list[Any]]: A list of OHLCV data points.
        """
