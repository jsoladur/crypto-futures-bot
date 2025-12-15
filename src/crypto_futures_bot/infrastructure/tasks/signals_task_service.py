import asyncio
import logging
from dataclasses import fields
from typing import override

import pandas as pd
from aiogram import html
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from pyee.asyncio import AsyncIOEventEmitter

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.constants import SIGNALS_EVALUATION_RESULT_EVENT_NAME, SIGNALS_TASK_SERVICE_CRON_PATTERN
from crypto_futures_bot.domain.enums import (
    CandleStickEnum,
    MarketActionTypeEnum,
    PositionTypeEnum,
    PushNotificationTypeEnum,
    TaskTypeEnum,
)
from crypto_futures_bot.domain.vo import SignalsEvaluationResult, TrackedCryptoCurrencyItem
from crypto_futures_bot.domain.vo.candlestick_indicators import CandleStickIndicators
from crypto_futures_bot.infrastructure.adapters.futures_exchange.base import AbstractFuturesExchangeService
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo import AccountInfo, SymbolTicker
from crypto_futures_bot.infrastructure.services.crypto_technical_analysis_service import CryptoTechnicalAnalysisService
from crypto_futures_bot.infrastructure.services.market_signal_service import MarketSignalService
from crypto_futures_bot.infrastructure.services.push_notification_service import PushNotificationService
from crypto_futures_bot.infrastructure.services.tracked_crypto_currency_service import TrackedCryptoCurrencyService
from crypto_futures_bot.infrastructure.services.trade_now_service import TradeNowService
from crypto_futures_bot.infrastructure.tasks.base import AbstractTaskService
from crypto_futures_bot.interfaces.telegram.services.telegram_service import TelegramService

logger = logging.getLogger(__name__)


