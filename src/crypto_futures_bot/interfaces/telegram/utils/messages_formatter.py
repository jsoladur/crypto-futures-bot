from aiogram import html

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo import PortfolioBalance


class MessagesFormatter:
    def __init__(self, configuration_properties: ConfigurationProperties):
        self._configuration_properties = configuration_properties

    @staticmethod
    def format_portfolio_balance(portfolio_balance: PortfolioBalance) -> str:
        message_lines = ["===========================", "🪙 PORTFOLIO BALANCE 🪙", "==========================="]
        message_lines.append(
            html.italic(
                f"📊  {html.bold('Total')}: {portfolio_balance.total_balance} {portfolio_balance.currency_code}"  # noqa: E501
            )
        )
        ret = "\n".join(message_lines)
        return ret
