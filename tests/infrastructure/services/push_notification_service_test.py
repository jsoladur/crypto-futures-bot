import logging

import pytest
from dependency_injector.containers import Container
from faker import Faker

from crypto_futures_bot.domain.enums import PushNotificationTypeEnum
from crypto_futures_bot.infrastructure.services.push_notification_service import PushNotificationService

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def should_toggle_push_notifications_properly(faker: Faker, test_environment: tuple[Container, ...]) -> None:
    application_container, *_ = test_environment
    push_notification_service: PushNotificationService = (
        application_container.infrastructure_container().services_container().push_notification_service()
    )

    chat_id = faker.pyint()
    notification_type = faker.random_element(list(PushNotificationTypeEnum))

    # Initially, no active subscriptions
    active_subscriptions = await push_notification_service.get_actived_subscription_by_type(notification_type)
    assert chat_id not in active_subscriptions

    # Toggle to activate
    toggled_item = await push_notification_service.toggle_push_notification_by_type(chat_id, notification_type)
    assert toggled_item.activated
    assert toggled_item.chat_id == chat_id
    assert toggled_item.notification_type == notification_type

    active_subscriptions = await push_notification_service.get_actived_subscription_by_type(notification_type)
    assert chat_id in active_subscriptions

    notifications = await push_notification_service.find_push_notification_by_chat_id(chat_id)
    notification = next(n for n in notifications if n.notification_type == notification_type)
    assert notification.activated

    # Toggle to deactivate
    toggled_item = await push_notification_service.toggle_push_notification_by_type(chat_id, notification_type)
    assert not toggled_item.activated

    active_subscriptions = await push_notification_service.get_actived_subscription_by_type(notification_type)
    assert chat_id not in active_subscriptions

    notifications = await push_notification_service.find_push_notification_by_chat_id(chat_id)
    notification = next(n for n in notifications if n.notification_type == notification_type)
    assert not notification.activated
