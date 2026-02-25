import pytest
from open_webui.internal.db_utils import AsyncDatabaseConnector
from open_webui.models.auths_table import AuthsTable
from open_webui.models.channels import ChannelTable
from open_webui.models.chats import ChatTable
from open_webui.models.domains import DomainTable
from open_webui.models.export_logs import ExportLogsTable
from open_webui.models.feedbacks import FeedbackTable
from open_webui.models.files import FilesTable
from open_webui.models.folders import FolderTable
from open_webui.models.functions import FunctionsTable
from open_webui.models.groups import GroupTable
from open_webui.models.knowledge import KnowledgeTable
from open_webui.models.memories import MemoriesTable
from open_webui.models.message_metrics import MessageMetricsTable
from open_webui.models.messages import MessageTable
from open_webui.models.models import ModelsTable
from open_webui.models.prompts import PromptsTable
from open_webui.models.tags import TagTable
from open_webui.models.tools import ToolsTable
from open_webui.models.users import UsersTable
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

"""
Configuration of the fixtures used for each of the table services.
"""


@pytest.fixture(scope="session")
def db_connector(
    async_session_maker: async_sessionmaker[AsyncSession],
):
    yield AsyncDatabaseConnector(async_session_maker)


@pytest.fixture(scope="session")
def auths_table(
    db_connector: AsyncDatabaseConnector,
    group_table: GroupTable,
    users_table: UsersTable,
):
    yield AuthsTable(db_connector, group_table, users_table)


@pytest.fixture(scope="session")
def channel_table(
    db_connector: AsyncDatabaseConnector,
):
    yield ChannelTable(db_connector=db_connector)


@pytest.fixture(scope="session")
def chat_table(db_connector: AsyncDatabaseConnector, tag_table: TagTable):
    yield ChatTable(db_connector=db_connector, tag_table=tag_table)


@pytest.fixture(scope="session")
def domain_table(
    db_connector: AsyncDatabaseConnector,
):
    yield DomainTable(db_connector=db_connector)


@pytest.fixture(scope="session")
def export_logs_table(
    db_connector: AsyncDatabaseConnector,
):
    yield ExportLogsTable(db_connector=db_connector)


@pytest.fixture(scope="session")
def feedback_table(
    db_connector: AsyncDatabaseConnector,
):
    yield FeedbackTable(db_connector=db_connector)


@pytest.fixture(scope="session")
def files_table(
    db_connector: AsyncDatabaseConnector,
):
    yield FilesTable(db_connector=db_connector)


@pytest.fixture(scope="session")
def folder_table(db_connector: AsyncDatabaseConnector, chat_table: ChatTable):

    yield FolderTable(db_connector=db_connector, chats=chat_table)


@pytest.fixture(scope="session")
def functions_table(db_connector: AsyncDatabaseConnector, users_table: UsersTable):

    yield FunctionsTable(db_connector=db_connector, users_table=users_table)


@pytest.fixture(scope="session")
def group_table(db_connector: AsyncDatabaseConnector, users_table: UsersTable):

    yield GroupTable(db_connector=db_connector, users_table=users_table)


@pytest.fixture(scope="session")
def knowledge_table(db_connector: AsyncDatabaseConnector, users_table: UsersTable):

    yield KnowledgeTable(db_connector=db_connector, users_table=users_table)


@pytest.fixture(scope="session")
def memories_table(
    db_connector: AsyncDatabaseConnector,
):

    yield MemoriesTable(db_connector=db_connector)


@pytest.fixture(scope="session")
def message_table(
    db_connector: AsyncDatabaseConnector,
):

    yield MessageTable(db_connector=db_connector)


@pytest.fixture(scope="session")
def message_metrics_table(
    db_connector: AsyncDatabaseConnector,
):

    yield MessageMetricsTable(db_connector=db_connector)


@pytest.fixture(scope="session")
def models_table(db_connector: AsyncDatabaseConnector, users_table: UsersTable):

    yield ModelsTable(db_connector=db_connector, users_table=users_table)


@pytest.fixture(scope="session")
def prompts_table(db_connector: AsyncDatabaseConnector, users_table: UsersTable):

    yield PromptsTable(db_connector=db_connector, users_table=users_table)


@pytest.fixture(scope="session")
def tag_table(
    db_connector: AsyncDatabaseConnector,
):

    yield TagTable(db_connector=db_connector)


@pytest.fixture(scope="session")
def tools_table(db_connector: AsyncDatabaseConnector, users_table: UsersTable):

    yield ToolsTable(db_connector=db_connector, users_table=users_table)


@pytest.fixture(scope="session")
def users_table(db_connector: AsyncDatabaseConnector, chat_table: ChatTable):

    users_table = UsersTable(db_connector=db_connector, chats=chat_table)
    yield users_table
