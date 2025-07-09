# External
from enum import Enum
from notifications_python_client.notifications import NotificationsAPIClient

# Internal
from open_webui.models.notifications import NotificationType
from open_webui.notifications.notifier import Notifier


class Template(Enum):
  WELCOME = (NotificationType.WELCOME, "b2f0784d-2779-4a9c-a64a-e1f2c43d8f3a")

  def __init__(self, type, id):
    self.type = type
    self.id = id

class GCNotify(Notifier):
  # The template IDs associated to specific
  templates = {
    NotificationType.WELCOME: "b2f0784d-2779-4a9c-a64a-e1f2c43d8f3a",
  }

  def notify(notification_type, users) -> bool:
    return false
