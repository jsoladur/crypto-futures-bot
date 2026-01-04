from __future__ import annotations

from enum import Enum
from typing import Any


class PushNotificationTypeEnum(str, Enum):
    SIGNALS = ("SIGNALS", "Market signals")
    TRADES = ("TRADES", "Trade alerts")
    FATAL_ERRORS = ("FATAL_ERRORS", "Fatal errors")

    @classmethod
    def from_value(cls, value: str) -> PushNotificationTypeEnum:
        for item in cls:
            if item.value == value:
                return item
        raise ValueError(f"{value!r} is not a valid {cls.__name__}")  # pragma: no cover

    def __new__(cls, value: str, description: str) -> PushNotificationTypeEnum:
        obj: Any = str.__new__(cls, value)
        obj._value_ = value
        obj.description = description
        return obj
