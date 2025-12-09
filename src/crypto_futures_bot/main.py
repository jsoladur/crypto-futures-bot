import asyncio
import logging
import sys
from inspect import isclass
from os import path

from aiogram import Bot, Dispatcher
from apscheduler.schedulers.base import BaseScheduler
from dependency_injector.providers import Singleton

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.config.dependencies import get_application_container
from crypto_futures_bot.infrastructure.services.base import AbstractEventHandlerService
from crypto_futures_bot.introspection import load_modules_by_folder

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(asctime)s - %(levelname)s - %(message)s")


def _load_telegram_commands() -> None:
    for layer_name in ["commands", "callbacks"]:
        load_modules_by_folder(
            root_folder=path.join(path.dirname(__file__), "interfaces", "telegram"),
            root_package=f"{__package__}.interfaces.telegram",
            folder_name=layer_name,
        )


async def main() -> None:
    application_container = get_application_container()
    configuration_properties: ConfigurationProperties = application_container.configuration_properties()
    version = application_container.application_version()
    dp: Dispatcher = application_container.interfaces_container().telegram_container().dispatcher()
    scheduler: BaseScheduler = application_container.infrastructure_container().tasks_container().scheduler()

    logger.info(f"Initializing Crypto Futures Bot :: v{version}")
    # Load Telegram commands dynamically
    _load_telegram_commands()
    # Background task manager initialization
    task_manager = await application_container.infrastructure_container().tasks_container().task_manager().load_tasks()
    logger.info(f"{len(task_manager.get_tasks())} jobs have been loaded!")
    # And the run events dispatching
    telegram_bot: Bot = application_container.interfaces_container().telegram_container().telegram_bot()
    if configuration_properties.background_tasks_enabled:
        scheduler.start()
    # Configure pyee listeners
    for provider in application_container.infrastructure_container().services_container().traverse(types=[Singleton]):
        if isclass(provider.provides) and issubclass(provider.provides, AbstractEventHandlerService):
            dependency_object = provider()
            dependency_object.configure()
    logger.info("Application startup complete.")
    await dp.start_polling(telegram_bot)


if __name__ == "__main__":
    asyncio.run(main())
