import asyncio
import logging
from datetime import datetime
from itertools import product

import pandas as pd
from backtesting import Backtest, backtesting
from joblib import Parallel, delayed
from tqdm.asyncio import tqdm
from typer import echo

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.constants import (
    DEFAULT_CURRENCY_CODE,
    LONG_ENTRY_OVERSOLD_THRESHOLDS,
    SHORT_ENTRY_OVERBOUGHT_THRESHOLDS,
    SL_MULTIPLIERS,
    TP_MULTIPLIERS,
)
from crypto_futures_bot.domain.types import Timeframe
from crypto_futures_bot.domain.vo import SignalParametrizationItem
from crypto_futures_bot.infrastructure.adapters.futures_exchange.impl.mexc_futures_exchange import (
    MEXCFuturesExchangeService,
)
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo import SymbolMarketConfig
from crypto_futures_bot.infrastructure.services.crypto_technical_analysis_service import CryptoTechnicalAnalysisService
from crypto_futures_bot.infrastructure.services.orders_analytics_service import OrdersAnalyticsService
from crypto_futures_bot.infrastructure.tasks.signals_task_service import SignalsTaskService
from crypto_futures_bot.scripts.jobs import run_single_backtest_combination
from crypto_futures_bot.scripts.strategy import BotStrategy
from crypto_futures_bot.scripts.vo import BacktestingResult

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
        *,
        initial_cash: float,
        long_entry_oversold_threshold: float,
        short_entry_overbought_threshold: float,
        atr_sl_mult: float,
        atr_tp_mult: float,
        show_plot: bool = False,
    ) -> None:
        symbol_market_config = await self._exchange_service.get_symbol_market_config(crypto_currency)
        symbol, df = await self._calculate_historical_indicators(
            crypto_currency=crypto_currency, start_date=start_date, end_date=end_date
        )
        bt, stats = await self.internal_run(
            symbol=symbol,
            df=df,
            initial_cash=initial_cash,
            long_entry_oversold_threshold=long_entry_oversold_threshold,
            short_entry_overbought_threshold=short_entry_overbought_threshold,
            atr_sl_mult=atr_sl_mult,
            atr_tp_mult=atr_tp_mult,
            symbol_market_config=symbol_market_config,
        )
        echo(f"\n--- Backtest Result for {crypto_currency} ---\n")
        echo(stats)
        if show_plot:
            bt.plot()

    async def research(
        self,
        start_date: datetime,
        end_date: datetime,
        crypto_currency: str,
        *,
        initial_cash: float,
        apply_paralellism: bool = True,
    ) -> None:
        echo(f"\n--- Research for {crypto_currency} ---\n")
        symbol_market_config = await self._exchange_service.get_symbol_market_config(crypto_currency)
        signal_parametrization_items = self._calculate_signal_parametrization_items(crypto_currency)
        symbol, df = await self._calculate_historical_indicators(
            crypto_currency=crypto_currency, start_date=start_date, end_date=end_date
        )
        if apply_paralellism:
            parallel_results = Parallel(n_jobs=-1)(
                delayed(run_single_backtest_combination)(
                    symbol=symbol,
                    df=df,
                    initial_cash=initial_cash,
                    signal_parametrization_item=signal_parametrization_item,
                    symbol_market_config=symbol_market_config,
                )
                for signal_parametrization_item in tqdm(
                    signal_parametrization_items, desc="Researching signal parametrizations"
                )
            )
            # Filter out any runs that failed (they will return None)
            results = [res for res in parallel_results if res is not None]
        else:
            results = []
            for signal_parametrization_item in tqdm(
                signal_parametrization_items, desc="Researching signal parametrizations"
            ):
                *_, stats = await self.internal_run(
                    symbol=symbol,
                    df=df,
                    initial_cash=initial_cash,
                    long_entry_oversold_threshold=signal_parametrization_item.long_entry_oversold_threshold,
                    short_entry_overbought_threshold=signal_parametrization_item.short_entry_overbought_threshold,
                    atr_sl_mult=signal_parametrization_item.atr_sl_mult,
                    atr_tp_mult=signal_parametrization_item.atr_tp_mult,
                    symbol_market_config=symbol_market_config,
                    use_tqdm=False,
                )
                results.append(
                    BacktestingResult(
                        signal_parametrization_item=signal_parametrization_item,
                        stats={key: value for key, value in stats.to_dict().items() if not key.startswith("_")},
                    )
                )
        results.sort(
            key=lambda r: (
                r.stats.get("Return [%]", -float("inf")),
                r.stats.get("Win Rate [%]", -float("inf")),
                -r.stats.get(
                    "Max. Drawdown [%]", float("inf")
                ),  # Negative for sorting ascending (lower drawdown is better)
            ),
            reverse=True,
        )
        best_result, *_ = results
        message_lines = [
            "\n 🎉 --- Best Backtesting Result 🎉",
            "🧩 Parametrization:",
            f"📉 Long Entry Oversold Threshold = {best_result.signal_parametrization_item.long_entry_oversold_threshold}",  # noqa: E501
            f"📈 Short Entry Overbought Threshold = {best_result.signal_parametrization_item.short_entry_overbought_threshold}",  # noqa: E501
            f"🛡️ SL ATR x = {best_result.signal_parametrization_item.atr_sl_mult}",  # noqa: E501
            f"🏁 TP ATR x = {best_result.signal_parametrization_item.atr_tp_mult}",  # noqa: E501
            "",
            "📊 Stats:",
            *[f"{key}: {value}" for key, value in best_result.stats.items()],
        ]
        echo("\n".join(message_lines))

    async def internal_run(
        self,
        *,
        symbol: str,
        df: pd.DataFrame,
        initial_cash: float,
        long_entry_oversold_threshold: float,
        short_entry_overbought_threshold: float,
        atr_sl_mult: float,
        atr_tp_mult: float,
        symbol_market_config: SymbolMarketConfig,
        use_tqdm: bool = True,
    ) -> tuple[Backtest, pd.Series]:
        original_backtesting_tqdm = backtesting._tqdm
        try:
            crypto_currency = symbol.split("/")[0]
            # We need the symbol market config for precision
            # 4. Run Backtest
            bt = Backtest(df, BotStrategy, cash=initial_cash, commission=self._exchange_service.get_taker_fee())
            if not use_tqdm:
                backtesting._tqdm = lambda iterable=None, *args, **kwargs: iterable
            stats = bt.run(
                signals_task_service=self._signals_task_service,
                orders_analytics_service=self._orders_analytics_service,
                symbol_market_config=symbol_market_config,
                signal_parametrization=SignalParametrizationItem(
                    crypto_currency=crypto_currency,
                    atr_sl_mult=atr_sl_mult,
                    atr_tp_mult=atr_tp_mult,
                    long_entry_oversold_threshold=long_entry_oversold_threshold,
                    short_entry_overbought_threshold=short_entry_overbought_threshold,
                ),
            )
            return bt, stats
        finally:
            backtesting._tqdm = original_backtesting_tqdm

    async def _calculate_historical_indicators(
        self, crypto_currency: str, start_date: datetime, end_date: datetime
    ) -> tuple[str, pd.DataFrame]:
        symbol = f"{crypto_currency}/{DEFAULT_CURRENCY_CODE}:{DEFAULT_CURRENCY_CODE}"
        echo(f"Starting backtest for {symbol} from {start_date} to {end_date}")
        # 1. Download Data
        df = await self._download_data(symbol, start_date, end_date)
        if df is None or df.empty:
            echo("No data found, aborting backtest.")
            return
        # 2. Prepare Data for Backtesting
        df.dropna(inplace=True)
        return symbol, df

    async def _download_data(
        self, symbol: str, start_date: datetime, end_date: datetime, *, timeframe: Timeframe = "15m"
    ) -> pd.DataFrame | None:
        echo(f"Downloading data for {symbol}...")
        limit = 1000
        all_ohlcv = []
        current_since = int(start_date.timestamp() * 1000)
        end_ts = int(end_date.timestamp() * 1000)

        with tqdm(
            total=end_ts - current_since,
            unit="ms",
            desc=f"Downloading {symbol} OHLCV",
            initial=0,
            dynamic_ncols=True,
            unit_scale=True,
        ) as pbar:
            while current_since < end_ts:
                ohlcv = await self._exchange_service.fetch_ohlcv(
                    symbol, timeframe=timeframe, limit=limit, since=current_since
                )
                if not ohlcv:
                    timeframe_duration_ms = self._calculate_timeframe_duration_ms(timeframe)
                    current_since += timeframe_duration_ms * limit
                    pbar.update(timeframe_duration_ms)
                else:
                    all_ohlcv.extend(ohlcv)
                    last_timestamp_fetched = ohlcv[-1][0]
                    progress_made = last_timestamp_fetched - current_since + 1
                    pbar.update(progress_made)
                    current_since = last_timestamp_fetched + 1
                await asyncio.sleep(0.05)
        echo(f"Total candles fetched: {len(all_ohlcv)}")
        if not all_ohlcv:
            return None
        df = await self._crypto_technical_analysis_service.get_technical_analysis(symbol, ohlcv=all_ohlcv)
        return df

    def _calculate_timeframe_duration_ms(self, timeframe: Timeframe) -> int:
        if timeframe.endswith("m"):
            timeframe_duration_ms = int(timeframe[:-1]) * 60 * 1000
        elif timeframe.endswith("h"):
            timeframe_duration_ms = int(timeframe[:-1]) * 60 * 60 * 1000
        elif timeframe.endswith("d"):
            timeframe_duration_ms = int(timeframe[:-1]) * 24 * 60 * 60 * 1000
        else:
            timeframe_duration_ms = 15 * 60 * 1000
        return timeframe_duration_ms

    def _calculate_signal_parametrization_items(self, crypto_currency: str) -> list[SignalParametrizationItem]:
        return [
            SignalParametrizationItem(
                crypto_currency=crypto_currency,
                atr_sl_mult=atr_sl_mult,
                atr_tp_mult=atr_tp_mult,
                long_entry_oversold_threshold=long_entry_oversold_threshold,
                short_entry_overbought_threshold=short_entry_overbought_threshold,
            )
            for long_entry_oversold_threshold, short_entry_overbought_threshold, atr_sl_mult, atr_tp_mult in product(
                LONG_ENTRY_OVERSOLD_THRESHOLDS, SHORT_ENTRY_OVERBOUGHT_THRESHOLDS, SL_MULTIPLIERS, TP_MULTIPLIERS
            )
        ]
