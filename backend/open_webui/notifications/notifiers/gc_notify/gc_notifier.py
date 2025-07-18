# External
from datetime import datetime, timezone
import json
import logging
from typing import Dict
import requests

# Internal
from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.notifications import MessageType, Notifications, NotificationType
from open_webui.models.users import UserModel
from open_webui.notifications.notifier import Notifier
from open_webui.notifications.notifiers.gc_notify.models import (
    GCNotifyTemplate,
    SendBulkEmailPostModel,
    SendBulkEmail201Model,
    SendBulkEmail400Model,
    SendBulkEmail500Model,
)
from open_webui.notifications.notifiers.gc_notify.utils import (
    format_errors,
    generate_rows,
)


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["NOTIFICATIONS"])


class GCNotify(Notifier):
    """
    A Notifier which uses GC Notify as its service provider.

    Attributes:
      templates (Dict(MessageType, GCNotifyTemplate)): A map from MessageType to a GCNotifyTemplate to use.
      api_endpoint (str): The URL to use when accessing the API.
    """

    templates = {
        MessageType.WELCOME: GCNotifyTemplate.WELCOME,
    }

    api_endpoint: str
    api_key: str
    auth_header: Dict[str, str]

    def __init__(
        self,
        api_key: str,
        api_endpoint: str = "https://api.notification.canada.ca/v2/notifications",
    ):
        self.api_endpoint = api_endpoint
        self.api_key = api_key
        self.auth_header = {"Authorization": f"ApiKey-v1 {api_key}"}
        super().__init__()

    def identifier(self):
        return "gc_notify"

    def supported_notification_types(self):
        return [NotificationType.EMAIL, NotificationType.SMS]

    def notify(
        self,
        message_type: MessageType,
        notification_type: NotificationType,
        users: list[UserModel],
    ) -> bool:
        value = (notification_type, len(users))
        match value:
            case (NotificationType.EMAIL, x) if x == 1:
                return self.send_email(message_type=message_type, user=users[0])

            case (NotificationType.EMAIL, x) if x > 1:
                return self.send_bulk_email(message_type=message_type, users=users)

            case (NotificationType.EMAIL, x) if x == 0:
                log.error("No users provided, no emails to be sent.")
                return False

            case (NotificationType.SMS, x):
                log.error("SMS notifications not yet implemented for GCNotify")
                return False

            case _:
                pass

        return False

    def send_email(self, message_type: MessageType, user: UserModel) -> bool:
        return False

    def send_bulk_email(self, message_type: MessageType, users: list[UserModel]) -> bool:
        current_datetime = datetime.now(tz=timezone.utc).isoformat()
        bulkEmailModel = SendBulkEmailPostModel(
            name=f"{message_type.name}-{current_datetime}",
            reference=f"{message_type.name}-{current_datetime}",
            template_id=self.templates[message_type].id,
            rows=generate_rows(template=self.templates[message_type], users=users),
        )

        response = requests.post(
            url=f"{self.api_endpoint}/bulk",
            headers=self.auth_header,
            json=bulkEmailModel.model_dump(mode="json"),
        )

        log.debug(
            "Received response %s from %s, json:\n%s",
            response.status_code,
            self.api_endpoint,
            json.dumps(response.json(), indent=2),
        )

        match response.status_code:
            case 201:
                log.debug(response.json())
                responseModel = SendBulkEmail201Model(**response.json())

                for user in users:
                    notification_dict = {
                        "user_id": user.id,
                        "message_type": message_type,
                        "notification_type": NotificationType.EMAIL,
                        "is_sent": True,
                        "is_received": False,
                        "notifier_used": self.identifier(),
                        "status": responseModel.data.job_status,
                    }

                    notification = Notifications.insert_new_notification(
                        user_id=user.id,
                        message_type=message_type,
                        notification_type=NotificationType.EMAIL,
                        is_sent=True,
                        is_received=False,
                        notifier_used=self.identifier(),
                        status=responseModel.data.job_status,
                    )

                    if notification:
                        pass
                    else:
                        log.error(
                            "Error creating Notification in DB: %d", notification_dict
                        )

                return True

            case 400:
                responseModel = SendBulkEmail400Model(**response.json())
                log.error("Received status code 400.\n%s", format_errors(responseModel))

                return False
            case 500:
                responseModel = SendBulkEmail500Model(**response.json())

            case _:
                log.error(
                    f"Received status code {response.status_code} from {self.api_endpoint}"
                )
                log.error(f"json:\n{json.dump(response.json(mode=json), indent=2)}")
                return False

        return True
