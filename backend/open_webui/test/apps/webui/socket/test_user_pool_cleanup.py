import asyncio
from unittest.mock import AsyncMock


class FakeRedisDict:
    store = {}

    def __init__(self, name, redis_url):
        del redis_url
        self.name = name
        if name not in self.store:
            self.store[name] = {}
        self._bucket = self.store[name]

    def __setitem__(self, key, value):
        self._bucket[key] = value

    def __getitem__(self, key):
        return self._bucket[key]

    def __delitem__(self, key):
        del self._bucket[key]

    def __contains__(self, key):
        return key in self._bucket

    def keys(self):
        return list(self._bucket.keys())

    def get(self, key, default=None):
        return self._bucket.get(key, default)

    @classmethod
    def reset(cls):
        cls.store = {}


def _setup_scheduler_redis(monkeypatch):
    from open_webui import scheduler
    from open_webui.socket import utils

    FakeRedisDict.reset()
    monkeypatch.setattr(scheduler, "WEBSOCKET_MANAGER", "redis")
    monkeypatch.setattr(scheduler, "WEBSOCKET_REDIS_URL", "redis://test")
    monkeypatch.setattr(utils, "RedisDict", FakeRedisDict)
    return scheduler


def test_user_pool_cleanup_keeps_users_with_active_sessions(monkeypatch):
    """
    Scheduler cleanup should preserve users that still have active socket sessions.
    """
    scheduler = _setup_scheduler_redis(monkeypatch)
    FakeRedisDict.store["open-webui: session_pool"] = {"sid1": {}, "sid2": {}}
    FakeRedisDict.store["open-webui:user_pool"] = {
        "user-a": ["sid1"],
        "user-b": ["sid2"],
    }

    asyncio.run(scheduler.automated_user_pool_cleanup())

    assert FakeRedisDict.store["open-webui:user_pool"] == {
        "user-a": ["sid1"],
        "user-b": ["sid2"],
    }


def test_user_pool_cleanup_removes_users_without_active_sessions(monkeypatch):
    """
    Scheduler cleanup should remove users whose session ids are all stale.
    """
    scheduler = _setup_scheduler_redis(monkeypatch)
    FakeRedisDict.store["open-webui: session_pool"] = {"sid1": {}}
    FakeRedisDict.store["open-webui:user_pool"] = {
        "user-a": ["sid1"],
        "user-b": ["sid-x"],
    }

    asyncio.run(scheduler.automated_user_pool_cleanup())

    assert FakeRedisDict.store["open-webui:user_pool"] == {"user-a": ["sid1"]}


def test_user_pool_cleanup_prunes_stale_sids_for_active_user(monkeypatch):
    """
    Scheduler cleanup should keep active sids and prune stale ones for mixed entries.
    """
    scheduler = _setup_scheduler_redis(monkeypatch)
    FakeRedisDict.store["open-webui: session_pool"] = {"sid1": {}}
    FakeRedisDict.store["open-webui:user_pool"] = {"user-a": ["sid1", "sid-x"]}

    asyncio.run(scheduler.automated_user_pool_cleanup())

    assert FakeRedisDict.store["open-webui:user_pool"] == {"user-a": ["sid1"]}


def test_user_pool_cleanup_is_skipped_when_not_using_redis(monkeypatch):
    """
    Cleanup job should not run when websocket manager is not Redis-backed.
    """
    from open_webui import scheduler

    monkeypatch.setattr(scheduler, "WEBSOCKET_MANAGER", "memory")
    monkeypatch.setattr(scheduler, "WEBSOCKET_REDIS_URL", "redis://test")

    # Should return early without touching RedisDict setup.
    asyncio.run(scheduler.automated_user_pool_cleanup())


def test_disconnect_handles_missing_user_pool_entry():
    """
    Disconnect should be resilient if USER_POOL has a missing user_id.
    """
    from open_webui.socket import main as socket_main

    socket_main.SESSION_POOL = {"sid1": {"id": "user-a", "name": "User A"}}
    socket_main.USER_POOL = {}
    socket_main.sio.emit = AsyncMock()

    asyncio.run(socket_main.disconnect("sid1"))

    assert "sid1" not in socket_main.SESSION_POOL
    socket_main.sio.emit.assert_awaited_once_with("user-list", {"user_ids": []})


def test_disconnect_removes_sid_but_keeps_user_when_other_sessions_exist():
    """
    Disconnect should remove only the current sid and keep user presence when
    additional active session ids remain for that user.
    """
    from open_webui.socket import main as socket_main

    socket_main.SESSION_POOL = {"sid1": {"id": "user-a", "name": "User A"}}
    socket_main.USER_POOL = {"user-a": ["sid1", "sid2"]}
    socket_main.sio.emit = AsyncMock()

    asyncio.run(socket_main.disconnect("sid1"))

    assert "sid1" not in socket_main.SESSION_POOL
    assert socket_main.USER_POOL["user-a"] == ["sid2"]
    socket_main.sio.emit.assert_awaited_once_with("user-list", {"user_ids": ["user-a"]})


def test_disconnect_removes_user_when_last_session_disconnects():
    """
    Disconnect should remove the user from USER_POOL when their last sid leaves.
    """
    from open_webui.socket import main as socket_main

    socket_main.SESSION_POOL = {"sid1": {"id": "user-a", "name": "User A"}}
    socket_main.USER_POOL = {"user-a": ["sid1"]}
    socket_main.sio.emit = AsyncMock()

    asyncio.run(socket_main.disconnect("sid1"))

    assert "sid1" not in socket_main.SESSION_POOL
    assert "user-a" not in socket_main.USER_POOL
    socket_main.sio.emit.assert_awaited_once_with("user-list", {"user_ids": []})
