from pydantic import BaseModel, ConfigDict, Field


class MEXCPlaceOrderResponseDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    order_id: str = Field(..., alias="orderId")
