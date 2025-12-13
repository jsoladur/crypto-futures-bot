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
from crypto_futures_bot.constants import (
    DEFAULT_LONG_ENTRY_OVERSOLD_THRESHOLD,
    DEFAULT_LONG_EXIT_OVERBOUGHT_THRESHOLD,
    DEFAULT_SHORT_ENTRY_OVERBOUGHT_THRESHOLD,
    SIGNALS_EVALUATION_RESULT_EVENT_NAME,
    SIGNALS_TASK_SERVICE_CRON_PATTERN,
)
from crypto_futures_bot.domain.enums import CandleStickEnum, PushNotificationTypeEnum, TaskTypeEnum
from crypto_futures_bot.domain.vo import SignalsEvaluationResult, TrackedCryptoCurrencyItem
from crypto_futures_bot.domain.vo.candlestick_indicators import CandleStickIndicators
from crypto_futures_bot.infrastructure.adapters.futures_exchange.base import AbstractFuturesExchangeService
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo import AccountInfo, SymbolTicker
from crypto_futures_bot.infrastructure.services.crypto_technical_analysis_service import CryptoTechnicalAnalysisService
from crypto_futures_bot.infrastructure.services.orders_analytics_service import OrdersAnalyticsService
from crypto_futures_bot.infrastructure.services.push_notification_service import PushNotificationService
from crypto_futures_bot.infrastructure.services.tracked_crypto_currency_service import TrackedCryptoCurrencyService
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
        orders_analytics_service: OrdersAnalyticsService,
        crypto_technical_analysis_service: CryptoTechnicalAnalysisService,
    ) -> None:
        super().__init__(configuration_properties, scheduler, push_notification_service, telegram_service)
        self._event_emitter = event_emitter
        self._tracked_crypto_currency_service = tracked_crypto_currency_service
        self._futures_exchange_service = futures_exchange_service
        self._orders_analytics_service = orders_analytics_service
        self._crypto_technical_analysis_service = crypto_technical_analysis_service
        self._last_signal_evalutation_result_cache: dict[str, SignalsEvaluationResult] = {}
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
            is_new_signals, *_ = self._is_new_signals(signals_evaluation_result)
            if is_new_signals:
                try:
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
                finally:
                    self._event_emitter.emit(SIGNALS_EVALUATION_RESULT_EVENT_NAME, signals_evaluation_result)
            else:  # pragma: no cover
                logger.info("Calculated signals were already notified previously!")
        except Exception as e:
            logger.error(f"Error evaluating signals for {tracked_crypto_currency}: {e}", exc_info=True)
            await self._notify_fatal_error_via_telegram(e)

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
        symbol_market_config = await self._futures_exchange_service.get_symbol_market_config(
            crypto_currency=signals_evaluation_result.crypto_currency.currency
        )
        entry_price = symbol_ticker.ask_or_close if is_long else symbol_ticker.bid_or_close
        stop_loss_percent_value = self._orders_analytics_service.get_stop_loss_percent_value(
            avg_entry_price=entry_price,
            last_candlestick_indicators=last_candle,
            symbol_market_config=symbol_market_config,
        )
        take_profit_percent_value = self._orders_analytics_service.get_take_profit_percent_value(
            avg_entry_price=entry_price,
            last_candlestick_indicators=last_candle,
            symbol_market_config=symbol_market_config,
        )
        stop_loss_price = self._orders_analytics_service.get_stop_loss_price(
            entry_price=entry_price,
            stop_loss_percent_value=stop_loss_percent_value,
            is_long=is_long,
            symbol_market_config=symbol_market_config,
        )
        take_profit_price = self._orders_analytics_service.get_take_profit_price(
            entry_price=entry_price,
            take_profit_percent_value=take_profit_percent_value,
            is_long=is_long,
            symbol_market_config=symbol_market_config,
        )
        break_even_price = self._orders_analytics_service.calculate_break_even_price(
            entry_price=entry_price, symbol_market_config=symbol_market_config, is_long=is_long
        )
        icon = "🟢" if is_long else "🔴"
        signal_type = "LONG" if is_long else "SHORT"
        message_lines = [
            f"{icon} {html.bold(signal_type + ' ENTRY SIGNAL')} for {html.code(signals_evaluation_result.crypto_currency.currency)} {icon}",  # noqa: E501
            "================",
            f"🏷️ {html.bold('Symbol:')} {html.code(signals_evaluation_result.crypto_currency.to_symbol(account_info=account_info))}",  # noqa: E501
            f"🎯 {html.bold('Entry Price:')} {html.code(entry_price)} {account_info.currency_code}",
            f"⚖️ {html.bold('Break Even Price:')} {html.code(break_even_price)} {account_info.currency_code}",
            f"🛑 {html.bold('Stop Loss:')} {html.code(stop_loss_price)} {account_info.currency_code} ({stop_loss_percent_value} %)",  # noqa: E501
            f"💰 {html.bold('Take Profit:')} {html.code(take_profit_price)} {account_info.currency_code} ({take_profit_percent_value} %)",  # noqa: E501
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
            "================",
            f"🏷️ {html.bold('Symbol:')} {html.code(signals_evaluation_result.crypto_currency.to_symbol(account_info=account_info))}",  # noqa: E501
            f"↩️ {html.bold('Exit Price:')} {html.code(exit_price)} {account_info.currency_code}",
        ]
        message = "\n".join(message_lines)
        await self._notify_alert(telegram_chat_ids=chat_ids, body_message=message)

    def _is_new_signals(self, current_signals: SignalsEvaluationResult) -> tuple[bool, SignalsEvaluationResult | None]:
        is_new_signals = current_signals.cache_key not in self._last_signal_evalutation_result_cache
        previous_signals: SignalsEvaluationResult | None = None
        if not is_new_signals:  # pragma: no cover
            previous_signals = self._last_signal_evalutation_result_cache[current_signals.cache_key]
            is_new_signals = previous_signals != current_signals
            logger.info(f"Previous ({repr(previous_signals)}) != Current ({repr(current_signals)}) ? {is_new_signals}")
        self._last_signal_evalutation_result_cache[current_signals.cache_key] = current_signals
        return is_new_signals, previous_signals

    def _is_long_entry(self, prev_candle: CandleStickIndicators, last_candle: CandleStickIndicators) -> bool:
        trend_ok = last_candle.closing_price > last_candle.ema50
        stoch_cross = (
            prev_candle.stoch_rsi_k <= prev_candle.stoch_rsi_d and last_candle.stoch_rsi_k > last_candle.stoch_rsi_d
        )
        stoch_condition = prev_candle.stoch_rsi_k < DEFAULT_LONG_ENTRY_OVERSOLD_THRESHOLD
        macd_improving = last_candle.macd_hist > prev_candle.macd_hist
        return trend_ok and stoch_cross and stoch_condition and macd_improving

    def _is_long_exit(self, prev_candle: CandleStickIndicators, last_candle: CandleStickIndicators) -> bool:
        # 1. HARD EXIT: Trend Broken (Price falls below EMA50)
        trend_broken = last_candle.closing_price < last_candle.ema50
        # 2. SOFT EXIT: Take Profit on Overbought
        stoch_take_profit = (
            prev_candle.stoch_rsi_k >= prev_candle.stoch_rsi_d
            and last_candle.stoch_rsi_k < last_candle.stoch_rsi_d
            and prev_candle.stoch_rsi_k > DEFAULT_LONG_EXIT_OVERBOUGHT_THRESHOLD
        )
        # 3. MOMENTUM EXIT: Only exit if momentum is failing
        momentum_failure = last_candle.macd_hist < 0 and last_candle.macd_hist < prev_candle.macd_hist
        return trend_broken or stoch_take_profit or momentum_failure

    def _is_short_entry(self, prev_candle: CandleStickIndicators, last_candle: CandleStickIndicators) -> bool:
        trend_ok = last_candle.closing_price < last_candle.ema50
        stoch_cross = (
            prev_candle.stoch_rsi_k >= prev_candle.stoch_rsi_d and last_candle.stoch_rsi_k < last_candle.stoch_rsi_d
        )
        stoch_condition = prev_candle.stoch_rsi_k > DEFAULT_SHORT_ENTRY_OVERBOUGHT_THRESHOLD
        macd_worsening = last_candle.macd_hist < prev_candle.macd_hist
        return trend_ok and stoch_cross and stoch_condition and macd_worsening

    def _is_short_exit(self, prev_candle: CandleStickIndicators, last_candle: CandleStickIndicators) -> bool:
        # 1. HARD EXIT: Price breaks above EMA50
        trend_broken = last_candle.closing_price > last_candle.ema50
        # 2. SOFT EXIT: Take Profit on Oversold
        stoch_take_profit = (
            prev_candle.stoch_rsi_k <= prev_candle.stoch_rsi_d
            and last_candle.stoch_rsi_k > last_candle.stoch_rsi_d
            and prev_candle.stoch_rsi_k < 0.20
        )
        # 3. MOMENTUM EXIT: Only exit if momentum is failing
        momentum_failure = last_candle.macd_hist > 0 and last_candle.macd_hist > prev_candle.macd_hist
        return trend_broken or stoch_take_profit or momentum_failure

    async def _notify_alert(self, telegram_chat_ids: list[str], body_message: str) -> None:
        await asyncio.gather(
            *[
                self._telegram_service.send_message(chat_id=tg_chat_id, text=body_message)
                for tg_chat_id in telegram_chat_ids
            ]
        )
