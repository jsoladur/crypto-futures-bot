from aiogram import html

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo import PortfolioBalance, SymbolTicker


class MessagesFormatter:
    def __init__(self, configuration_properties: ConfigurationProperties):
        self._configuration_properties = configuration_properties

    def format_prices(self, tickers: list[SymbolTicker]) -> str:
        message_lines = ["===========================", "💵 CURRENT PRICES 💵", "==========================="]
        for ticker in tickers:
            message_lines.append(
                f"🔥 {html.bold(ticker.base_asset.upper())} :: {html.bold(str(ticker.close) + ' ' + ticker.quote_asset.upper())}"  # noqa: E501
            )
        ret = "\n".join(message_lines)
        return ret

    def format_portfolio_balance(self, portfolio_balance: PortfolioBalance) -> str:
        message_lines = ["===========================", "🏦  PORTFOLIO BALANCE 🏦", "==========================="]
        message_lines.append(
            html.italic(
                f"📊  {html.bold('Total')}: {portfolio_balance.total_balance} {portfolio_balance.currency_code}"  # noqa: E501
            )
        )
        ret = "\n".join(message_lines)
        return ret
