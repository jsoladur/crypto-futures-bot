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
from crypto_futures_bot.infrastructure.adapters.futures_exchange.base import AbstractFuturesExchangeService
from crypto_futures_bot.infrastructure.database.alembic import run_migrations_async
from crypto_futures_bot.infrastructure.services.base import AbstractEventHandlerService
from crypto_futures_bot.introspection import load_modules_by_folder

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s - %(levelname)s - %(message)s",
    force=True,  # re-apply your config after Alembic wipes it
)

logger = logging.getLogger(__name__)


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
    telegram_bot: Bot = application_container.interfaces_container().telegram_container().telegram_bot()
    scheduler: BaseScheduler = application_container.infrastructure_container().tasks_container().scheduler()
    futures_exchange_service: AbstractFuturesExchangeService = (
        application_container.infrastructure_container().adapters_container().futures_exchange_service()
    )
    logger.info(f"Initializing Crypto Futures Bot :: v{version}")
    await run_migrations_async(configuration_properties)
    # Load Telegram commands dynamically
    _load_telegram_commands()
    # Background task manager initialization
    task_manager = await application_container.infrastructure_container().tasks_container().task_manager().load_tasks()
    logger.info(f"{len(task_manager.get_tasks())} jobs have been loaded!")
    # And the run events dispatching
    if configuration_properties.background_tasks_enabled:
        scheduler.start()
    # Configure pyee listeners
    for provider in application_container.infrastructure_container().services_container().traverse(types=[Singleton]):
        if isclass(provider.provides) and issubclass(provider.provides, AbstractEventHandlerService):
            dependency_object = provider()
            dependency_object.configure()
    logger.info("Futures exchange service initialization...")
    await futures_exchange_service.post_init()
    logger.info("Futures exchange service initialized...")
    if configuration_properties.telegram_bot_enabled:
        logger.info("Starting Telegram bot...")
        await dp.start_polling(telegram_bot)


if __name__ == "__main__":
    asyncio.run(main())
