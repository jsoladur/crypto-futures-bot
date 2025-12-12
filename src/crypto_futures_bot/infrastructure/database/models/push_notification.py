from uuid import uuid4

from sqlalchemy import UUID, Boolean, Column, Enum, Integer, UniqueConstraint

from crypto_futures_bot.domain.enums.push_notification_type_enum import PushNotificationTypeEnum
from crypto_futures_bot.infrastructure.database.models.base import Persistable


class PushNotification(Persistable):
    __tablename__ = "push_notification"
    __table_args__ = (UniqueConstraint("notification_type", "chat_id"),)

    id: UUID = Column(UUID(as_uuid=True), primary_key=True, nullable=False, default=uuid4)
    notification_type: PushNotificationTypeEnum = Column(Enum(PushNotificationTypeEnum), nullable=False)
    chat_id: int = Column(Integer, nullable=False)
    activated: bool = Column(Boolean, nullable=False, default=True)
