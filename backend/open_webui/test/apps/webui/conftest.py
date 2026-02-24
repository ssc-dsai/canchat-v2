import shutil

import docker
import docker.errors
import pytest
from open_webui.internal.db_utils import run_migrations
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

_PG_DOCKER_CONTAINER_NAME = "canchat-postgres-unit-test-container-will-get-deleted"
__PG_USER = "user"
__PG_PW = "example"
__PG_DB = "openwebui"
__PG_PORT = 25432


@pytest.fixture(scope="session", params=["postgresql://", "sqlite:///"])
def async_engine_creator(
    request: pytest.FixtureRequest,
    tmp_path_factory: pytest.TempPathFactory,
):
    try:
        param: str = request.param
        match param:
            case url if url.startswith("postgresql"):
                env_vars_postgres = {
                    "POSTGRES_USER": __PG_USER,
                    "POSTGRES_PASSWORD": __PG_PW,
                    "POSTGRES_DB": __PG_DB,
                    "POSTGRES_PORT": __PG_PORT,
                }
                docker_client = docker.from_env()

                try:
                    if c := docker_client.containers.get(_PG_DOCKER_CONTAINER_NAME):
                        c.remove(v=True, force=True)
                except docker.errors.NotFound:
                    pass
                except docker.errors.APIError:
                    pass

                docker_client.containers.run(
                    image="postgres:16.2",
                    detach=True,
                    environment=env_vars_postgres,
                    name=_PG_DOCKER_CONTAINER_NAME,
                    ports={"5432/tcp": __PG_PORT},
                    command="postgres -c log_statement=all",
                    auto_remove=True,
                )

                container = docker_client.containers.get(_PG_DOCKER_CONTAINER_NAME)

                POSTGRES_URL = (
                    f"{param}{__PG_USER}:{__PG_PW}@localhost:{__PG_PORT}/{__PG_DB}"
                )
                run_migrations(POSTGRES_URL)
                engine = create_async_engine(
                    POSTGRES_URL.replace("postgresql://", "postgresql+asyncpg://"),
                    pool_pre_ping=True,
                )
            case url if url.startswith("sqlite"):
                directory = tmp_path_factory.mktemp(
                    "canchat-unit-tests-sqlite", numbered=True
                )
                SQLITE_URL = f"sqlite:///{directory.absolute()}/webui.db"
                run_migrations(SQLITE_URL)
                engine = create_async_engine(
                    SQLITE_URL.replace("sqlite://", "sqlite+aiosqlite://"),
                    connect_args={"check_same_thread": False},
                )

            case _:
                pytest.skip("Unknown db URL.")

        yield engine
    finally:
        match param:
            case url if url.startswith("postgresql"):
                if container:
                    container.remove(v=True, force=True)
            case url if url.startswith("sqlite"):
                shutil.rmtree(directory)
            case _:
                pytest.skip("Unknown db URL.")


@pytest.fixture(scope="session")
def async_session_maker(async_engine_creator: AsyncEngine):

    yield async_sessionmaker(
        bind=async_engine_creator, expire_on_commit=False, class_=AsyncSession
    )
