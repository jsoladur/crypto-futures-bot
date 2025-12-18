import asyncio

import pandas as pd
from backtesting import Backtest

from crypto_futures_bot.domain.vo import SignalParametrizationItem
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo import SymbolMarketConfig
from crypto_futures_bot.scripts.vo import BacktestingResult


def run_single_backtest_combination(
    symbol: str,
    df: pd.DataFrame,
    initial_cash: float,
    signal_parametrization_item: SignalParametrizationItem,
    symbol_market_config: SymbolMarketConfig,
) -> BacktestingResult | None:
    """
    Runs a single backtest for one combination of parameters. Designed to be called in parallel.
    """
    import logging
    import warnings

    from crypto_futures_bot.scripts.config import Container
    from crypto_futures_bot.scripts.services import BacktestingService

    warnings.filterwarnings("ignore")
    logger = logging.getLogger(__name__)

    application_container = Container()
    application_container.check_dependencies()

    backtesting_service: BacktestingService = application_container.backtesting_service()
    ret: tuple[Backtest, pd.Series] | None = None
    try:
        # We use df.copy() to ensure each process gets its own data
        *_, stats = asyncio.run(
            backtesting_service.internal_run(
                symbol=symbol,
                df=df.copy(),
                initial_cash=initial_cash,
                long_entry_oversold_threshold=signal_parametrization_item.long_entry_oversold_threshold,
                short_entry_overbought_threshold=signal_parametrization_item.short_entry_overbought_threshold,
                atr_sl_mult=signal_parametrization_item.atr_sl_mult,
                atr_tp_mult=signal_parametrization_item.atr_tp_mult,
                symbol_market_config=symbol_market_config,
                use_tqdm=False,
            )
        )
        ret = BacktestingResult(
            signal_parametrization_item=signal_parametrization_item,
            stats={key: value for key, value in stats.to_dict().items() if not key.startswith("_")},
        )
    except Exception as e:
        # We use echo_fn for thread-safe printing if needed
        logger.warning(
            f"Backtest failed for params {signal_parametrization_item}: {e}",  # noqa: E501
            exc_info=True,
        )
    return ret
