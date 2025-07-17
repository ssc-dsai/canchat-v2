from abc import ABC, abstractmethod
from enum import auto, Enum
from typing import List

from open_webui.models.notifications import MessageType, NotificationType
from open_webui.models.users import User


class Notifier(ABC):
    """
    A system that sends notifications to users.
    """

    @abstractmethod
    def identifier() -> str:
        pass

    @abstractmethod
    def notify(
        message_type: MessageType,
        notification_type: NotificationType,
        users: list[User],
    ) -> bool:
        pass

    @abstractmethod
    def supported_notification_types() -> List[NotificationType]:
        return []
