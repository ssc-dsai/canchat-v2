import time
import uuid

from open_webui.models.notifications import (
    MessageType,
    NotificationModel,
    NotificationType,
)


def create_notification(
    user_id: str,
    message_type: MessageType,
    notification_type: NotificationType = NotificationType.EMAIL,
    notifier_used: str = "unit_test",
    is_sent: bool = True,
    is_received: bool | None = None,
    status: str = "sent",
) -> NotificationModel:
    return NotificationModel(
        id=str(uuid.uuid4()),
        user_id=user_id,
        message_type=message_type,
        notification_type=notification_type,
        notifier_used=notifier_used,
        is_sent=is_sent,
        is_received=is_received,
        status=status,
        created_at=int(time.time()),
        updated_at=int(time.time()),
    )
