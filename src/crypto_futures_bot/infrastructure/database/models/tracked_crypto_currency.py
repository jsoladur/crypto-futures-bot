from uuid import uuid4

from sqlalchemy import UUID, Column, String

from crypto_futures_bot.infrastructure.database.models.base import Persistable


class TrackedCryptoCurrency(Persistable):
    __tablename__ = "tracked_crypto_currency"

    id: UUID = Column(UUID(as_uuid=True), primary_key=True, nullable=False, default=uuid4)

    currency: str = Column(String, nullable=False)
