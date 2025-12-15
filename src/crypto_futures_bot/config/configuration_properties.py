from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

from crypto_futures_bot.constants import (
    DEFAULT_CURRENCY_CODE,
    DEFAULT_JOB_INTERVAL_SECONDS,
    DEFAULT_LONG_ENTRY_OVERSOLD_THRESHOLD,
    DEFAULT_LONG_EXIT_OVERBOUGHT_THRESHOLD,
    DEFAULT_MARKET_SIGNAL_RETENTION_DAYS,
    DEFAULT_SHORT_ENTRY_OVERBOUGHT_THRESHOLD,
    DEFAULT_SHORT_EXIT_OVERSOLD_THRESHOLD,
)
from crypto_futures_bot.infrastructure.adapters.futures_exchange.enums import FuturesExchangeEnum


class ConfigurationProperties(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", validate_default=False, extra="ignore"
    )

    root_user: str
    root_password: str

    telegram_bot_token: str

    database_url: str

    futures_exchange: FuturesExchangeEnum = FuturesExchangeEnum.MEXC
    futures_exchange_debug_mode: bool = False
    mexc_api_key: str | None = None
    mexc_api_secret: str | None = None

    currency_code: str = DEFAULT_CURRENCY_CODE

    login_enabled: bool = True
    background_tasks_enabled: bool = True
    job_interval_seconds: int = DEFAULT_JOB_INTERVAL_SECONDS
    signals_run_via_cron_pattern: bool = True

    long_entry_oversold_threshold: float = DEFAULT_LONG_ENTRY_OVERSOLD_THRESHOLD
    long_exit_overbought_threshold: float = DEFAULT_LONG_EXIT_OVERBOUGHT_THRESHOLD
    short_entry_overbought_threshold: float = DEFAULT_SHORT_ENTRY_OVERBOUGHT_THRESHOLD
    short_exit_oversold_threshold: float = DEFAULT_SHORT_EXIT_OVERSOLD_THRESHOLD

    market_signal_retention_days: int = DEFAULT_MARKET_SIGNAL_RETENTION_DAYS
