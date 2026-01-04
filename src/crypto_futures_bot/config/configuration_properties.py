from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

from crypto_futures_bot.constants import (
    DEFAULT_CURRENCY_CODE,
    DEFAULT_FUTURES_EXCHANGE_TIMEOUT,
    DEFAULT_JOB_INTERVAL_SECONDS,
    DEFAULT_MARKET_SIGNAL_RETENTION_DAYS,
    DEFAULT_SQLITE_BUSY_TIMEOUT,
    MEXC_WEB_API_BASE_URL,
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
    database_busy_timeout: int = DEFAULT_SQLITE_BUSY_TIMEOUT

    futures_exchange: FuturesExchangeEnum = FuturesExchangeEnum.MEXC
    futures_exchange_timeout: int = DEFAULT_FUTURES_EXCHANGE_TIMEOUT
    futures_exchange_debug_mode: bool = False
    mexc_web_api_base_url: str = MEXC_WEB_API_BASE_URL
    mexc_web_auth_token: str | None = None
    mexc_api_key: str | None = None
    mexc_api_secret: str | None = None

    currency_code: str = DEFAULT_CURRENCY_CODE

    login_enabled: bool = True
    background_tasks_enabled: bool = True
    job_interval_seconds: int = DEFAULT_JOB_INTERVAL_SECONDS
    signals_run_via_cron_pattern: bool = True

    market_signal_retention_days: int = DEFAULT_MARKET_SIGNAL_RETENTION_DAYS

    notify_entry_signals: bool = True
    notify_exit_signals: bool = False
