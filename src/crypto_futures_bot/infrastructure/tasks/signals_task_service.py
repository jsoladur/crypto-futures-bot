from typing import override

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.constants import SIGNALS_TASK_SERVICE_CRON_PATTERN
from crypto_futures_bot.domain.enums import TaskTypeEnum
from crypto_futures_bot.infrastructure.tasks.base import AbstractTaskService


class SignalsTaskService(AbstractTaskService):
    def __init__(self, configuration_properties: ConfigurationProperties, scheduler: AsyncIOScheduler) -> None:
        super().__init__(configuration_properties, scheduler)
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

    @override
    def _get_job_trigger(self) -> CronTrigger | IntervalTrigger:  # pragma: no cover
        if self._configuration_properties.buy_sell_signals_run_via_cron_pattern:
            trigger = CronTrigger(
                minute=",".join([str(minute) for minute in SIGNALS_TASK_SERVICE_CRON_PATTERN]), hour="*"
            )
        else:
            trigger = IntervalTrigger(seconds=self._configuration_properties.job_interval_seconds)
        return trigger
