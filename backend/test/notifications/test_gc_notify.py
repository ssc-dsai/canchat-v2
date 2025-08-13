import os
import pytest
from pytest_mock import MockerFixture

from open_webui.models.notifications import Notifications
from open_webui.models.users import UserModel
from open_webui.notifications.notifier import MessageType, NotificationType
from open_webui.notifications.notifiers.gc_notify.gc_notifier import GCNotify

from test.conftest import setup_clean_db  # type: ignore
from test.test_utils.user_utils import create_user


def test_gc_notify(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    setup_clean_db: None,
):
    caplog.set_level("DEBUG", logger="open_webui.models.notifications")

    api_key = os.environ["GC_NOTIFY_TEST_KEY"]
    assert api_key

    notifier = GCNotify(api_key=api_key)
    users: list[UserModel] = [
        create_user(name="Test User", email="test@ssc-spc.gc.ca"),
        create_user(name="Test User2", email="test2@test.gc.ca"),
    ]

    assert notifier.notify(
        message_type=MessageType.WELCOME,
        notification_type=NotificationType.EMAIL,
        users=users,
    )

    for user in users:
        notifications = Notifications.get_by_user_id(user_id=user.id)
        assert len(notifications) == 1
