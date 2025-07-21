from open_webui.config import NOTIFICATIONS_NOTIFIER
from open_webui.notifications.notifier import Notifier
from open_webui.notifications.notifiers.gc_notify.gc_notifier import GCNotify

_notifier_service: Notifier

match NOTIFICATIONS_NOTIFIER:
  case GCNotify.identifier():
    _notifier_service = GCNotify("asdasd")


  case _:
    raise TypeError()

NOTIFIER = _notifier_service
