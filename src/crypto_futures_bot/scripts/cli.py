import asyncio
import logging
from datetime import UTC, datetime, timedelta

import typer

from crypto_futures_bot.scripts.config import Container
from crypto_futures_bot.scripts.services import BacktestingService

# Configure basic logging for CLI
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
            show_plot=show_plot,
        )
    )


if __name__ == "__main__":
    app()
