from typing import Annotated
from pydantic import BaseModel, Field


class UserAuth(BaseModel):
    """
    Docstring for UserAuth
    """

    token: str
    expiry: int


class UserSession(BaseModel):
    """
    Docstring for UserSession
    """

    user_id: Annotated[
        str, Field(frozen=True, description="The user_id of the owner of the session.")
    ]
    graph_access_token: Annotated[
        UserAuth | None,
        Field(
            default=None,
            description="The access token used to access Azure Graph resources.",
        ),
    ] = None
