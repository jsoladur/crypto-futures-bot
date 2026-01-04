from uuid import uuid4

from sqlalchemy import UUID, Boolean, Column, String

from crypto_futures_bot.infrastructure.database.models.base import Persistable


class AutoTraderCryptoCurrency(Persistable):
    __tablename__ = "auto_trader_crypto_currency"

    id: UUID = Column(UUID(as_uuid=True), primary_key=True, nullable=False, default=uuid4)

    currency: str = Column(String, nullable=False)
    activated: bool = Column(Boolean, nullable=False, default=True)
