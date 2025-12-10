from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dependency_injector import containers, providers

from crypto_futures_bot.infrastructure.tasks.signals_task_service import SignalsTaskService
from crypto_futures_bot.infrastructure.tasks.task_manager import TaskManager


class TasksContainer(containers.DeclarativeContainer):
    __self__ = providers.Self()

    configuration_properties = providers.Dependency()
    event_emitter = providers.Dependency()

    tracked_crypto_currency_service = providers.Dependency()
    futures_exchange_service = providers.Dependency()
    crypto_technical_analysis_service = providers.Dependency()

    scheduler = providers.Singleton(AsyncIOScheduler)

    task_manager = providers.Singleton(TaskManager, tasks_container=__self__)

    signals_task_service = providers.Singleton(
        SignalsTaskService,
        configuration_properties=configuration_properties,
        scheduler=scheduler,
        tracked_crypto_currency_service=tracked_crypto_currency_service,
        futures_exchange_service=futures_exchange_service,
        crypto_technical_analysis_service=crypto_technical_analysis_service,
    )
