import asyncio
import logging
from datetime import UTC, datetime, timedelta

import typer

from crypto_futures_bot.scripts.services import BacktestingService

# Configure basic logging for CLI
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

app = typer.Typer()


@app.command()
def backtest(
    symbol: str = typer.Option("BTC/USDT:USDT", help="Symbol to backtest"),
    days: int = typer.Option(365, help="Number of days to backtest"),
    initial_cash: float = typer.Option(3000.0, help="Initial cash in USDT"),
):
    """
    Run backtesting strategy for a given symbol.
    """
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=days)

    service = BacktestingService(start_date=start_date, end_date=end_date, symbol=symbol, initial_cash=initial_cash)
    asyncio.run(service.run())


if __name__ == "__main__":
    app()
