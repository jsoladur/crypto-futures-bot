from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigurationProperties(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", validate_default=False, extra="ignore"
    )

    root_user: str
    root_password: str

    telegram_bot_token: str

    database_url: str

    background_tasks_enabled: bool = True
