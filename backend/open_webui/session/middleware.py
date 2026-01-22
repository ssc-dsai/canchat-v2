import logging
from typing import Tuple
from fastapi import Request
import jwt
from starlette.middleware.base import BaseHTTPMiddleware

from backend.open_webui.session.models import UserAuth, UserSession
from backend.open_webui.utils.auth import decode_token, extract_token_from_auth_header
from open_webui.session.main import SESSION_SERVICE


def extract_jwt_expiry(token: str) -> int:
    """
    Docstring for extract_access_token_expiry

    :param token: Description
    :type token: str
    :return: Description
    :rtype: int
    """
    if token:
        # Extract token information without verifying signature
        # Tokens can currently come from two different AppIDs
        token_decoded = jwt.decode(token, options={"verify_signature": False})

        return int(token_decoded["exp"])
    else:
        return -1


def update_graph_access_token(
    token: str, session: UserSession
) -> Tuple[bool, UserSession]:
    """
    Docstring for update_graph_access_token

    :param token: Description
    :type token: str
    :param session: Description
    :type session: UserSession
    :return: Description
    :rtype: Tuple[bool, UserSession]
    """
    updated = False

    if token:
        access_token_expiry = extract_jwt_expiry(token)

        if (
            # No stored token
            not session.graph_access_token
            # New token has later expiry
            or session.graph_access_token.expiry > access_token_expiry
        ):
            session.graph_access_token = UserAuth(
                token=token, expiry=access_token_expiry
            )
            updated = True

    return (updated, session)


async def get_session_from_token(token: str) -> UserSession | None:
    """
    Docstring for get_session_from_token

    :param token: Description
    :type token: str
    :return: Description
    :rtype: UserSession | None
    """

    payload = decode_token(token)

    # Extract user's id from
    if user_id := payload.get("id"):
        user_session = await SESSION_SERVICE.get_session(user_id) or UserSession(
            user_id=user_id
        )

        return user_session

    return None


class UserSessionMiddleware(BaseHTTPMiddleware):
    """
    Docstring for UserSessionMiddleware
    """

    async def dispatch(self, request: Request, call_next):

        is_updated = False
        # Get token if available in Request
        if token := (
            request.cookies.get("token")
            or extract_token_from_auth_header(request.headers["Authorization"])
        ):
            try:
                if user_session := await get_session_from_token(token):

                    # Add the graph_access_token to the session storage
                    # if in the request.
                    is_updated, user_session = update_graph_access_token(
                        request.headers.get("HTTP_X_FORWARDED_ACCESS_TOKEN", ""),
                        user_session,
                    )

                    # Commit changes if there are any.
                    if is_updated:
                        await SESSION_SERVICE.update_session(user_session)

            except jwt.ExpiredSignatureError:
                logging.error("Error: Token has expired! Please acquire a new token.")
            except jwt.InvalidSignatureError:
                logging.error(
                    "Error: Token signature is invalid! This token might be tampered with or from an unknown source."
                )

        return await call_next(request)
