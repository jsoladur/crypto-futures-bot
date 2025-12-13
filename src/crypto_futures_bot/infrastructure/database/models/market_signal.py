from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import UUID, Column, DateTime, Enum, Float, String

from crypto_futures_bot.domain.enums import MarketSignalTypeEnum
from crypto_futures_bot.infrastructure.adapters.futures_exchange.types import Timeframe
from crypto_futures_bot.infrastructure.database.models.base import Persistable


class MarketSignal(Persistable):
    __tablename__ = "market_signal"

    id: UUID = Column(UUID(as_uuid=True), primary_key=True, nullable=False, default=uuid4)
    timestamp: datetime = Column(DateTime(timezone=UTC), nullable=False, default=lambda: datetime.now(UTC))
    crypto_currency: str = Column(String, nullable=False)
    timeframe: Timeframe = Column(String, nullable=False)
    signal_type: MarketSignalTypeEnum = Column(Enum(MarketSignalTypeEnum), nullable=False)
    entry_price: float = Column(Float, nullable=True)
    break_event_price: float = Column(Float, nullable=True)
    sl_percent: float = Column(Float, nullable=True)
    tp_percent: float = Column(Float, nullable=True)
    sl_price: float = Column(Float, nullable=True)
    tp_price: float = Column(Float, nullable=True)
