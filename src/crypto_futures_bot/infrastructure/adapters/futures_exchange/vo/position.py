from dataclasses import dataclass

from crypto_futures_bot.domain.enums import PositionTypeEnum


@dataclass
class Position:
    position_type: PositionTypeEnum
