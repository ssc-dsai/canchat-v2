import time
from typing import Annotated

from pydantic import Field

from open_webui.session.models import UserSession
from open_webui.session.session_service import SessionService


class TimedUserSession(UserSession):
    """
    A UserSession which tracks the last time it was updated.
    """

    updated_at: Annotated[
        int, Field(description="The epoch time when the session was last updated.")
    ]


class DictSessionService(SessionService):
    """
    A session storage service backed by a python dict.

    SHOULD NOT be used when running with replication since
    sessions will not be shared across instances.
    """

    __session_store: dict[str, TimedUserSession]
    __last_cleaned: int = int(time.time())
    __clean_interval: int = 60  # 1 min
    __session_lifetime: int = 60 * 30  # 30 min

    def __init__(self) -> None:
        self.__session_store = dict()
        super().__init__()

    async def __clean_expired_sessions(self):
        """
        Docstring for __clean_expired_sessions

        :param self: Description
        """

        current_time = int(time.time())

        # If has not been cleaned since last Winterval.
        if current_time - self.__last_cleaned > self.__clean_interval:

            self.__last_cleaned = current_time

            for user_id, session in self.__session_store.items():
                if current_time - session.updated_at > self.__session_lifetime:
                    await self.remove_session(user_id=user_id)

    async def get_session(self, user_id: str) -> UserSession | None:
        """
        Docstring for get_session

        :param self: Description
        :param user_id: Description
        :type user_id: str
        :return: Description
        :rtype: UserSession | None
        """

        await self.__clean_expired_sessions()

        return self.__session_store.get(user_id, None)

    async def remove_session(self, user_id: str):
        """
        Docstring for remove_session

        :param self: Description
        :param user_id: Description
        :type user_id: str
        """

        await self.__clean_expired_sessions()

        try:
            self.__session_store.pop(user_id)
        except KeyError:
            pass

    async def update_session(self, session: UserSession) -> bool:
        """
        Docstring for update_session

        :param self: Description
        :param session: Description
        :type session: UserSession
        :return: Description
        :rtype: bool
        """

        await self.__clean_expired_sessions()

        s = TimedUserSession(**session.model_dump())
        s.updated_at = int(time.time())
        self.__session_store[session.user_id] = s
        return True
