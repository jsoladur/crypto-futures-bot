import logging
from typing import override

import pandas as pd
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.constants import SIGNALS_TASK_SERVICE_CRON_PATTERN
from crypto_futures_bot.domain.enums import CandleStickEnum, TaskTypeEnum
from crypto_futures_bot.domain.vo import SignalsEvaluationResult
from crypto_futures_bot.infrastructure.adapters.futures_exchange.base import AbstractFuturesExchangeService
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo import AccountInfo
from crypto_futures_bot.infrastructure.services.crypto_technical_analysis_service import CryptoTechnicalAnalysisService
from crypto_futures_bot.infrastructure.services.tracked_crypto_currency_service import TrackedCryptoCurrencyService
from crypto_futures_bot.infrastructure.tasks.base import AbstractTaskService
from crypto_futures_bot.interfaces.telegram.services.vo.tracked_crypto_currency_item import TrackedCryptoCurrencyItem

logger = logging.getLogger(__name__)


class SignalsTaskService(AbstractTaskService):
    def __init__(
        self,
        configuration_properties: ConfigurationProperties,
        scheduler: AsyncIOScheduler,
        tracked_crypto_currency_service: TrackedCryptoCurrencyService,
        futures_exchange_service: AbstractFuturesExchangeService,
        crypto_technical_analysis_service: CryptoTechnicalAnalysisService,
    ) -> None:
        super().__init__(configuration_properties, scheduler)
        self._tracked_crypto_currency_service = tracked_crypto_currency_service
        self._futures_exchange_service = futures_exchange_service
        self._crypto_technical_analysis_service = crypto_technical_analysis_service
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
            logger.info(signals_evaluation_result)
        except Exception as e:
            logger.error(f"Error evaluating signals for {tracked_crypto_currency}: {e}")
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
        logger.info(prev_candle)
        logger.info(last_candle)
        # TODO: To be implemented!
        return None
