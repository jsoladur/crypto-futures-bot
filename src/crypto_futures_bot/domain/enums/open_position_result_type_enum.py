from enum import StrEnum


class OpenPositionResultTypeEnum(StrEnum):
    SUCCESS = "SUCCESS"
    ALREADY_OPEN = "ALREADY_OPEN"
    NO_FUNDS = "NO_FUNDS"
    ERROR = "ERROR"
