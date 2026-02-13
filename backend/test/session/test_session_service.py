import pytest
from pytest_mock import MockerFixture
import redis.asyncio as redis

from open_webui.env import REDIS_URL
from open_webui.session.session_service_redis import RedisSessionServiceImpl
from open_webui.session.session_service_dict import DictSessionService
import open_webui.session.session_service as ss


@pytest.mark.asyncio
async def test_setup_session_service_dict(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):

    # Ensure no REDIS_URL set
    monkeypatch.setattr(ss, "REDIS_URL", "")
    # Rerun setup
    await ss.setup_session_service()

    assert isinstance(ss.SESSION_SERVICE, DictSessionService)


@pytest.mark.skipif(not REDIS_URL, reason="REDIS_URL not set skipping.")
@pytest.mark.asyncio
async def test_setup_session_service_redis(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    try:
        client = await redis.from_url(REDIS_URL)
        await client.ping()
    except redis.ConnectionError:
        pytest.skip("No connection to Redis.")

    # Ensure no REDIS_URL set
    monkeypatch.setattr(ss, "REDIS_URL", REDIS_URL)
    # Rerun setup
    await ss.setup_session_service()

    assert isinstance(ss.SESSION_SERVICE, RedisSessionServiceImpl)
