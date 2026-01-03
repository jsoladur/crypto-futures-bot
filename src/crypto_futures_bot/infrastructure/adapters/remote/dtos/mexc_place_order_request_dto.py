from pydantic import BaseModel, ConfigDict, Field

from crypto_futures_bot.infrastructure.adapters.remote.enums import (
    MEXCPlaceOrderOpenTypeEnum,
    MEXCPlaceOrderSideEnum,
    MEXCPlaceOrderTypeEnum,
)


class MEXCPlaceOrderRequestDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    symbol: str
    price: float
    vol: float
    leverage: int | None = None
    side: MEXCPlaceOrderSideEnum
    order_type: MEXCPlaceOrderTypeEnum = Field(alias="type", default=MEXCPlaceOrderTypeEnum.MARKET)
    open_type: MEXCPlaceOrderOpenTypeEnum = Field(alias="openType", default=MEXCPlaceOrderOpenTypeEnum.ISOLATED)
    market_ceiling: bool = Field(alias="marketCeiling", default=False)
    stop_loss_price: float | None = Field(alias="stopLossPrice", default=None)
    take_profit_price: float | None = Field(alias="takeProfitPrice", default=None)
    loss_trend: int = Field(alias="lossTrend", default=1)  # 1: fixed price, 2: trailing stop
    profit_trend: int = Field(alias="profitTrend", default=1)  # 1: fixed price, 2: trailing stop
    price_protection: int = Field(alias="priceProtection", default=0)  # 0: disabled, 1: enabled
