from abc import ABC, abstractmethod
from enum import auto, Enum
from typing import List

from open_webui.models.notifications import MessageType, NotificationType
from open_webui.models.users import UserModel


class Notifier(ABC):
    """
    A system that sends notifications to users.
    """

    @abstractmethod
    def identifier(self) -> str:
        pass

    @abstractmethod
    def notify(self,
        message_type: MessageType,
        notification_type: NotificationType,
        users: list[UserModel],
    ) -> bool:
        pass

    @abstractmethod
    def supported_notification_types(self) -> List[NotificationType]:
        return []
