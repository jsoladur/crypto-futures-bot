from uuid import uuid4

from sqlalchemy import UUID, Column, Float, Integer

from crypto_futures_bot.infrastructure.database.models.base import Persistable


class RiskManagement(Persistable):
    __tablename__ = "risk_management"

    id: UUID = Column(UUID(as_uuid=True), primary_key=True, nullable=False, default=uuid4)
    percent_value: Float = Column(Float, nullable=False)
    number_of_concurrent_trades: Integer = Column(Integer, nullable=True)
