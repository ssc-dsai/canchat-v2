import logging

from open_webui.env import (
    DATABASE_URL,
    SRC_LOG_LEVELS,
)
from open_webui.internal.db_utils import (
    AsyncDatabaseConnector,
    DatabaseConnector,
    get_async_session_maker,
    get_session_maker,
    run_migrations,
)
from sqlalchemy.orm import scoped_session

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["DB"])

# Run the peewee and alembic migrations
run_migrations(DATABASE_URL)


DB_SESSION = scoped_session(get_session_maker(DATABASE_URL))
DATABASE_CONNECTOR = DatabaseConnector(session=DB_SESSION)

# For backwards compatibility until everything can move to using the DatabaseService class
# Leaving in place a Blocking context manager for the config
get_db = DATABASE_CONNECTOR.get_db


ASYNC_SESSION_LOCAL = get_async_session_maker(DATABASE_URL)
ASYNC_DATABASE_CONNECTOR = AsyncDatabaseConnector(session=ASYNC_SESSION_LOCAL)

get_async_db = ASYNC_DATABASE_CONNECTOR.get_async_db
