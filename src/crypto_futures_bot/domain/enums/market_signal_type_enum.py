from enum import Enum


class MarketSignalTypeEnum(str, Enum):
    LONG_ENTRY = "LONG_ENTRY"
    LONG_EXIT = "LONG_EXIT"
    SHORT_ENTRY = "SHORT_ENTRY"
    SHORT_EXIT = "SHORT_EXIT"
