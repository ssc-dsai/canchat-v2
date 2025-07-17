import os
import pytest
import shutil
import tempfile

TEMP_DIR = tempfile.mkdtemp()


def pytest_configure(config: pytest.Config):
    # os.environ["DATABASE_URL"]= f"sqlite://{Path(__file__).parent}/test-webui.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(TEMP_DIR, 'test-webui.db')}"
    pass


def pytest_sessionstart(session):
    """Create a temporary directory at the start of the test session."""
    session.temp_dir = TEMP_DIR
    print(f"Temporary directory created: {session.temp_dir}")


def pytest_sessionfinish(session, exitstatus):
    """Clean up the temporary directory at the end of the test session."""
    if hasattr(session, "temp_dir"):
        shutil.rmtree(session.temp_dir)
        print(f"Temporary directory removed: {session.temp_dir}")
