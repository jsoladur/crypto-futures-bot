from abc import ABC, abstractmethod
from typing import Any

from crypto_futures_bot.domain.types import Timeframe
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo import (
    AccountInfo,
    FuturesWallet,
    PortfolioBalance,
    Position,
    SymbolMarketConfig,
    SymbolTicker,
)


class AbstractFuturesExchangeService(ABC):
    def __init__(self):
        pass

    @abstractmethod
    async def post_init(self) -> None:
        """Post initialization method."""

    @abstractmethod
    async def get_account_info(self) -> AccountInfo:
        """Get the account info from the futures exchange.

        Returns:
            AccountInfo: The account info."""

    @abstractmethod
    async def get_portfolio_balance(self) -> PortfolioBalance:
        """Get the portfolio balance from the futures exchange.

        Returns:
            PortfolioBalance: The portfolio balance.
        """

    @abstractmethod
    async def get_futures_wallet(self) -> FuturesWallet:
        """Get the futures wallet from the futures exchange.

        Returns:
            FuturesWallet: The futures wallet.
        """

    @abstractmethod
    async def get_symbol_ticker(self, symbol: str) -> SymbolTicker:
        """Get the symbol ticker from the futures exchange.

        Args:
            symbol (str): The trading pair symbol (e.g., 'BTC/USDT:USDT').

        Returns:
            SymbolTicker: The symbol ticker.
        """

    @abstractmethod
    async def get_symbol_tickers(self, *, symbols: list[str] | None = None) -> list[SymbolTicker]:
        """Get the list of symbol tickers from the futures exchange.

        Args:
            symbols (list[str] | None, optional):
                The list of trading pair symbols (e.g., 'BTC/USDT:USDT').
                Defaults to None.

        Returns:
            list[SymbolTicker]: The list of symbol tickers.
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

    @abstractmethod
    async def get_symbol_market_config(self, crypto_currency: str) -> SymbolMarketConfig:
        """Get the symbol market config from the futures exchange.

        Args:
            crypto_currency (str): The trading pair symbol (e.g., 'BTC').

        Returns:
            SymbolMarketConfig: The symbol market config.
        """

    @abstractmethod
    async def get_open_positions(self) -> list[Position]:
        """Get the list of open positions from the futures exchange.

        Returns:
            list[Position]: The list of open positions.
        """

    @abstractmethod
    def get_taker_fee(self) -> float:
        """Get the taker fee from the futures exchange.

        Returns:
            float: The taker fee.
        """
