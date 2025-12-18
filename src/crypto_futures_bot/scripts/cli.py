import asyncio
import logging
import warnings
from datetime import UTC, datetime, timedelta

import typer

from crypto_futures_bot.constants import (
    DEFAULT_ATR_SL_MULT,
    DEFAULT_ATR_TP_MULT,
    DEFAULT_LONG_ENTRY_OVERSOLD_THRESHOLD,
    DEFAULT_SHORT_ENTRY_OVERBOUGHT_THRESHOLD,
)
from crypto_futures_bot.scripts.config import Container
from crypto_futures_bot.scripts.services import BacktestingService

# Configure basic logging for CLI
warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
application_container = Container()
application_container.check_dependencies()
backtesting_service: BacktestingService = application_container.backtesting_service()

app = typer.Typer()


@app.command()
def backtest(
    currency: str = typer.Option("DOGE", help="Crypto currency to backtest"),
    days: int = typer.Option(365, help="Number of days to backtest"),
    initial_cash: float = typer.Option(3_000.0, help="Initial cash in USDT"),
    long_entry_oversold_threshold: float = typer.Option(
        DEFAULT_LONG_ENTRY_OVERSOLD_THRESHOLD, help="Long entry oversold threshold"
    ),
    short_entry_overbought_threshold: float = typer.Option(
        DEFAULT_SHORT_ENTRY_OVERBOUGHT_THRESHOLD, help="Short entry overbought threshold"
    ),
    atr_sl_mult: float = typer.Option(DEFAULT_ATR_SL_MULT, help="ATR SL multiplier"),
    atr_tp_mult: float = typer.Option(DEFAULT_ATR_TP_MULT, help="ATR TP multiplier"),
    show_plot: bool = typer.Option(False, help="Show plot"),
):
    """
    Run backtesting strategy for a given symbol.
    """
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=days)
    asyncio.run(
        backtesting_service.run(
            start_date=start_date,
            end_date=end_date,
            crypto_currency=currency,
            initial_cash=initial_cash,
            long_entry_oversold_threshold=long_entry_oversold_threshold,
            short_entry_overbought_threshold=short_entry_overbought_threshold,
            atr_sl_mult=atr_sl_mult,
            atr_tp_mult=atr_tp_mult,
            show_plot=show_plot,
        )
    )


@app.command()
def research(
    currency: str = typer.Option("DOGE", help="Crypto currency to backtest"),
    days: int = typer.Option(365, help="Number of days to backtest"),
    initial_cash: float = typer.Option(3_000.0, help="Initial cash in USDT"),
):
    """
    Run backtesting strategy for a given symbol.
    """
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=days)
    asyncio.run(
        backtesting_service.research(
            start_date=start_date, end_date=end_date, crypto_currency=currency, initial_cash=initial_cash
        )
    )


if __name__ == "__main__":
    app()
