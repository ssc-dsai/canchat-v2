from abc import ABC, abstractmethod

from open_webui.models.users import User
from open_webui.models.notifications import NotificationType

class Notifier(ABC):

  @abstractmethod
  def notify(notification_type: NotificationType, users: list[User]) -> bool:
    pass
