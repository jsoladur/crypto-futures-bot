import asyncio
import logging

from alembic import command
from alembic.config import Config

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties

logger = logging.getLogger(__name__)


def _run_migrations(config: ConfigurationProperties) -> None:
    """
    Run Alembic migrations programmatically.

    This function creates an Alembic configuration object, sets the database URL
    from the application configuration, and runs the 'upgrade head' command.
    """
    logger.info("Starting database migrations...")
    # Path to alembic.ini - assumes running from project root or finding it relative to this file
    # We'll try to find it in the project root.
    # If this file is in src/crypto_futures_bot/infrastructure/database/,
    # root is 5 levels up? No, 4: infrastructure, database, crypto_futures_bot, src -> root.

    # A safer way relies on the working directory being the project root
    # (which is standard for Docker/dev usage)
    alembic_ini_path = "alembic.ini"
    alembic_cfg = Config(alembic_ini_path)
    # Overwrite the sqlalchemy.url in the config with the one from our app settings
    # We assume 'database_url' exists in ConfigurationProperties
    # Note: We verify if the user added it, otherwise we'll add it.
    if hasattr(config, "database_url"):
        alembic_cfg.set_main_option("sqlalchemy.url", str(config.database_url))
    else:
        logger.warning("ConfigurationProperties has no 'database_url'. using default from alembic.ini if available.")
    # Execute the migration in a separate thread to ensure the async loop in env.py
    # (via run_migrations_online -> asyncio.run) works correctly.
    # But wait, we can't spawn a thread *here* and expect asyncio.run to work if we are ALREADY in a thread?
    # No, if we call this function from main() using run_in_executor, we are in a thread.
    # Then env.py calls asyncio.run(), which starts a NEW loop in THIS thread.
    # This is valid as long as this thread doesn't already have a running loop.
    command.upgrade(alembic_cfg, "head")
    logger.info("Database migrations completed successfully.")


async def run_migrations_async(config: ConfigurationProperties):
    await asyncio.to_thread(_run_migrations, config)
