from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dependency_injector import containers, providers

from crypto_futures_bot.infrastructure.tasks.task_manager import TaskManager


class TasksContainer(containers.DeclarativeContainer):
    __self__ = providers.Self()

    configuration_properties = providers.Dependency()
    event_emitter = providers.Dependency()

    scheduler = providers.Singleton(AsyncIOScheduler)

    task_manager = providers.Singleton(TaskManager, tasks_container=__self__)
