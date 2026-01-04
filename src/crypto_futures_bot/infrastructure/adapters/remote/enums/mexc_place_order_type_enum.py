from enum import IntEnum


class MEXCPlaceOrderTypeEnum(IntEnum):
    LIMIT = 1
    POST_ONLY = 2
    IOC = 3
    FOK = 4
    MARKET = 5
