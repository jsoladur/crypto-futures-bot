from aiogram import html

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.domain.vo import TradeNowHints
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

    def format_trade_now_hints(self, hints: TradeNowHints) -> str:
        ticker = hints.ticker
        fiat_currency = ticker.quote_asset
        header = [
            "==========================",
            f"🚀 TRADE NOW HINTS :: {html.bold(ticker.base_asset)} 🚀",
            "==========================",
        ]
        params_lines = [
            html.bold("⚙️ SL/TP Parameters:"),
            f"   🔥 {html.italic('Last Price')} = {html.code(f'{ticker.close:.4f} {fiat_currency}')}",
            f"   🚏 {html.bold('Stop Loss')} = {hints.stop_loss_percent_value}%",
            f"   🏆 {html.bold('Take Profit')} = {hints.take_profit_percent_value}%",
        ]
        long_lines = [
            html.bold("📈 LONG Position:"),
            f"   🎯 {html.italic('Entry')} = {html.code(hints.long.entry_price)} {fiat_currency}",
            f"   🔴 {html.italic('Stop Loss')} = {html.code(hints.long.stop_loss_price)} {fiat_currency}",
            f"   🟢 {html.italic('Take Profit')} = {html.code(hints.long.take_profit_price)} {fiat_currency}",
        ]
        short_lines = [
            html.bold("📉 SHORT Position:"),
            f"   🎯 {html.italic('Entry')} = {html.code(hints.short.entry_price)} {fiat_currency}",
            f"   🔴 {html.italic('Stop Loss')} = {html.code(hints.short.stop_loss_price)} {fiat_currency}",
            f"   🟢 {html.italic('Take Profit')} = {html.code(hints.short.take_profit_price)} {fiat_currency}",
        ]
        message = "\n".join(header + params_lines + long_lines + short_lines)
        return message
