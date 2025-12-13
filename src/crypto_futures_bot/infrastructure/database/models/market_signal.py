from uuid import uuid4

from sqlalchemy import UUID, Column, Enum, Float, String

from crypto_futures_bot.domain.enums import MarketActionTypeEnum, PositionTypeEnum
from crypto_futures_bot.domain.types import Timeframe
from crypto_futures_bot.infrastructure.database.models.base import Persistable


class MarketSignal(Persistable):
    __tablename__ = "market_signal"

    id: UUID = Column(UUID(as_uuid=True), primary_key=True, nullable=False, default=uuid4)
    crypto_currency: str = Column(String, nullable=False)
    timeframe: Timeframe = Column(String, nullable=False, default="15m")
    position_type: PositionTypeEnum = Column(Enum(PositionTypeEnum), nullable=False)
    action_type: MarketActionTypeEnum = Column(Enum(MarketActionTypeEnum), nullable=False)
    entry_price: float = Column(Float, nullable=True)
    break_even_price: float = Column(Float, nullable=True)
    stop_loss_percent_value: float = Column(Float, nullable=True)
    take_profit_percent_value: float = Column(Float, nullable=True)
    stop_loss_price: float = Column(Float, nullable=True)
    take_profit_price: float = Column(Float, nullable=True)
