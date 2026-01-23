import jwt
import pytest
from pytest_mock import MockerFixture


@pytest.mark.asyncio
async def test_extract_access_token(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    pass
