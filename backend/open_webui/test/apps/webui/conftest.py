import asyncio
import shutil
import time

import docker
import docker.errors
import pytest
import pytest_asyncio
from open_webui.internal.db_utils import get_async_session_maker, run_migrations

_PG_DOCKER_CONTAINER_NAME = "canchat-postgres-unit-test-container-will-get-deleted"
__PG_USER = "user"
__PG_PW = "example"
__PG_DB = "openwebui"
__PG_PORT = 25432


@pytest_asyncio.fixture(scope="session")
async def event_loop():
    """
    Creates a session-scoped event loop for async tests.
    All async fixtures and tests will run on this loop.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", params=["postgresql://", "sqlite:///"])
async def async_session_maker(
    event_loop,
    request: pytest.FixtureRequest,
    tmp_path_factory: pytest.TempPathFactory,
):
    try:
        param: str = request.param
        match param:
            case url if url.startswith("postgres"):
                # Setup database for tests.
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

                time.sleep(2)
                container = docker_client.containers.get(_PG_DOCKER_CONTAINER_NAME)

                current_time = time.time()
                for line in container.logs(stream=True, follow=True):
                    # Wait for database to be ready or for five seconds
                    if "ready to accept connections" in line.decode():
                        time.sleep(1)
                        break
                    elif time.time() - current_time > 5:
                        pytest.skip("PostgreSQL did not come up withing 5 seconds.")

                DB_URL = f"{param}{__PG_USER}:{__PG_PW}@localhost:{__PG_PORT}/{__PG_DB}"

            case url if url.startswith("sqlite"):
                directory = tmp_path_factory.mktemp(
                    "canchat-unit-tests-sqlite", numbered=True
                )
                DB_URL = f"sqlite:///{directory.absolute()}/webui.db"

            case _:
                pytest.skip("Unknown db URL.")

        run_migrations(DB_URL)
        yield get_async_session_maker(DB_URL)

    finally:
        match param:
            case url if url.startswith("postgresql"):
                if container:
                    container.remove(v=True, force=True)
            case url if url.startswith("sqlite"):
                shutil.rmtree(directory)
            case _:
                pytest.skip("Unknown db URL.")


# @pytest.fixture(scope="session")
# def async_session_maker(async_engine_creator: AsyncEngine):

#     yield async_sessionmaker(
#         bind=async_engine_creator, expire_on_commit=False, class_=AsyncSession
#     )
