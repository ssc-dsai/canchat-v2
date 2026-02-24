import logging
import redis.asyncio as redis

from open_webui.session.session_service_redis import RedisSessionServiceImpl
from open_webui.session.session_service_dict import DictSessionService
from open_webui.session.session_service_abc import SessionService
from open_webui.env import REDIS_URL, SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["SESSION"])


async def setup_session_service():
    __service: SessionService = DictSessionService()
    if REDIS_URL:
        try:
            client: redis.Redis = redis.from_url(REDIS_URL)
            await client.ping()
            modules = await client.module_list()
            __service = RedisSessionServiceImpl(client=client)
        except redis.ConnectionError:
            log.error("No connectivity to Redis, unable to create SessionService.")
            log.error("Falling back on DictSessionService.")

    global SESSION_SERVICE
    SESSION_SERVICE = __service


SESSION_SERVICE: SessionService
