import logging
from typing import override

import pandas as pd
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from pyee.asyncio import AsyncIOEventEmitter

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.constants import SIGNALS_EVALUATION_RESULT_EVENT_NAME, SIGNALS_TASK_SERVICE_CRON_PATTERN
from crypto_futures_bot.domain.enums import CandleStickEnum, PushNotificationTypeEnum, TaskTypeEnum
from crypto_futures_bot.domain.vo import SignalsEvaluationResult
from crypto_futures_bot.domain.vo.candlestick_indicators import CandleStickIndicators
from crypto_futures_bot.infrastructure.adapters.futures_exchange.base import AbstractFuturesExchangeService
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo import AccountInfo
from crypto_futures_bot.infrastructure.services.crypto_technical_analysis_service import CryptoTechnicalAnalysisService
from crypto_futures_bot.infrastructure.services.push_notification_service import PushNotificationService
from crypto_futures_bot.infrastructure.services.tracked_crypto_currency_service import TrackedCryptoCurrencyService
from crypto_futures_bot.infrastructure.tasks.base import AbstractTaskService
from crypto_futures_bot.interfaces.telegram.services.telegram_service import TelegramService
from crypto_futures_bot.interfaces.telegram.services.vo.tracked_crypto_currency_item import TrackedCryptoCurrencyItem

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
    ) -> None:
        super().__init__(configuration_properties, scheduler, push_notification_service, telegram_service)
        self._event_emitter = event_emitter
        self._tracked_crypto_currency_service = tracked_crypto_currency_service
        self._futures_exchange_service = futures_exchange_service
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
            signals_evaluation_result = await self._check_signals(
                tracked_crypto_currency=tracked_crypto_currency,
                technical_analysis_df=technical_analysis_df,
                account_info=account_info,
            )
            is_new_signals, previous_signals = self._is_new_signals(signals_evaluation_result)
            if is_new_signals:
                try:
                    chat_ids = await self._push_notification_service.get_actived_subscription_by_type(
                        notification_type=PushNotificationTypeEnum.SIGNALS
                    )
                    if chat_ids:
                        await self._notify_signals_via_telegram(
                            signals_evaluation_result=signals_evaluation_result,
                            previous_signals=previous_signals,
                            chat_ids=chat_ids,
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
    ) -> SignalsEvaluationResult:
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
        long_exit = self._is_long_exit(prev_candle=prev_candle, last_candle=last_candle)
        short_entry = self._is_short_entry(prev_candle=prev_candle, last_candle=last_candle)
        short_exit = self._is_short_exit(prev_candle=prev_candle, last_candle=last_candle)
        return SignalsEvaluationResult(
            timestamp=last_candle.timestamp,
            symbol=tracked_crypto_currency.to_symbol(account_info=account_info),
            long_entry=long_entry,
            long_exit=long_exit,
            short_entry=short_entry,
            short_exit=short_exit,
        )

    async def _notify_signals_via_telegram(
        self,
        signals_evaluation_result: SignalsEvaluationResult,
        previous_signals: SignalsEvaluationResult | None,
        chat_ids: list[str],
    ) -> None:
        raise NotImplementedError("To be implemented!")

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
        return (
            last_candle.closing_price > last_candle.ema50  # Closing price is above the 50-period EMA
            and last_candle.macd_hist > 0  # MACD histogram is positive
            and last_candle.macd_hist > prev_candle.macd_hist  # MACD histogram is increasing
            and prev_candle.stoch_rsi_k <= prev_candle.stoch_rsi_d  # K < D (cross)
            and last_candle.stoch_rsi_k > last_candle.stoch_rsi_d  # K > D (cross)
            and prev_candle.stoch_rsi_k < 0.20  # oversold area
        )

    def _is_long_exit(self, prev_candle: CandleStickIndicators, last_candle: CandleStickIndicators) -> bool:
        return (
            last_candle.macd_hist < 0  # MACD histogram is negative
            and last_candle.macd_hist < prev_candle.macd_hist  # MACD histogram is decreasing
            and prev_candle.stoch_rsi_k >= prev_candle.stoch_rsi_d  # K > D (cross)
            and last_candle.stoch_rsi_k < last_candle.stoch_rsi_d  # K < D (cross)
            and prev_candle.stoch_rsi_k > 0.80  # overbought area
        )

    def _is_short_entry(self, prev_candle: CandleStickIndicators, last_candle: CandleStickIndicators) -> bool:
        return (
            last_candle.closing_price < last_candle.ema50  # Closing price is below the 50-period EMA
            and last_candle.macd_hist < 0  # MACD histogram is negative
            and last_candle.macd_hist < prev_candle.macd_hist  # MACD histogram is decreasing
            and prev_candle.stoch_rsi_k >= prev_candle.stoch_rsi_d  # K > D (cross)
            and last_candle.stoch_rsi_k < last_candle.stoch_rsi_d  # K < D (cross)
            and prev_candle.stoch_rsi_k > 0.80  # overbought area
        )

    def _is_short_exit(self, prev_candle: CandleStickIndicators, last_candle: CandleStickIndicators) -> bool:
        return (
            last_candle.macd_hist > 0  # MACD histogram is positive
            and last_candle.macd_hist > prev_candle.macd_hist  # MACD histogram is increasing
            and prev_candle.stoch_rsi_k <= prev_candle.stoch_rsi_d  # K < D (cross)
            and last_candle.stoch_rsi_k > last_candle.stoch_rsi_d  # K > D (cross)
            and prev_candle.stoch_rsi_k < 0.20  # oversold area
        )
