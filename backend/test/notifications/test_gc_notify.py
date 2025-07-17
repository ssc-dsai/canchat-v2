import os
import pytest
import uuid

from open_webui.models.users import User
from open_webui.notifications.notifier import MessageType, NotificationType
from open_webui.notifications.notifiers.gc_notify.gc_notifier import GCNotify


@pytest.fixture
def setup_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://test-webui.db")
    monkeypatch.setenv("ANOTHER_ENV_VAR", "another_value")


def test_gc_notify(monkeypatch, caplog):
    caplog.set_level("DEBUG", logger="open_webui.models.notifications")

    api_key = os.environ["GC_NOTIFY_TEST_KEY"]

    assert api_key

    notifier = GCNotify(api_key=api_key)
    users = [
        User(
            id=str(uuid.uuid4()),
            name="Test User",
            email="test@test.gc.ca",
        ),
        User(
            name="Test User2",
            id=str(uuid.uuid4()),
            email="test2@test.gc.ca",
        ),
    ]

    assert notifier.notify(
        message_type=MessageType.WELCOME,
        notification_type=NotificationType.EMAIL,
        users=users,
    )
    # notifier.
