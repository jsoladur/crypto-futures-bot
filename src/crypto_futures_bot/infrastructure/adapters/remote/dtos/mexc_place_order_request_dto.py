from pydantic import BaseModel, Field

from crypto_futures_bot.infrastructure.adapters.remote.enums import (
    MEXCPlaceOrderOpenTypeEnum,
    MEXCPlaceOrderSideEnum,
    MEXCPlaceOrderTypeEnum,
)


class MEXCPlaceOrderRequestDto(BaseModel):
    symbol: str
    price: float
    vol: float
    leverage: int | None = None
    side: MEXCPlaceOrderSideEnum
    order_type: MEXCPlaceOrderTypeEnum = Field(alias="type", default=MEXCPlaceOrderTypeEnum.MARKET)
    open_type: MEXCPlaceOrderOpenTypeEnum = Field(alias="openType", default=MEXCPlaceOrderOpenTypeEnum.ISOLATED)
    external_oid: str | None = Field(alias="externalOid", default=None)
    stop_loss_price: float | None = Field(alias="stopLossPrice", default=None)
    take_profit_price: float | None = Field(alias="takeProfitPrice", default=None)
