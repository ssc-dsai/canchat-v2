import os
import pytest
import time
import uuid

from open_webui.models.users import UserModel
from open_webui.notifications.notifier import MessageType, NotificationType
from open_webui.notifications.notifiers.gc_notify.gc_notifier import GCNotify


@pytest.fixture
def setup_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://test-webui.db")
    monkeypatch.setenv("ANOTHER_ENV_VAR", "another_value")

def _create_user(name: str, email: str) -> UserModel:
  return UserModel(
     id=str(uuid.uuid4()),
     name=name,
     email=email,
     domain=email.split("@")[1],
     created_at=int(time.time()),
     last_active_at=int(time.time()),
     updated_at=int(time.time()),
     profile_image_url="",
  )

def test_gc_notify(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture):
    caplog.set_level("DEBUG", logger="open_webui.models.notifications")

    api_key = os.environ["GC_NOTIFY_TEST_KEY"]

    assert api_key

    notifier = GCNotify(api_key=api_key)
    users = [
       _create_user(name="Test User", email="test@ssc-spc.gc.ca"),
       _create_user(name="Test User2", email="test2@test.gc.ca"),
    ]

    assert notifier.notify(
        message_type=MessageType.WELCOME,
        notification_type=NotificationType.EMAIL,
        users=users,
    )
    # notifier.
