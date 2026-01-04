from enum import IntEnum


class MEXCPlaceOrderSideEnum(IntEnum):
    OPEN_LONG = 1
    CLOSE_SHORT = 2
    OPEN_SHORT = 3
    CLOSE_LONG = 4
