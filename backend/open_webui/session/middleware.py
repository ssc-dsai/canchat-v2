import logging
from typing import Tuple
from fastapi import Request
import jwt
from starlette.middleware.base import BaseHTTPMiddleware

from open_webui.env import SRC_LOG_LEVELS
from open_webui.session.models import UserAuth, UserSession
from open_webui.utils.auth import decode_token, extract_token_from_auth_header

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["SESSION"])


def extract_jwt_expiry(token: str) -> int:
    """
    Extracts the expiry time (Unix timestamp) from a JWT.

    :param token: The JWT from which to extract the expiry.
    :type token: str
    :return: A Unix timestamp (epoch) in seconds.
    :rtype: int
    """
    if token:
        # Extract token information without verifying signature
        # Tokens can currently come from two different AppIDs
        token_decoded = jwt.decode(token, options={"verify_signature": False})

        # Claims Reference: https://learn.microsoft.com/en-us/entra/identity-platform/access-token-claims-reference
        return int(token_decoded["exp"])
    else:
        return -1


def update_graph_access_token(
    token: str, session: UserSession
) -> Tuple[bool, UserSession]:
    """
    Performs an update to the UserSession based on the provided JWT.

    :param token: The JWT add to the session.
    :type token: str
    :param session: The session object to add the JWT to.
    :type session: UserSession
    :return: A tuple of a bool representing the if the session was updated and the session object.
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
    Gets the a session object based off of the user id in the token.

    :param token: The JWT.
    :type token: str
    :return: Returns the session object or None if there are issues.
    :rtype: UserSession | None
    """
    try:
        from open_webui.session.session_service import SESSION_SERVICE

        payload = decode_token(token)

        # Extract user's id from
        if user_id := payload.get("id", None):
            user_session = await SESSION_SERVICE.get_session(user_id) or UserSession(
                user_id=user_id
            )

            return user_session
    except jwt.ExpiredSignatureError:
        logging.error("Error: Token has expired! Please acquire a new token.")
    except jwt.InvalidSignatureError:
        logging.error(
            "Error: Token signature is invalid! This token might be tampered with or from an unknown source."
        )

    return None


class UserSessionMiddleware(BaseHTTPMiddleware):
    """
    Middleware which populates the UserSession with valid info.
    """

    async def dispatch(self, request: Request, call_next):
        from open_webui.session.session_service import SESSION_SERVICE

        is_updated = False
        # Get token if available in Request
        if token := (
            request.cookies.get("token")
            or extract_token_from_auth_header(request.headers.get("Authorization", ""))
        ):

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

        return await call_next(request)
