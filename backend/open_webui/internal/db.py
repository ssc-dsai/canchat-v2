from abc import ABC
import json
import logging
from contextlib import contextmanager
from typing import Any, Optional, overload

from open_webui.internal.wrappers import register_connection
from open_webui.env import (
    OPEN_WEBUI_DIR,
    DATABASE_URL,
    SRC_LOG_LEVELS,
    DATABASE_POOL_MAX_OVERFLOW,
    DATABASE_POOL_RECYCLE,
    DATABASE_POOL_SIZE,
    DATABASE_POOL_TIMEOUT,
)
from peewee_migrate import Router
from sqlalchemy import Dialect, create_engine, types
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.sql.type_api import _T
from typing_extensions import Self

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["DB"])


class JSONField(types.TypeDecorator):
    impl = types.Text
    cache_ok = True

    def process_bind_param(self, value: Optional[_T], dialect: Dialect) -> Any:
        return json.dumps(value)

    def process_result_value(self, value: Optional[_T], dialect: Dialect) -> Any:
        if value is not None:
            return json.loads(value)

    def copy(self, **kw: Any) -> Self:
        return JSONField(self.impl.length)

    def db_value(self, value):
        return json.dumps(value)

    def python_value(self, value):
        if value is not None:
            return json.loads(value)


# Workaround to handle the peewee migration
# This is required to ensure the peewee migration is handled before the alembic migration
def handle_peewee_migration(database_url: str):
    # db = None
    try:
        # Replace the postgresql:// with postgres:// to handle the peewee migration
        db = register_connection(database_url.replace("postgresql://", "postgres://"))
        migrate_dir = OPEN_WEBUI_DIR / "internal" / "migrations"
        router = Router(db, logger=log, migrate_dir=migrate_dir)
        router.run()
        db.close()

    except Exception as e:
        log.error(f"Failed to initialize the database connection: {e}")
        raise
    finally:
        # Properly closing the database connection
        if db and not db.is_closed():
            db.close()

        # Assert if db connection has been closed
        assert db.is_closed(), "Database connection is still open."


# Function to run the alembic migrations
def run_migrations(database_url: str):
    handle_peewee_migration(database_url)
    print("Running migrations")
    try:
        from alembic import command
        from alembic.config import Config

        alembic_cfg = Config(OPEN_WEBUI_DIR / "alembic.ini")

        # Set the script location dynamically
        migrations_path = OPEN_WEBUI_DIR / "migrations"
        alembic_cfg.set_main_option("script_location", str(migrations_path))
        alembic_cfg.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        print(f"Error: {e}")


run_migrations(DATABASE_URL)


def get_session_maker(database_url: str = DATABASE_URL):
    SQLALCHEMY_DATABASE_URL = database_url
    if "sqlite" in SQLALCHEMY_DATABASE_URL:
        engine = create_engine(
            SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
        )
    else:
        if DATABASE_POOL_SIZE > 0:
            engine = create_engine(
                SQLALCHEMY_DATABASE_URL,
                pool_size=DATABASE_POOL_SIZE,
                max_overflow=DATABASE_POOL_MAX_OVERFLOW,
                pool_timeout=DATABASE_POOL_TIMEOUT,
                pool_recycle=DATABASE_POOL_RECYCLE,
                pool_pre_ping=True,
                poolclass=QueuePool,
            )
        else:
            engine = create_engine(
                SQLALCHEMY_DATABASE_URL, pool_pre_ping=True, poolclass=NullPool
            )

    return sessionmaker(
        autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
    )


Session = scoped_session(get_session_maker(DATABASE_URL))


class DatabaseConnector:
    database_url: str

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    @contextmanager
    def get_db(self):
        db = get_session_maker(database_url=self.database_url)()
        try:
            yield db
        finally:
            db.close()


class DatabaseService(ABC):
    db: DatabaseConnector

    @overload
    def __init__(self, database: str) -> None: ...

    @overload
    def __init__(self, database: DatabaseConnector) -> None: ...

    def __init__(self, database: str | DatabaseConnector) -> None:
        if isinstance(database, str):
            self.db = DatabaseConnector(database_url=database)
        elif isinstance(database, DatabaseConnector):
            self.db = database
        else:
            raise TypeError("database is not a str or a DatabaseConnector")


DATABASE_CONNECTOR = DatabaseConnector(database_url=DATABASE_URL)

# For backwards compatibility until everything can move to using the DatabaseService class
get_db = DATABASE_CONNECTOR.get_db
