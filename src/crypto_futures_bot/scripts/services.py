import asyncio
import logging
from datetime import datetime
from unittest.mock import MagicMock

import pandas as pd
from backtesting import Backtest

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.infrastructure.adapters.futures_exchange.impl.mexc_futures_exchange import (
    MEXCFuturesExchangeService,
)
from crypto_futures_bot.infrastructure.services.crypto_technical_analysis_service import CryptoTechnicalAnalysisService
from crypto_futures_bot.infrastructure.services.orders_analytics_service import OrdersAnalyticsService
from crypto_futures_bot.infrastructure.tasks.signals_task_service import SignalsTaskService
from crypto_futures_bot.scripts.strategy import BotStrategy

logger = logging.getLogger(__name__)


class BacktestingService:
    def __init__(self, start_date: datetime, end_date: datetime, symbol: str, initial_cash: float):
        self._start_date = start_date
        self._end_date = end_date
        self._symbol = symbol
        self._initial_cash = initial_cash
        self._config = ConfigurationProperties()

        # Initialize Services
        self._exchange_service = MEXCFuturesExchangeService(self._config)

        # We mock dependencies not strictly needed for the logic we use
        self._crypto_technical_analysis_service = CryptoTechnicalAnalysisService(
            tracked_crypto_currency_service=MagicMock(), futures_exchange_service=self._exchange_service
        )

        self._orders_analytics_service = OrdersAnalyticsService(
            configuration_properties=self._config, push_notification_service=MagicMock(), telegram_service=MagicMock()
        )

        self._signals_task_service = SignalsTaskService(
            configuration_properties=self._config,
            telegram_service=MagicMock(),
            push_notification_service=MagicMock(),
            event_emitter=MagicMock(),
            scheduler=MagicMock(),
            tracked_crypto_currency_service=MagicMock(),
            futures_exchange_service=self._exchange_service,
            orders_analytics_service=self._orders_analytics_service,
            crypto_technical_analysis_service=self._crypto_technical_analysis_service,
        )

    async def run(self):
        await self._exchange_service.post_init()

        logger.info(f"Starting backtest for {self._symbol} from {self._start_date} to {self._end_date}")

        # 1. Download Data
        df = await self._download_data()
        if df is None or df.empty:
            logger.error("No data found, aborting backtest.")
            return

        # 2. Calculate Indicators
        # Accessing protected method to avoid code duplication as per requirements
        df = self._crypto_technical_analysis_service._calculate_indicators(df)

        # 3. Prepare Data for Backtesting
        df.dropna(inplace=True)
        df.rename(
            columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}, inplace=True
        )

        # 4. Configure Strategy
        base_currency = self._symbol.split("/")[0]
        # We need the symbol market config for precision
        symbol_market_config = await self._exchange_service.get_symbol_market_config(base_currency)

        BotStrategy.signals_service = self._signals_task_service
        BotStrategy.orders_service = self._orders_analytics_service
        BotStrategy.symbol_market_config = symbol_market_config

        # 5. Run Backtest
        bt = Backtest(df, BotStrategy, cash=self._initial_cash, commission=0.0006)
        stats = bt.run()

        logger.info("\n--- Backtest Result ---\n")
        logger.info(stats)
        # bt.plot() # Requires browser

    async def _download_data(self) -> pd.DataFrame | None:
        logger.info(f"Downloading data for {self._symbol}...")

        timeframe = "15m"
        limit = 1000
        all_ohlcv = []

        current_since = int(self._start_date.timestamp() * 1000)
        end_ts = int(self._end_date.timestamp() * 1000)

        while current_since < end_ts:
            ohlcv = await self._exchange_service.fetch_ohlcv(
                self._symbol, timeframe=timeframe, limit=limit, since=current_since
            )
            if not ohlcv:
                break
            all_ohlcv.extend(ohlcv)
            logger.info(f"Fetched {len(ohlcv)} candles. Last timestamp: {ohlcv[-1][0]}")

            last_timestamp = ohlcv[-1][0]
            if last_timestamp <= current_since:
                # Avoid infinite loop if exchange returns same data
                current_since += 15 * 60 * 1000
            else:
                current_since = last_timestamp + 1

            await asyncio.sleep(0.1)

        logger.info(f"Total candles fetched: {len(all_ohlcv)}")

        if not all_ohlcv:
            return None

        df = pd.DataFrame(all_ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df.set_index("timestamp", inplace=True)
        return df
