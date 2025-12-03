from __future__ import annotations

from typing import Any

from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, EnvSettingsSource, PydanticBaseSettingsSource, SettingsConfigDict


class _CustomEnvSettingsSource(EnvSettingsSource):
    def prepare_field_value(self, field_name: str, field: FieldInfo, value: Any, value_is_complex: bool) -> Any:
        if field_name == "authorized_google_user_emails_comma_separated":
            ret = [str(v).strip().lower() for v in value.split(",")] if value else None
        else:
            ret = super().prepare_field_value(field_name, field, value, value_is_complex)
        return ret


class ConfigurationProperties(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", validate_default=False, extra="allow")

    root_user: str
    root_password: str

    @classmethod
    def settings_customise_sources(
        cls, settings_cls: type[BaseSettings], *_, **__
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (_CustomEnvSettingsSource(settings_cls),)
