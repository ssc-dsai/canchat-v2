import os
import pytest
import redis.asyncio as redis

from pytest_mock import MockerFixture
from open_webui.session.models import UserSession
from open_webui.session.session_service_redis import RedisSessionService

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
REDIS_CLIENT: redis.Redis


@pytest.fixture(scope="session")
async def redis_client_fixture():
    try:
        REDIS_CLIENT = await redis.from_url(REDIS_URL)
        await REDIS_CLIENT.ping()
    except redis.ConnectionError:
        pytest.skip("No connection to Redis.")

    return REDIS_CLIENT


@pytest.mark.asyncio
async def test_redis_session_service(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    redis_client_fixture: redis.Redis,
):
    client = await redis_client_fixture
    session_storage = RedisSessionService(client=client)

    session = UserSession(user_id="6b553593-5ff3-45b3-8127-afa69bb1cce4")

    assert await session_storage.update_session(session=session)

    session2 = await session_storage.get_session("6b553593-5ff3-45b3-8127-afa69bb1cce4")

    assert session2
