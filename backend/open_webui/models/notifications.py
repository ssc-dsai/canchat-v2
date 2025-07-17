from enum import Enum
import logging
import time
from typing import Optional
import uuid
from pydantic import BaseModel
from sqlalchemy import Column, Text, BigInteger, Boolean, Null

from open_webui.env import SRC_LOG_LEVELS
from open_webui.internal.db import Base, get_db
# from open_webui.models.base import Base

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["DB"])


# The types of notifications that can be sent.
class MessageType(str, Enum):
    """
    Identifies the type of message that is sent to the user.
    """

    WELCOME = "welcome"
    ACCOUNT_DELETION = "account_deletion"


class NotificationType(str, Enum):
    """
    Identitifies the mode of communication used to send the notification.
    """

    EMAIL = "email"
    SMS = "sms"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Text, primary_key=True)
    user_id = Column(Text)
    message_type = Column(Text)
    notification_type = Column(Text)
    notifier_used = Column(Text)
    is_sent = Column(Boolean)
    is_received = Column(Boolean, nullable=True, default=Null)
    status = Column(Text, nullable=True)
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class NotificationModel(BaseModel):
    id: str
    user_id: str
    message_type: MessageType
    notification_type: NotificationType
    is_sent: bool
    is_received: bool | None
    status: str | None
    created_at: int
    updated_at: int
    notifier_used: str


class NotificationsTable:
    def insert_new_notification(
        self,
        user_id: str,
        message_type: MessageType,
        notification_type: NotificationType,
        is_sent: bool,
        notifier_used: str,
        is_received: str | None = None,
        status: str | None = None,
    ) -> Optional[NotificationModel]:
        with get_db() as db:
            notification = NotificationModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                message_type=message_type,
                notification_type=notification_type,
                is_sent=is_sent,
                is_received=is_received,
                status=status,
                created_at=int(time.time()),
                updated_at=int(time.time()),
                notifier_used=notifier_used,
            )
            log.debug(notification.model_dump(mode="json"))
            result = Notification(**notification.model_dump(mode="json"))
            db.add(result)
            db.commit()
            db.refresh(result)
            if result:
                return notification
            else:
                return None

Notifications = NotificationsTable()
