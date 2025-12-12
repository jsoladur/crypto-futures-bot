import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.domain.enums import PushNotificationTypeEnum
from crypto_futures_bot.domain.vo.push_notification_item import PushNotificationItem
from crypto_futures_bot.infrastructure.database.models.push_notification import PushNotification
from crypto_futures_bot.infrastructure.services.decorators import transactional

logger = logging.getLogger(__name__)


class PushNotificationService:
    def __init__(self, configuration_properties: ConfigurationProperties) -> None:
        self._configuration_properties = configuration_properties

    @transactional(read_only=True)
    async def find_push_notification_by_chat_id(
        self, chat_id: int, *, session: AsyncSession | None = None
    ) -> list[PushNotificationItem]:
        query = select(PushNotification).where(PushNotification.chat_id == chat_id)
        query_result = await session.execute(query)
        push_notifications = query_result.scalars().all()
        ret = []
        for current in PushNotificationTypeEnum:
            persisted = next(
                filter(
                    lambda n: PushNotificationTypeEnum.from_value(n.notification_type) == current, push_notifications
                ),
                None,
            )
            ret.append(
                PushNotificationItem(
                    chat_id=chat_id, notification_type=current, activated=persisted is not None and persisted.activated
                )
            )
        return ret

    @transactional()
    async def toggle_push_notification_by_type(
        self, chat_id: int, notification_type: PushNotificationTypeEnum, *, session: AsyncSession | None = None
    ) -> PushNotificationItem:
        query = (
            select(PushNotification)
            .where(PushNotification.chat_id == chat_id)
            .where(PushNotification.notification_type == notification_type.value)
        )
        query_result = await session.execute(query)
        push_notification = query_result.scalars().one_or_none()
        if push_notification:
            push_notification.activated = not push_notification.activated
        else:
            push_notification = PushNotification(
                chat_id=chat_id, notification_type=notification_type.value, activated=True
            )
            session.add(push_notification)
            await session.flush()
        ret = PushNotificationItem(
            chat_id=push_notification.chat_id,
            notification_type=PushNotificationTypeEnum.from_value(push_notification.notification_type),
            activated=push_notification.activated,
        )
        return ret

    @transactional(read_only=True)
    async def get_actived_subscription_by_type(
        self, notification_type: PushNotificationTypeEnum, *, session: AsyncSession | None = None
    ) -> list[int]:
        query = (
            select(PushNotification.chat_id)
            .where(PushNotification.notification_type == notification_type.value)
            .where(PushNotification.activated.is_(True))
        )
        query_result = await session.execute(query)
        chat_ids = query_result.scalars().all()
        return chat_ids
