from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from crypto_futures_bot.domain.enums.candlestick_enum import CandleStickEnum


@dataclass(frozen=True)
class CandleStickIndicators:
    symbol: str
    timestamp: datetime
    index: CandleStickEnum
    # Candlestick
    highest_price: float
    lowest_price: float
    opening_price: float
    closing_price: float
    # EMAs
    ema50: float
    # MACD
    macd_line: float
    macd_signal: float
    macd_hist: float
    # Stochastic RSI
    stoch_rsi: float
    stoch_rsi_k: float
    stoch_rsi_d: float
    # RSI
    rsi: float
    # Average True Range (ATR)
    atr: float
    # Relative Volume (RVOL)
    relative_volume: float

    @staticmethod
    def from_series(*, symbol: str, index: CandleStickEnum, series: pd.Series) -> CandleStickIndicators:
        return CandleStickIndicators(
            symbol=symbol,
            timestamp=series.name,
            index=index,
            highest_price=series["High"],
            lowest_price=series["Low"],
            opening_price=series["Open"],
            closing_price=series["Close"],
            ema50=series["ema50"],
            macd_line=series["macd_line"],
            macd_signal=series["macd_signal"],
            macd_hist=series["macd_hist"],
            stoch_rsi=series["stoch_rsi"],
            stoch_rsi_k=series["stoch_rsi_k"],
            stoch_rsi_d=series["stoch_rsi_d"],
            rsi=series["rsi"],
            atr=series["atr"],
            relative_volume=series["relative_volume"],
        )
