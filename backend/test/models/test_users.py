import pytest
from pytest_mock import MockerFixture

from open_webui.models.users import Users
from open_webui.models.notifications import MessageType, NotificationType, Notifications

from test.conftest import setup_clean_db  # type: ignore
from test.test_utils.user_utils import create_user


def test_get_users_without_welcome_notification(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    setup_clean_db: None,
):
    caplog.set_level("DEBUG", logger="open_webui.models.users")

    u = create_user(name="Test User", email="test@ssc-spc.gc.ca")
    user = Users.insert_new_user(
        id=u.id,
        name=u.name,
        email=u.email,
    )
    assert user != None

    users_without_welcome = Users.get_users_without_welcome_notification()
    assert len(users_without_welcome) == 1

    notification = Notifications.insert_new_notification(
        user_id=user.id,
        message_type=MessageType.WELCOME,
        notification_type=NotificationType.EMAIL,
        is_sent=True,
        is_received=False,
        notifier_used="unit_test",
        status="bob",
    )
    assert notification != None

    users_without_welcome_after_insert = Users.get_users_without_welcome_notification()
    assert len(users_without_welcome_after_insert) == 0
