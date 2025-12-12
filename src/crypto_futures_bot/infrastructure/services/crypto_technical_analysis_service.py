from typing import Any

import backoff
import pandas as pd
import pydash
from ta.momentum import RSIIndicator, StochRSIIndicator
from ta.trend import MACD, EMAIndicator
from ta.volatility import AverageTrueRange

from crypto_futures_bot.domain.enums.candlestick_enum import CandleStickEnum
from crypto_futures_bot.domain.vo.candlestick_indicators import CandleStickIndicators
from crypto_futures_bot.infrastructure.adapters.futures_exchange.base import AbstractFuturesExchangeService
from crypto_futures_bot.infrastructure.adapters.futures_exchange.types import Timeframe
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo.symbol_ticker import SymbolTicker
from crypto_futures_bot.infrastructure.services.tracked_crypto_currency_service import TrackedCryptoCurrencyService
from crypto_futures_bot.interfaces.telegram.services.utils import backoff_on_backoff_handler


class CryptoTechnicalAnalysisService:
    def __init__(
        self,
        tracked_crypto_currency_service: TrackedCryptoCurrencyService,
        futures_exchange_service: AbstractFuturesExchangeService,
    ) -> None:
        self._futures_exchange_service = futures_exchange_service
        self._tracked_crypto_currency_service = tracked_crypto_currency_service

    async def get_tracked_crypto_currency_prices(self) -> list[SymbolTicker]:
        tracked_crypto_currencies = await self._tracked_crypto_currency_service.find_all()
        account_info = await self._futures_exchange_service.get_account_info()
        symbols = [crypto_currency.to_symbol(account_info) for crypto_currency in tracked_crypto_currencies]
        tickers = await self._futures_exchange_service.get_symbol_tickers(symbols=symbols)
        ret = pydash.order_by(tickers, ["base_asset", "quote_asset"], ["asc", "asc"])
        return ret

    async def get_candlestick_indicators(
        self,
        symbol: str,
        *,
        timeframe: Timeframe = "15m",
        index: CandleStickEnum = CandleStickEnum.LAST,
        technical_analysis_df: pd.DataFrame | None = None,
    ) -> CandleStickIndicators:
        if technical_analysis_df is None:
            technical_analysis_df = await self.get_technical_analysis(symbol, timeframe=timeframe)
        selected_candlestick = technical_analysis_df.iloc[index.value]
        ret = CandleStickIndicators.from_series(symbol=symbol, index=index, series=selected_candlestick)
        return ret

    @backoff.on_exception(
        backoff.fibo,
        exception=IndexError,
        max_value=5,
        max_tries=7,
        jitter=backoff.random_jitter,
        on_backoff=backoff_on_backoff_handler,
    )
    async def get_technical_analysis(
        self, symbol: str, *, timeframe: Timeframe = "15m", ohlcv: list[list[Any]] | None = None
    ) -> pd.DataFrame:
        if ohlcv is None:
            ohlcv = await self._futures_exchange_service.fetch_ohlcv(symbol=symbol, timeframe=timeframe)
        df = pd.DataFrame(ohlcv, columns=["timestamp", "Open", "High", "Low", "Close", "Volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)

        df = self._calculate_indicators(df)
        # Drop NaN values and reset the index.
        # This cleans the data from the shorter lookback periods of the simple indicators.
        df.dropna(inplace=True)
        df.reset_index(drop=True, inplace=True)
        df.set_index("timestamp", inplace=True)
        return df

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        # EMAs
        df["ema50"] = EMAIndicator(df["Close"], window=50).ema_indicator()  # MACD
        macd = MACD(df["Close"])
        df["macd_line"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["macd_hist"] = macd.macd_diff()

        # Stochastic RSI
        stoch_rsi = StochRSIIndicator(df["Close"])
        df["stoch_rsi"] = stoch_rsi.stochrsi()
        df["stoch_rsi_k"] = stoch_rsi.stochrsi_k()
        df["stoch_rsi_d"] = stoch_rsi.stochrsi_d()

        # Relative Strength Index (RSI)
        df["rsi"] = RSIIndicator(df["Close"]).rsi()

        # Average True Range (ATR)
        df["atr"] = AverageTrueRange(df["High"], df["Low"], df["Close"]).average_true_range()

        # Relative Volume (RVOL)
        df["volume_sma"] = df["Volume"].rolling(window=20).mean()
        df["relative_volume"] = df["Volume"] / df["volume_sma"]
        return df
