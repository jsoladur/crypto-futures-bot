from dataclasses import dataclass

from crypto_futures_bot.domain.enums import PushNotificationTypeEnum


@dataclass
class PushNotificationItem:
    chat_id: int
    notification_type: PushNotificationTypeEnum
    activated: bool
