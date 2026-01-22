import logging
import redis.asyncio as redis
from redis.commands.json.path import Path

from open_webui.session.models import UserSession
from open_webui.session.session_service import SessionService


class RedisSessionService(SessionService):
    """
    Docstring for RedisSessionService
    """

    _redis: redis.Redis
    __SESSION_PREFIX = "user_session"

    def __init__(self, client: redis.Redis, session_lifetime: int = 60 * 45) -> None:

        self._redis = client
        super().__init__(session_lifetime=session_lifetime)

    async def update_session(self, session: UserSession) -> bool:
        try:
            async with self._redis.pipeline(transaction=True) as pipe:
                pipe.json().set(
                    self.__get_session_id(session.user_id),
                    Path.root_path(),
                    session.model_dump_json(),
                )
                pipe.expire(session.user_id, self._session_lifetime)
                await pipe.execute(raise_on_error=True)
            return True
        except redis.RedisError as e:
            logging.error("Error updating session in Redis.")
            return False

    async def remove_session(self, user_id: str):
        await self._redis.delete(self.__get_session_id(user_id))

    async def get_session(self, user_id: str) -> UserSession | None:

        if await self._redis.exists(self.__get_session_id(user_id)):
            json = await self._redis.json().get(self.__get_session_id(user_id))

            return UserSession.model_validate_json(json)
        else:
            return None

    def __get_session_id(self, user_id: str) -> str:
        """
        Docstring for __get_session_id

        :param self: Description
        :param user_id: Description
        :type user_id: str
        :return: Description
        :rtype: str
        """
        return f"{self.__SESSION_PREFIX}:{user_id}"
