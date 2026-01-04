from dataclasses import dataclass

from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo.base import AbstractPosition


@dataclass(kw_only=True, frozen=True)
class CreateMarketPositionOrder(AbstractPosition):
    pass
