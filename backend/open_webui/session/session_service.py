from abc import ABC, abstractmethod

from open_webui.session.models import UserSession


class SessionService(ABC):
    """
    Docstring for SessionService
    """

    _session_lifetime: int = 60 * 45

    def __init__(self, session_lifetime: int) -> None:
        self._session_lifetime = session_lifetime
        super().__init__()

    @abstractmethod
    async def get_session(self, user_id: str) -> UserSession | None:
        """
        Docstring for get_session

        :param self: The SessionService.
        :param user_id: The user_id of the session to get.
        :type user_id: str
        :return: The requested UserSession or None if there isn't one.
        :rtype: UserSession | None
        """
        pass

    @abstractmethod
    async def remove_session(self, user_id: str):
        """
        Docstring for remove_session

        :param self: Description
        :param user_id: Description
        :type user_id: str
        """
        pass

    @abstractmethod
    async def update_session(self, session: UserSession) -> bool:
        """
        Docstring for update_session

        :param self: Description
        :param session: Description
        :type session: UserSession
        :return: Description
        :rtype: bool
        """
        pass
