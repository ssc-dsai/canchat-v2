import os
import uuid
import pytest
from pytest_mock import MockerFixture
import shutil
import tempfile

"""
Top level configurations for pytest.

This file will always be run first and can be used to setup a general testing environment.
"""

GLOBAL_TEST_TEMPFOLDER = tempfile.mkdtemp()
GLOBAL_TEST_DB_URL = (
    f"sqlite:///{os.path.join(GLOBAL_TEST_TEMPFOLDER, 'test-webui.db')}"
)


def pytest_configure(config: pytest.Config):
    # os.environ["DATABASE_URL"]= f"sqlite://{Path(__file__).parent}/test-webui.db"
    # os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(TEMP_DIR, 'test-webui.db')}"
    print(f"Global tempory test folder: {GLOBAL_TEST_TEMPFOLDER}")
    os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", GLOBAL_TEST_DB_URL)
    pass


# def pytest_sessionstart(session):
#     """Create a temporary directory at the start of the test session."""
#     session.temp_dir = TEMP_DIR
#     print(f"Temporary directory created: {session.temp_dir}")


def pytest_sessionfinish(session, exitstatus):
    """Clean up the temporary directory at the end of the test session."""
    print(f"\nCleaning up temp folder: {GLOBAL_TEST_TEMPFOLDER}")
    shutil.rmtree(GLOBAL_TEST_TEMPFOLDER)


# @pytest.fixture(autouse=True)
@pytest.fixture
def setup_clean_db(mocker: MockerFixture):
    """
    Fixture which sets up a new clean database to use for a test.
    """
    test_db_name = f"{uuid.uuid4()}.db"
    test_db_path = os.path.join(GLOBAL_TEST_TEMPFOLDER, test_db_name)
    test_db_url = f"sqlite:///{test_db_path}"
    # Code to run before each test
    print(f"\nSetting up new database: {test_db_url}")
    from open_webui.internal.db import DATABASE_CONNECTOR, run_migrations

    run_migrations(test_db_url)
    mocker.patch.object(DATABASE_CONNECTOR, "database_url", test_db_url)

    yield  # The test will execute here
    # Code to run after each test
