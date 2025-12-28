from datetime import datetime
from zoneinfo import ZoneInfo

import pydash
from aiogram import html

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.domain.enums import MarketActionTypeEnum, PositionOpenTypeEnum, PositionTypeEnum
from crypto_futures_bot.domain.vo import (
    MarketSignalItem,
    PositionHints,
    PositionMetrics,
    SignalParametrizationItem,
    TradeNowHints,
)
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo import (
    AccountInfo,
    PortfolioBalance,
    SymbolMarketConfig,
    SymbolTicker,
)


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
        message_lines = [
            "===========================",
            "🏦  PORTFOLIO BALANCE 🏦",
            "===========================",
            f"📊  Spot Balance: {html.italic(f'{portfolio_balance.spot_balance} {portfolio_balance.currency_code}')}",
            f"📊  Futures Balance: {html.italic(f'{portfolio_balance.futures_balance} {portfolio_balance.currency_code}')}",  # noqa: E501
            "------------------------------------------------------",
            f"📊  {html.bold('TOTAL')}: {html.bold(f'{portfolio_balance.total_balance} {portfolio_balance.currency_code}')}",  # noqa: E501
        ]
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
            f"    🔥 {html.italic('Last Price')} = {html.code(ticker.close)} {fiat_currency}",
            f"    🚏 {html.bold('Stop Loss')} = {hints.stop_loss_percent_value}%",
            f"    🏆 {html.bold('Take Profit')} = {hints.take_profit_percent_value}%",
            "",
        ]
        long_lines = [html.bold("📈 LONG Position:"), *self._format_position_hints(hints.long, fiat_currency), ""]
        short_lines = [html.bold("📉 SHORT Position:"), *self._format_position_hints(hints.short, fiat_currency)]
        message = "\n".join(header + params_lines + long_lines + short_lines)
        return message

    def format_market_signals_message(
        self,
        *,
        currency: str,
        account_info: AccountInfo,
        symbol_market_config: SymbolMarketConfig,
        market_signals: list[MarketSignalItem],
    ) -> str:
        header = [
            "==========================",
            f"🚦 MARKET SIGNALS :: {html.bold(currency)} 🚦",
            "==========================",
        ]
        signals_lines = []
        for idx, market_signal in enumerate(market_signals):
            additional_info_lines = []
            if market_signal.action_type == MarketActionTypeEnum.ENTRY:
                icon = "🟢" if market_signal.position_type == PositionTypeEnum.LONG else "🔴"
                additional_info_lines.extend(
                    [
                        f"🎯 {html.bold('Entry Price:')} {html.code(round(market_signal.entry_price, ndigits=symbol_market_config.price_precision))} {account_info.currency_code}",  # noqa: E501
                        f"⚖️ {html.bold('Break Even Price:')} {html.code(round(market_signal.break_even_price, ndigits=symbol_market_config.price_precision))} {account_info.currency_code}",  # noqa: E501
                        f"🛑 {html.bold('Stop Loss:')} {html.code(round(market_signal.stop_loss_price, ndigits=symbol_market_config.price_precision))} {account_info.currency_code} ({market_signal.stop_loss_percent_value} %)",  # noqa: E501
                        f"💰 {html.bold('Take Profit:')} {html.code(round(market_signal.take_profit_price, ndigits=symbol_market_config.price_precision))} {account_info.currency_code} ({market_signal.take_profit_percent_value} %)",  # noqa: E501
                    ]
                )
            elif market_signal.action_type == MarketActionTypeEnum.EXIT:
                icon = "🟦" if market_signal.position_type == PositionTypeEnum.LONG else "🟧"
            else:
                icon = "🟡"
            signals_lines.extend(
                [
                    f"{icon} {html.bold(market_signal.position_type.value)} {html.bold(market_signal.action_type.value)}",  # noqa: E501
                    "================================",
                    f"🗓️ {html.bold('Timestamp:')} {self._format_timestamp_with_timezone(market_signal.timestamp)}",  # noqa: E501
                    *additional_info_lines,
                ]
            )
            if idx + 1 < len(market_signals):
                signals_lines.append("")
        message = "\n".join(header + signals_lines)
        return message

    def format_position_metrics(self, position_metrics: PositionMetrics) -> str:
        position = position_metrics.position
        ticker = position_metrics.ticker
        icon = "🟢" if position.position_type == PositionTypeEnum.LONG else "🔴"
        margin_icon = "🔒" if position.open_type == PositionOpenTypeEnum.ISOLATED else "🔗"
        message_lines = [
            f"{icon} {html.bold(position.position_type.value.upper())} {html.code(position.symbol)} || {margin_icon} {html.bold(pydash.start_case(position.open_type.value))} {html.bold(position.leverage)}x",  # noqa: E501
            "====================================================",
            f"🔥 {html.bold('Current Price')} ({html.bold('Bid' if position.position_type == PositionTypeEnum.LONG else 'Ask')}) = {ticker.bid_or_close if position.position_type == PositionTypeEnum.LONG else ticker.ask_or_close} {ticker.quote_asset}",  # noqa: E501
            f"🏦 {html.bold('Unrealized PnL')} = {'+' if position_metrics.unrealised_pnl > 0 else '-'}{abs(position_metrics.unrealised_pnl)} {ticker.quote_asset} [{position_metrics.unrealised_pnl_ratio}%]",  # noqa: E501
            f"🤑 {html.bold('Unrealized Net Revenue')} = {'+' if position_metrics.unrealised_net_revenue > 0 else '-'}{abs(position_metrics.unrealised_net_revenue)} {ticker.quote_asset}",  # noqa: E501
            "----------------------------------------------------",
            f"💰 {html.bold('Notional')} = {position_metrics.notional} {ticker.quote_asset}",
            f"🧱 {html.bold('Initial Margin')} = {position_metrics.initial_margin} {ticker.quote_asset}",
            "----------------------------------------------------",
            f"🎯 {html.bold('Avg. Entry Price')} = {position.entry_price} {ticker.quote_asset}",
            f"☠️ {html.bold('Liq. Price')} = {position.liquidation_price} {ticker.quote_asset}",
            "----------------------------------------------------",
            # Risk controls
            f"🛑 {html.bold('Stop Loss')} = {position.stop_loss_price} {ticker.quote_asset}"
            if position.stop_loss_price is not None
            else "🛑 Stop Loss = —",
            f"🎉 {html.bold('Take Profit')} = {position.take_profit_price} {ticker.quote_asset}"
            if position.take_profit_price is not None
            else "🎉 Take Profit = —",
            "----------------------------------------------------",
            f"💸 {html.bold('Fees Paid')} = {position.fee} {ticker.quote_asset}",
        ]
        if position_metrics.profit_factor is not None:
            message_lines.append(
                f"⚖️ {html.bold('Profit Factor')} = {position_metrics.profit_factor} {ticker.quote_asset}"  # noqa: E501
            )
        if position_metrics.potential_profit_at_tp is not None:
            message_lines.append(
                f"🟢 {html.bold('Potential Profit at TP')} = {'+' if position_metrics.potential_profit_at_tp > 0 else '-'}{abs(position_metrics.potential_profit_at_tp)} {ticker.quote_asset}"  # noqa: E501
            )
        if position_metrics.potential_loss_at_sl is not None:
            message_lines.append(
                f"🔴 {html.bold('Potential Loss at SL')} = {'+' if position_metrics.potential_loss_at_sl > 0 else '-'}{abs(position_metrics.potential_loss_at_sl)} {ticker.quote_asset}"  # noqa: E501
            )
        return "\n".join(message_lines)

    def format_signal_parametrization_message(self, signal_parametrization: SignalParametrizationItem) -> str:
        message_lines = [
            f"📉 Long Entry Oversold Threshold = {html.code(signal_parametrization.long_entry_oversold_threshold)}",
            f"📈 Short Entry Overbought Threshold = {html.code(signal_parametrization.short_entry_overbought_threshold)}",  # noqa: E501
            f"🛡️ SL ATR x = {html.code(signal_parametrization.atr_sl_mult)}",
            f"🏁 TP ATR x = {html.code(signal_parametrization.atr_tp_mult)}",
        ]
        ret = "\n".join(message_lines)
        return ret

    def _format_position_hints(self, position_hints: PositionHints, fiat_currency: str) -> list[str]:
        return [
            f"    🛡️ Safe Trade? {self._get_safety_icon_and_message(position_hints.is_safe)}",
            "     --------------------------------",
            f"    🎯 {html.bold('Entry')} = {html.code(position_hints.entry_price)} {fiat_currency}",
            f"    💰 {html.bold('Margin')} = {html.code(position_hints.margin)} {fiat_currency}",  # noqa: E501
            f"    ⚡ {html.bold('Leverage')} = x{html.code(f'{position_hints.leverage}')}",
            f"    🛑 {html.bold('STOP LOSS')} = {html.code(position_hints.stop_loss_price)} {fiat_currency}",
            f"    🏆 {html.bold('TAKE PROFIT')} = {html.code(position_hints.take_profit_price)} {fiat_currency}",
            "     --------------------------------",
            f"    ⚖️ {html.italic('Break Even')} = {html.code(position_hints.break_even_price)} {fiat_currency}",
            f"    ✳️ {html.italic('Move SL to Break Even')} = {html.code(position_hints.move_sl_to_break_even_price)} {fiat_currency}",  # noqa: E501
            f"    ☝️ {html.italic('Move SL to First Target Profit')} = {html.code(position_hints.move_sl_to_first_target_profit_price)} {fiat_currency}",  # noqa: E501
            "     --------------------------------",
            f"    📦 {html.bold('Notional Size')} = {html.bold(position_hints.notional_size)} {fiat_currency}",
            f"    ☠️ {html.bold('LIQUIDATION PRICE')} = {html.code(position_hints.liquidation_price)} {fiat_currency}",  # noqa: E501
            f"    🟢 {html.bold('Profit at TP')} = {html.code(f'+{position_hints.potential_profit}')} {fiat_currency}",  # noqa: E501
            f"    🔴 {html.bold('Losses at SL')} = {html.code(f'-{position_hints.potential_loss}')} {fiat_currency}",  # noqa: E501
        ]

    def _get_safety_icon_and_message(self, is_safe: bool) -> str:
        return "✅ YES" if is_safe else "❌ NO (Liquidation Risk!)"

    def _format_timestamp_with_timezone(self, timestamp: datetime, *, zoneinfo: str = "Europe/Madrid") -> str:
        return timestamp.astimezone(ZoneInfo(zoneinfo)).strftime("%d-%m-%Y %H:%M")
