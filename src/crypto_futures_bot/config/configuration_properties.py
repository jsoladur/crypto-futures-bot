from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

from crypto_futures_bot.constants import DEFAULT_CURRENCY_CODE, DEFAULT_JOB_INTERVAL_SECONDS
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
    mexc_api_key: str | None = None
    mexc_api_secret: str | None = None

    currency_code: str = DEFAULT_CURRENCY_CODE

    login_enabled: bool = True
    background_tasks_enabled: bool = True
    job_interval_seconds: int = DEFAULT_JOB_INTERVAL_SECONDS
