from abc import abstractmethod
import logging
import redis.asyncio as redis
from redis.commands.json.path import Path

from open_webui.env import SRC_LOG_LEVELS
from open_webui.session.models import UserSession
from open_webui.session.session_service_abc import SessionService

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["SESSION"])


class RedisSessionService(SessionService):

    _redis: redis.Redis
    _SESSION_PREFIX = "user_session"

    def __init__(self, client: redis.Redis, session_lifetime: int = 60 * 45) -> None:
        self._redis = client
        super().__init__(session_lifetime=session_lifetime)

    @abstractmethod
    def _get_session_id(self, user_id: str) -> str:
        """
        Creates a unique hash key used to store the session.

        :param self: Description
        :param user_id: The id of the user whose session it is.
        :type user_id: str
        :return: A hash to use for storing the session in Redis.
        :rtype: str
        """
        pass


class RedisSessionServiceImpl(RedisSessionService):
    """
    A SessionService which used Redis as a distributed store with basic commands.
    """

    def __init__(self, client: redis.Redis, session_lifetime: int = 60 * 45) -> None:
        super().__init__(client=client, session_lifetime=session_lifetime)

    async def update_session(self, session: UserSession) -> bool:
        try:
            async with self._redis.pipeline(transaction=True) as pipe:
                pipe.set(
                    self._get_session_id(session.user_id),
                    session.model_dump_json(),
                )
                pipe.expire(session.user_id, self._session_lifetime)
                await pipe.execute(raise_on_error=True)
            return True
        except redis.RedisError as e:
            logging.error(f"Error updating session in Redis: {e}")
            return False

    async def remove_session(self, user_id: str):
        await self._redis.delete(self._get_session_id(user_id))

    async def get_session(self, user_id: str) -> UserSession | None:
        if await self._redis.exists(self._get_session_id(user_id)):
            json = await self._redis.get(self._get_session_id(user_id))

            return UserSession.model_validate_json(json)
        else:
            return None

    def _get_session_id(self, user_id: str) -> str:
        """
        Creates a unique hash key used to store the session.

        :param self: Description
        :param user_id: The id of the user whose session it is.
        :type user_id: str
        :return: A hash to use for storing the session in Redis.
        :rtype: str
        """
        return f"{self._SESSION_PREFIX}:{user_id}"


class RedisJSONSessionService(RedisSessionService):
    """
    A SessionService which used Redis as a distributed store with ReJSON module commands.

    Note: Not all redis instances might have the ReJSON module loaded.
    """

    def __init__(self, client: redis.Redis, session_lifetime: int = 60 * 45) -> None:
        super().__init__(client=client, session_lifetime=session_lifetime)

    async def update_session(self, session: UserSession) -> bool:
        try:
            async with self._redis.pipeline(transaction=True) as pipe:
                pipe.json().set(
                    self._get_session_id(session.user_id),
                    Path.root_path(),
                    session.model_dump_json(),
                )
                pipe.expire(session.user_id, self._session_lifetime)
                await pipe.execute(raise_on_error=True)
            return True
        except redis.RedisError as e:
            logging.error(f"Error updating session in Redis: {e}")
            return False

    async def remove_session(self, user_id: str):
        await self._redis.delete(self._get_session_id(user_id))

    async def get_session(self, user_id: str) -> UserSession | None:

        if await self._redis.exists(self._get_session_id(user_id)):
            json = await self._redis.json().get(self._get_session_id(user_id))

            return UserSession.model_validate_json(json)
        else:
            return None

    def _get_session_id(self, user_id: str) -> str:
        """
        Creates a unique hash key used to store the session.

        :param self: Description
        :param user_id: The id of the user whose session it is.
        :type user_id: str
        :return: A hash to use for storing the session in Redis.
        :rtype: str
        """
        return f"{self._SESSION_PREFIX}:json:{user_id}"
