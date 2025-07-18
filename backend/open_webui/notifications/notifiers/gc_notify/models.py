# External
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, model_validator
from typing import Any, Dict, List, Self, cast

# Internal
from open_webui.models.users import UserModel

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

class SendBulkEmail201Model(BaseModel):
    """
    Top level object for a successful response when sending a bulk email.

    Swagger API Docs: https://documentation.notification.canada.ca/en/apispec.html#/Notifications/sendBulkNotifications
    """
    data: SendBulkEmail201DataModel


# Classes for Templates
class TemplatePersonalization(ABC):
    """
    Defines a template personalization for GC Notify.
    A personalization is defined by the key used in the template and the value to fill it.

    Attributes:
      name (str): the name(key) of the personalization in the template.
    """
    __name: str

    def __init__(self, name: str) -> None:
        self.__name=name
        super().__init__()

    def get_name(self) -> str:
        """
        Returns the name of the personalization used in the template.
        """
        return self.__name

    @abstractmethod
    def get_value(self, arg: Any = None) -> str:
        """
        Returns the value to be inserted into the template.
        """
        pass

class StaticPersonalization(TemplatePersonalization):
    """
    Represents a static value to be inserted into the template.

    Attributes:
      value (str): The value to insert into the template.
    """

    __value: str

    def __init__(self, name: str, value: str) -> None:
        self.__value=value
        super().__init__(name)

    def get_value(self, arg: Any = None) -> str:
        return self.__value

class UserPersonalization(TemplatePersonalization):
    """
    A personalization which extract data from a UserModel.

    Attributes:
      name (str): the name(key) of the personalization in the template.
      field_name(str): the name of the field in the UserModel to extract data from.
    """

    __field_name: str

    def __init__(self, name: str, field_name: str):
        self.__field_name=field_name
        super().__init__(name)

    def get_value(self, arg: Any = None) -> str:
        if not isinstance(arg, UserModel):
            raise TypeError("arg must be a UserModel")
        return str(getattr(arg, self.__field_name))

class MappedStatic(TemplatePersonalization):
    """
    Allows for
    """

    __map: dict[str, str]
    __default: str
    __accessor: TemplatePersonalization

    def __init__(self, name: str, map: dict[str, str], default: str, accessor: TemplatePersonalization) -> None:
        self.__map=map
        self.__default=default
        self.__accessor=accessor
        super().__init__(name)

    def get_value(self, arg: Any = None) -> str:
        return self.__map.get(self.__accessor.get_value(arg), self.__default)


class GCNotifyTemplate(Enum):
    """
    An enum that represents a mapping from the MessageTypes to a template in GC Notify.

    Attributes:
      id (str): the UUID of the template in GC Notify.
      personalizations (List(TemplatePersonalization)): A list of personalizations to pass to the template.
    """

    WELCOME = (
        "b2f0784d-2779-4a9c-a64a-e1f2c43d8f3a",
        cast(list[TemplatePersonalization],
          [
            UserPersonalization(
                name="email address",
                field_name="email"
            ),
            UserPersonalization(
                name="name",
                field_name="name"
            ),
            # StaticPersonalization(
            #     name="url",
            #     value="https://https://canchat-v2.dsai-sdia.ssc-spc.cloud-nuage.canada.ca"
            # ),
            MappedStatic(
                name="url",
                map={
                    "ssc-spc.gc.ca": "https://https://canchat-v2.dsai-sdia.ssc-spc.cloud-nuage.canada.ca",
                },
                default="https://canchat.pilot-pilote.dsai-sdia.ssc-spc.cloud-nuage.canada.ca",
                accessor=UserPersonalization(
                    name="domain",
                    field_name="domain"
                )
            )
        ]),
    )

    def __init__(self, id: str, personalizations: list[TemplatePersonalization]):
        self.id: str = id
        self.personalizations: list[TemplatePersonalization] = personalizations
