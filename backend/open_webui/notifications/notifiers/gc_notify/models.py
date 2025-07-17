# External
from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from typing import Dict, List

# Internal


# Forms
class SendBulkEmail500Model(BaseModel):
    message: str
    result: str


class SendBulkEmail400ErrorsModel(BaseModel):
    error: str
    message: str


class SendBulkEmail400Model(BaseModel):
    """
    Model which represents the data returned for an HTTP status code of 400.
    """

    errors: List[SendBulkEmail400ErrorsModel]
    status_code: int


class SendBulkEmailPostModel(BaseModel):
    name: str
    template_id: str
    rows: List[List[str]]
    scheduled_for: datetime | None = None
    reference: str | None = None


class SendBulkEmail201ApiKeyModel(BaseModel):
    id: str
    key_type: str
    name: str


class SendBulkEmail201CreatedByModel(BaseModel):
    id: str
    name: str


class SendBulkEmail201ServiceModel(BaseModel):
    name: str


class SendBulkEmail201DataModel(BaseModel):
    """

    https://documentation.notification.canada.ca/en/apispec.html#/Notifications/sendBulkNotifications
    """

    api_key: SendBulkEmail201ApiKeyModel | None
    archived: bool | None
    created_at: datetime | None
    created_by: SendBulkEmail201CreatedByModel | None
    id: str
    job_status: str
    notification_count: int
    original_file_name: str | None
    processing_finished: datetime | None
    processing_started: datetime | None
    scheduled_for: datetime | None
    sender_id: str | None
    service: str | None
    service_name: SendBulkEmail201ServiceModel | None
    template: str
    template_type: str | None
    template_version: int | None
    updated_at: datetime | None


# https://documentation.notification.canada.ca/en/apispec.html#/Notifications/sendBulkNotifications
class SendBulkEmail201Model(BaseModel):
    data: SendBulkEmail201DataModel


class PersonalizationValueType(str, Enum):
    """
    An Enum which identifies where the information for a personalization in a template comes from.

    STATIC: A static value to insert.
    USER_FIELD: A field from the User Model.
    """

    STATIC = "static"
    USER_FIELD = "user_field"


class TemplatePersonalization(BaseModel):
    """
    A model that represents a personalization in a GC Notify Template.
    Docs: https://notification.canada.ca/sending-custom-content/

    Attributes:
      type (PersonalizationValueType): the type identifies from where data is extracted.
      name (str): the name of the variable in the template.
      value (str): the value to be used to populate the variable in the template.
    """

    type: PersonalizationValueType
    name: str
    value: str | Dict[str, PersonalizationValueType]


class GCNotifyTemplate(Enum):
    """
    An enum that represents a mapping from the MessageTypes to a template in GC Notify.

    Attributes:
      id (str): the UUID of the template in GC Notify.
      personalizations (List(TemplatePersonalization)): A list of personalizations to pass to the template.
    """

    WELCOME = (
        "b2f0784d-2779-4a9c-a64a-e1f2c43d8f3a",
        [
            TemplatePersonalization(
                name="email address",
                type=PersonalizationValueType.USER_FIELD,
                value="email",
            ),
            TemplatePersonalization(
                name="name", type=PersonalizationValueType.USER_FIELD, value="name"
            ),
            TemplatePersonalization(
                name="url",
                type=PersonalizationValueType.STATIC,
                value="https://https://canchat-v2.dsai-sdia.ssc-spc.cloud-nuage.canada.ca",
            ),
        ],
    )

    def __init__(self, id: str, personalizations: list[TemplatePersonalization]):
        self.id: str = id
        self.personalizations: list[TemplatePersonalization] = personalizations
