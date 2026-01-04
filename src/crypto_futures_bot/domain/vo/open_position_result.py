from dataclasses import dataclass

from crypto_futures_bot.domain.enums.open_position_result_type_enum import OpenPositionResultTypeEnum
from crypto_futures_bot.domain.enums.position_type_enum import PositionTypeEnum
from crypto_futures_bot.domain.vo.position_metrics import PositionMetrics
from crypto_futures_bot.domain.vo.tracked_crypto_currency_item import TrackedCryptoCurrencyItem


@dataclass(frozen=True, kw_only=True)
class OpenPositionResult:
    result_type: OpenPositionResultTypeEnum = OpenPositionResultTypeEnum.SUCCESS
    crypto_currency: TrackedCryptoCurrencyItem
    position_type: PositionTypeEnum
    position_metrics: PositionMetrics | None = None