class SignalsTaskService(AbstractTaskService):
    def __init__(
        self,
        configuration_properties: ConfigurationProperties,
        telegram_service: TelegramService,
        push_notification_service: PushNotificationService,
        event_emitter: AsyncIOEventEmitter,
        scheduler: AsyncIOScheduler,
        tracked_crypto_currency_service: TrackedCryptoCurrencyService,
        futures_exchange_service: AbstractFuturesExchangeService,
        crypto_technical_analysis_service: CryptoTechnicalAnalysisService,
        trade_now_service: TradeNowService,
        market_signal_service: MarketSignalService,
    ) -> None:
        super().__init__(configuration_properties, scheduler, push_notification_service, telegram_service)
        self._event_emitter = event_emitter
        self._tracked_crypto_currency_service = tracked_crypto_currency_service
        self._futures_exchange_service = futures_exchange_service
        self._crypto_technical_analysis_service = crypto_technical_analysis_service
        self._trade_now_service = trade_now_service
        self._market_signal_service = market_signal_service
        self._job = self._create_job()

    @override
    async def start(self) -> None:
        """
        Start method does not do anything,
        this job will be running every time to collect buy/sell signals
        """

    @override
    async def stop(self) -> None:
        """
        Start method does not do anything,
        this job will be running every time to collect buy/sell signals
        """

    @override
    def get_task_type(self) -> TaskTypeEnum | None:
        return None

    @override
    async def _run(self) -> None:
        """
        Run the task
        """
        account_info = await self._futures_exchange_service.get_account_info()
        tracked_crypto_currencies = await self._tracked_crypto_currency_service.find_all()
        for tracked_crypto_currency in tracked_crypto_currencies:
            await self._eval_signals(tracked_crypto_currency=tracked_crypto_currency, account_info=account_info)

    @override
    def _get_job_trigger(self) -> CronTrigger | IntervalTrigger:  # pragma: no cover
        if self._configuration_properties.signals_run_via_cron_pattern:
            trigger = CronTrigger(
                minute=",".join([str(minute) for minute in SIGNALS_TASK_SERVICE_CRON_PATTERN]), hour="*"
            )
        else:
            trigger = IntervalTrigger(seconds=self._configuration_properties.job_interval_seconds)
        return trigger

    async def _eval_signals(
        self, tracked_crypto_currency: TrackedCryptoCurrencyItem, *, account_info: AccountInfo
    ) -> None:
        try:
            technical_analysis_df = await self._crypto_technical_analysis_service.get_technical_analysis(
                symbol=tracked_crypto_currency.to_symbol(account_info=account_info)
            )
            signals_evaluation_result, last_candle = await self._check_signals(
                tracked_crypto_currency=tracked_crypto_currency,
                technical_analysis_df=technical_analysis_df,
                account_info=account_info,
            )
            chat_ids = await self._push_notification_service.get_actived_subscription_by_type(
                notification_type=PushNotificationTypeEnum.SIGNALS
            )
            if chat_ids:
                await self._notify_signals(
                    signals_evaluation_result=signals_evaluation_result,
                    chat_ids=chat_ids,
                    account_info=account_info,
                    last_candle=last_candle,
                )
        except Exception as e:
            logger.error(f"Error evaluating signals for {tracked_crypto_currency}: {e}", exc_info=True)
            await self._notify_fatal_error_via_telegram(e)
        finally:
            self._event_emitter.emit(SIGNALS_EVALUATION_RESULT_EVENT_NAME, signals_evaluation_result)

    async def _check_signals(
        self,
        tracked_crypto_currency: TrackedCryptoCurrencyItem,
        technical_analysis_df: pd.DataFrame,
        account_info: AccountInfo,
    ) -> tuple[SignalsEvaluationResult, CandleStickIndicators]:
        prev_candle = await self._crypto_technical_analysis_service.get_candlestick_indicators(
            symbol=tracked_crypto_currency.to_symbol(account_info=account_info),
            index=CandleStickEnum.PREV,
            technical_analysis_df=technical_analysis_df,
        )
        last_candle = await self._crypto_technical_analysis_service.get_candlestick_indicators(
            symbol=tracked_crypto_currency.to_symbol(account_info=account_info),
            index=CandleStickEnum.LAST,
            technical_analysis_df=technical_analysis_df,
        )
        long_entry = self._is_long_entry(prev_candle=prev_candle, last_candle=last_candle)
        short_entry = self._is_short_entry(prev_candle=prev_candle, last_candle=last_candle)
        signals_evaluation_result = SignalsEvaluationResult(
            timestamp=last_candle.timestamp,
            crypto_currency=tracked_crypto_currency,
            long_entry=long_entry,
            long_exit=self._is_long_exit(prev_candle=prev_candle, last_candle=last_candle) if not long_entry else False,
            short_entry=short_entry,
            short_exit=self._is_short_exit(prev_candle=prev_candle, last_candle=last_candle)
            if not short_entry
            else False,
        )
        return signals_evaluation_result, last_candle

    async def _notify_signals(
        self,
        signals_evaluation_result: SignalsEvaluationResult,
        chat_ids: list[str],
        account_info: AccountInfo,
        last_candle: CandleStickIndicators,
    ) -> None:
        signals_field_names = [field.name for field in fields(signals_evaluation_result) if field.type is bool]
        for signals_field_name in signals_field_names:
            if getattr(signals_evaluation_result, signals_field_name):
                await self._notify_single_signal(
                    signals_evaluation_result,
                    is_long=signals_field_name.startswith("long"),
                    is_entry=signals_field_name.endswith("_entry"),
                    chat_ids=chat_ids,
                    account_info=account_info,
                    last_candle=last_candle,
                )

    async def _notify_single_signal(
        self,
        signals_evaluation_result: SignalsEvaluationResult,
        *,
        is_long: bool,
        is_entry: bool,
        chat_ids: list[str],
        account_info: AccountInfo,
        last_candle: CandleStickIndicators,
    ) -> None:
        current_market_action_type = MarketActionTypeEnum.ENTRY if is_entry else MarketActionTypeEnum.EXIT
        last_market_signal = await self._market_signal_service.find_last_market_signal(
            signals_evaluation_result.crypto_currency,
            position_type=PositionTypeEnum.LONG if is_long else PositionTypeEnum.SHORT,
            timeframe=signals_evaluation_result.timeframe,
        )
        if last_market_signal is None or last_market_signal.action_type != current_market_action_type:
            symbol_ticker = await self._futures_exchange_service.get_symbol_ticker(
                symbol=signals_evaluation_result.crypto_currency.to_symbol(account_info=account_info)
            )
            if is_entry:
                await self._notify_entry(
                    signals_evaluation_result=signals_evaluation_result,
                    is_long=is_long,
                    chat_ids=chat_ids,
                    account_info=account_info,
                    last_candle=last_candle,
                    symbol_ticker=symbol_ticker,
                )
            else:
                await self._notify_exit(
                    signals_evaluation_result=signals_evaluation_result,
                    is_long=is_long,
                    chat_ids=chat_ids,
                    account_info=account_info,
                    symbol_ticker=symbol_ticker,
                )

    async def _notify_entry(
        self,
        signals_evaluation_result: SignalsEvaluationResult,
        *,
        is_long: bool,
        chat_ids: list[str],
        account_info: AccountInfo,
        last_candle: CandleStickIndicators,
        symbol_ticker: SymbolTicker,
    ) -> None:
        trade_now_hints = await self._trade_now_service.get_trade_now_hints(signals_evaluation_result.crypto_currency)
        position_hints = trade_now_hints.long if is_long else trade_now_hints.short
        icon = "🟢" if is_long else "🔴"
        signal_type = "LONG" if is_long else "SHORT"
        message_lines = [
            f"{icon} {html.bold(signal_type + ' ENTRY SIGNAL')} for {html.code(signals_evaluation_result.crypto_currency.currency)} {icon}",  # noqa: E501
            "================================",
            f"🏷️ {html.bold('Symbol:')} {html.code(signals_evaluation_result.crypto_currency.to_symbol(account_info=account_info))}",  # noqa: E501
            f"🎯 {html.bold('Entry Price:')} {html.code(position_hints.entry_price)} {account_info.currency_code}",
            f"⚖️ {html.bold('Break Even Price:')} {html.code(position_hints.break_even_price)} {account_info.currency_code}",  # noqa: E501
            f"🛑 {html.bold('Stop Loss:')} {html.code(position_hints.stop_loss_price)} {account_info.currency_code} ({trade_now_hints.stop_loss_percent_value} %)",  # noqa: E501
            f"💰 {html.bold('Take Profit:')} {html.code(position_hints.take_profit_price)} {account_info.currency_code} ({trade_now_hints.take_profit_percent_value} %)",  # noqa: E501
        ]
        message = "\n".join(message_lines)
        await self._notify_alert(telegram_chat_ids=chat_ids, body_message=message)

    async def _notify_exit(
        self,
        signals_evaluation_result: SignalsEvaluationResult,
        *,
        is_long: bool,
        chat_ids: list[str],
        account_info: AccountInfo,
        symbol_ticker: SymbolTicker,
    ) -> None:
        icon = "🟦" if is_long else "🟧"
        signal_type = "LONG" if is_long else "SHORT"
        exit_price = symbol_ticker.bid_or_close if is_long else symbol_ticker.ask_or_close
        message_lines = [
            f"{icon} {html.bold(signal_type + ' EXIT SIGNAL')} for {html.code(signals_evaluation_result.crypto_currency.currency)} {icon}",  # noqa: E501
            "================================",
            f"🏷️ {html.bold('Symbol:')} {html.code(signals_evaluation_result.crypto_currency.to_symbol(account_info=account_info))}",  # noqa: E501
            f"↩️ {html.bold('Exit Price:')} {html.code(exit_price)} {account_info.currency_code}",
        ]
        message = "\n".join(message_lines)
        await self._notify_alert(telegram_chat_ids=chat_ids, body_message=message)

    def _is_long_entry(self, prev_candle: CandleStickIndicators, last_candle: CandleStickIndicators) -> bool:
        # TREND: Price is above the baseline (Safety)
        trend_ok = last_candle.closing_price > last_candle.ema50
        # TRIGGER: Stoch Cross Up
        stoch_cross = (
            prev_candle.stoch_rsi_k <= prev_candle.stoch_rsi_d and last_candle.stoch_rsi_k > last_candle.stoch_rsi_d
        )
        # FILTER: Must be Oversold (Buying the dip)
        stoch_condition = prev_candle.stoch_rsi_k < self._configuration_properties.long_entry_oversold_threshold
        # MOMENTUM: Histogram is ticking up (Recovery started)
        macd_improving = last_candle.macd_hist > prev_candle.macd_hist
        return trend_ok and stoch_cross and stoch_condition and macd_improving

    def _is_long_exit(self, prev_candle: CandleStickIndicators, last_candle: CandleStickIndicators) -> bool:
        # HARD EXIT: Trend Broken (Price falls below EMA50)
        trend_broken = last_candle.closing_price < last_candle.ema50
        # SOFT EXIT: Take Profit on Overbought
        stoch_take_profit = (
            prev_candle.stoch_rsi_k >= prev_candle.stoch_rsi_d
            and last_candle.stoch_rsi_k < last_candle.stoch_rsi_d
            and prev_candle.stoch_rsi_k > self._configuration_properties.long_exit_overbought_threshold
        )
        # MOMENTUM EXIT: Only exit if momentum is failing
        momentum_failure = last_candle.macd_hist < 0 and last_candle.macd_hist < prev_candle.macd_hist
        return trend_broken or stoch_take_profit or momentum_failure

    def _is_short_entry(self, prev_candle: CandleStickIndicators, last_candle: CandleStickIndicators) -> bool:
        trend_ok = last_candle.closing_price < last_candle.ema50
        stoch_cross = (
            prev_candle.stoch_rsi_k >= prev_candle.stoch_rsi_d and last_candle.stoch_rsi_k < last_candle.stoch_rsi_d
        )
        stoch_condition = prev_candle.stoch_rsi_k > self._configuration_properties.short_entry_overbought_threshold
        macd_worsening = last_candle.macd_hist < prev_candle.macd_hist
        return trend_ok and stoch_cross and stoch_condition and macd_worsening

    def _is_short_exit(self, prev_candle: CandleStickIndicators, last_candle: CandleStickIndicators) -> bool:
        # HARD EXIT: Price breaks above EMA50
        trend_broken = last_candle.closing_price > last_candle.ema50
        # SOFT EXIT: Take Profit on Oversold
        stoch_take_profit = (
            prev_candle.stoch_rsi_k <= prev_candle.stoch_rsi_d
            and last_candle.stoch_rsi_k > last_candle.stoch_rsi_d
            and prev_candle.stoch_rsi_k < self._configuration_properties.short_exit_oversold_threshold
        )
        # MOMENTUM EXIT: Only exit if momentum is failing
        momentum_failure = last_candle.macd_hist > 0 and last_candle.macd_hist > prev_candle.macd_hist
        return trend_broken or stoch_take_profit or momentum_failure

    async def _notify_alert(self, telegram_chat_ids: list[str], body_message: str) -> None:
        await asyncio.gather(
            *[
                self._telegram_service.send_message(chat_id=tg_chat_id, text=body_message)
                for tg_chat_id in telegram_chat_ids
            ]
        )
