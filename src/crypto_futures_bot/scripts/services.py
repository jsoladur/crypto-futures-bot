import asyncio
import logging
from datetime import datetime

import pandas as pd
from backtesting import Backtest
from typer import echo

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.constants import DEFAULT_CURRENCY_CODE
from crypto_futures_bot.infrastructure.adapters.futures_exchange.impl.mexc_futures_exchange import (
    MEXCFuturesExchangeService,
)
from crypto_futures_bot.infrastructure.services.crypto_technical_analysis_service import CryptoTechnicalAnalysisService
from crypto_futures_bot.infrastructure.services.orders_analytics_service import OrdersAnalyticsService
from crypto_futures_bot.infrastructure.tasks.signals_task_service import SignalsTaskService
from crypto_futures_bot.scripts.strategy import BotStrategy

logger = logging.getLogger(__name__)


class BacktestingService:
    def __init__(
        self,
        configuration_properties: ConfigurationProperties,
        futures_exchange_service: MEXCFuturesExchangeService,
        crypto_technical_analysis_service: CryptoTechnicalAnalysisService,
        orders_analytics_service: OrdersAnalyticsService,
        signals_task_service: SignalsTaskService,
    ) -> None:
        self._config = configuration_properties
        self._exchange_service = futures_exchange_service
        self._crypto_technical_analysis_service = crypto_technical_analysis_service
        self._orders_analytics_service = orders_analytics_service
        self._signals_task_service = signals_task_service

    async def run(
        self,
        start_date: datetime,
        end_date: datetime,
        crypto_currency: str,
        initial_cash: float,
        *,
        show_plot: bool = False,
    ) -> None:
        symbol = f"{crypto_currency}/{DEFAULT_CURRENCY_CODE}:{DEFAULT_CURRENCY_CODE}"
        await self._exchange_service.post_init()
        echo(f"Starting backtest for {symbol} from {start_date} to {end_date}")
        # 1. Download Data
        df = await self._download_data(symbol, start_date, end_date)
        if df is None or df.empty:
            echo("No data found, aborting backtest.")
            return
        # 2. Calculate Indicators
        # Accessing protected method to avoid code duplication as per requirements

        # 3. Prepare Data for Backtesting
        df.dropna(inplace=True)
        # 4. Configure Strategy
        # We need the symbol market config for precision
        symbol_market_config = await self._exchange_service.get_symbol_market_config(crypto_currency)

        BotStrategy.signals_service = self._signals_task_service
        BotStrategy.orders_service = self._orders_analytics_service
        BotStrategy.symbol_market_config = symbol_market_config

        # 5. Run Backtest
        bt = Backtest(df, BotStrategy, cash=initial_cash, commission=0.0004)
        stats = bt.run()

        echo("\n--- Backtest Result ---\n")
        echo(stats)
        if show_plot:
            bt.plot()  # Requires browser

    async def _download_data(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame | None:
        echo(f"Downloading data for {symbol}...")

        timeframe = "15m"
        limit = 1000
        all_ohlcv = []

        current_since = int(start_date.timestamp() * 1000)
        end_ts = int(end_date.timestamp() * 1000)

        while current_since < end_ts:
            ohlcv = await self._exchange_service.fetch_ohlcv(
                symbol, timeframe=timeframe, limit=limit, since=current_since
            )
            if not ohlcv:
                break
            all_ohlcv.extend(ohlcv)
            echo(f"Fetched {len(ohlcv)} candles. Last timestamp: {ohlcv[-1][0]}")

            last_timestamp = ohlcv[-1][0]
            if last_timestamp <= current_since:
                # Avoid infinite loop if exchange returns same data
                current_since += 15 * 60 * 1000
            else:
                current_since = last_timestamp + 1

            await asyncio.sleep(0.05)

        echo(f"Total candles fetched: {len(all_ohlcv)}")

        if not all_ohlcv:
            return None

        df = await self._crypto_technical_analysis_service.get_technical_analysis(symbol, ohlcv=all_ohlcv)
        return df
