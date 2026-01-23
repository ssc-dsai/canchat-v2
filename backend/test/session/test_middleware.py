import datetime
import uuid
import pytest

from pytest_mock import MockerFixture
from open_webui.session.middleware import get_session_from_token
import open_webui.utils.auth as auth

from open_webui.session.session_service import setup_session_service

SESSION_SECRET_1 = "this-is-a-secret-asdasd"
SESSION_SECRET_2 = "this-is-a-different-secret"


@pytest.mark.asyncio
async def test_get_session_from_token(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    await setup_session_service()

    # Set a secret for the test
    monkeypatch.setattr(auth, "SESSION_SECRET", SESSION_SECRET_1)

    USER_ID = str(uuid.uuid4())
    TIME_DELTA = datetime.timedelta(seconds=60)

    token_1 = auth.create_token(
        data={"id": USER_ID},
        expires_delta=TIME_DELTA,
    )

    session = await get_session_from_token(token_1)
    assert session


@pytest.mark.asyncio
async def test_get_session_from_invalid_token(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    await setup_session_service()

    # Set a secret for the test
    monkeypatch.setattr(auth, "SESSION_SECRET", SESSION_SECRET_1)

    USER_ID = str(uuid.uuid4())
    TIME_DELTA = datetime.timedelta(seconds=60)

    token_1 = auth.create_token(
        data={"id": USER_ID},
        expires_delta=TIME_DELTA,
    )

    # Set a secret for the test
    monkeypatch.setattr(auth, "SESSION_SECRET", SESSION_SECRET_2)

    session = await get_session_from_token(token_1)

    # SESSION_SECRET is not equal to one which created original token
    # meaning the signature verification will fail and session will not be returned.
    assert not session
