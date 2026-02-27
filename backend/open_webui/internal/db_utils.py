import json
import logging
from contextlib import asynccontextmanager, contextmanager
from typing import Any

from open_webui.env import (
    DATABASE_POOL_MAX_OVERFLOW,
    DATABASE_POOL_RECYCLE,
    DATABASE_POOL_SIZE,
    DATABASE_POOL_TIMEOUT,
    DATABASE_URL,
    OPEN_WEBUI_DIR,
    SRC_LOG_LEVELS,
)
from open_webui.internal.wrappers import register_connection
from peewee_migrate import Router
from sqlalchemy import Dialect, create_engine, types
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy.sql.type_api import _T
from typing_extensions import Self

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["DB"])


class JSONField(types.TypeDecorator):
    impl = types.Text
    cache_ok = True

    def process_bind_param(self, value: _T | None, dialect: Dialect) -> Any:
        return json.dumps(value)

    def process_result_value(self, value: _T | None, dialect: Dialect) -> Any:
        if value is not None:
            return json.loads(value)

    def copy(self, **kw: Any) -> Self:
        return JSONField(self.impl.length)

    def db_value(self, value):
        return json.dumps(value)

    def python_value(self, value):
        if value is not None:
            return json.loads(value)


class DatabaseConnector:
    __session: scoped_session[Session]

    def __init__(self, session: scoped_session[Session]) -> None:
        self.__session = session

    @contextmanager
    def get_db(self):
        db = self.__session()
        try:
            yield db
        finally:
            db.close()


class AsyncDatabaseConnector:
    __async_session: async_sessionmaker[AsyncSession]

    def __init__(self, session: async_sessionmaker[AsyncSession]) -> None:
        self.__async_session = session

    @asynccontextmanager
    async def get_async_db(self):
        """
        Provides an asynchronous SQLAlchemy session.
        This can be used as a dependency in web frameworks like FastAPI.
        """
        db = self.__async_session()
        try:
            yield db
            # For web frameworks, commit/rollback often happens explicitly in routes.
            # If you want to auto-commit on success and rollback on error,
            # you could add:
            # await db.commit()
        except Exception:
            await db.rollback()
            raise
        finally:
            await db.close()


# Workaround to handle the peewee migration
# This is required to ensure the peewee migration is handled before the alembic migration
def handle_peewee_migration(database_url: str):
    db = None
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
        if db:
            db.close()

            # Assert if db connection has been closed
            assert db.is_closed(), "Database connection is still open."


# Function to run the alembic migrations
def run_migrations(database_url: str):
    print("Running migrations")
    handle_peewee_migration(database_url)
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


def get_async_session_maker(database_url: str = DATABASE_URL):
    SQLALCHEMY_DATABASE_URL = database_url
    if "sqlite" in SQLALCHEMY_DATABASE_URL:
        __db_url = SQLALCHEMY_DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")
        async_engine = create_async_engine(
            __db_url, connect_args={"check_same_thread": False}
        )
    else:
        __db_url: str = SQLALCHEMY_DATABASE_URL
        if "postgresql" in SQLALCHEMY_DATABASE_URL:
            __db_url = SQLALCHEMY_DATABASE_URL.replace(
                "postgresql://", "postgresql+asyncpg://"
            )

        if DATABASE_POOL_SIZE > 0:
            async_engine = create_async_engine(
                __db_url,
                pool_size=DATABASE_POOL_SIZE,
                max_overflow=DATABASE_POOL_MAX_OVERFLOW,
                pool_timeout=DATABASE_POOL_TIMEOUT,
                pool_recycle=DATABASE_POOL_RECYCLE,
                pool_pre_ping=True,
            )
        else:
            async_engine = create_async_engine(__db_url, pool_pre_ping=True)

    return async_sessionmaker(
        bind=async_engine,
        expire_on_commit=False,  # Recommended for async
        class_=AsyncSession,  # Ensure it's an AsyncSession
    )
