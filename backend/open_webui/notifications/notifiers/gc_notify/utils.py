import logging
from typing import List

from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.users import User
from open_webui.notifications.notifiers.gc_notify.models import (
    GCNotifyTemplate,
    PersonalizationValueType,
    SendBulkEmail400Model,
)

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["NOTIFICATIONS"])


def format_errors(model: SendBulkEmail400Model) -> str:
    formatted_errors: str = "Errors:\n"

    for error in model.errors:
        formatted_errors += f"\t{error.error}: {error.message}\n"

    return formatted_errors


def _get_personalization_value(
    personalization: PersonalizationValueType, user: User
) -> str:
    value: str

    match personalization.type:
        case PersonalizationValueType.STATIC:
            value = personalization.value
        case PersonalizationValueType.USER_FIELD:
            value = getattr(user, personalization.value)
        case _:
            raise

    return value


def generate_rows(template: GCNotifyTemplate, users: List[User]) -> List[List[str]]:
    rows: List[List[str]] = list()

    # Set first row which is the column headers
    rows.append([personalization.name for personalization in template.personalizations])

    for current_user in users:
        user_row: List[str] = list()

        for personalization in template.personalizations:
            user_row.append(
                _get_personalization_value(
                    personalization=personalization, user=current_user
                )
            )
        rows.append(user_row)

    return rows
