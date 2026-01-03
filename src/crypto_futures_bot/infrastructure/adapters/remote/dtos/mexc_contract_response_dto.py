from typing import Any

from pydantic import BaseModel, ConfigDict


class MEXCContractResponseDto[T: BaseModel | dict[str, Any] | Any](BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    success: bool = False
    code: int = 0
    data: T | None = None
    message: str | None = None
