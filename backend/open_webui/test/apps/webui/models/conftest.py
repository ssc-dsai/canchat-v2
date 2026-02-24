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


@pytest.fixture(scope="class")
def auths_table(
    async_session_maker: async_sessionmaker[AsyncSession],
    group_table: GroupTable,
    users_table: UsersTable,
):
    db_connector = AsyncDatabaseConnector(async_session_maker)
    yield AuthsTable(db_connector, group_table, users_table)


@pytest.fixture(scope="class")
def channel_table(async_session_maker: async_sessionmaker[AsyncSession]):
    db_connector = AsyncDatabaseConnector(async_session_maker)
    yield ChannelTable(db_connector=db_connector)


@pytest.fixture(scope="class")
def chat_table(
    async_session_maker: async_sessionmaker[AsyncSession], tag_table: TagTable
):
    db_connector = AsyncDatabaseConnector(async_session_maker)
    yield ChatTable(db_connector=db_connector, tag_table=tag_table)


@pytest.fixture(scope="class")
def domain_table(async_session_maker: async_sessionmaker[AsyncSession]):
    db_connector = AsyncDatabaseConnector(async_session_maker)
    yield DomainTable(db_connector=db_connector)


@pytest.fixture(scope="class")
def export_logs_table(async_session_maker: async_sessionmaker[AsyncSession]):
    db_connector = AsyncDatabaseConnector(async_session_maker)
    yield ExportLogsTable(db_connector=db_connector)


@pytest.fixture(scope="class")
def feedback_table(async_session_maker: async_sessionmaker[AsyncSession]):
    db_connector = AsyncDatabaseConnector(async_session_maker)
    yield FeedbackTable(db_connector=db_connector)


@pytest.fixture(scope="class")
def files_table(async_session_maker: async_sessionmaker[AsyncSession]):
    db_connector = AsyncDatabaseConnector(async_session_maker)
    yield FilesTable(db_connector=db_connector)


@pytest.fixture(scope="class")
def folder_table(
    async_session_maker: async_sessionmaker[AsyncSession], chat_table: ChatTable
):
    db_connector = AsyncDatabaseConnector(async_session_maker)
    yield FolderTable(db_connector=db_connector, chats=chat_table)


@pytest.fixture(scope="class")
def functions_table(
    async_session_maker: async_sessionmaker[AsyncSession], users_table: UsersTable
):
    db_connector = AsyncDatabaseConnector(async_session_maker)
    yield FunctionsTable(db_connector=db_connector, users_table=users_table)


@pytest.fixture(scope="class")
def group_table(
    async_session_maker: async_sessionmaker[AsyncSession], users_table: UsersTable
):
    db_connector = AsyncDatabaseConnector(async_session_maker)
    yield GroupTable(db_connector=db_connector, users_table=users_table)


@pytest.fixture(scope="class")
def knowledge_table(
    async_session_maker: async_sessionmaker[AsyncSession], users_table: UsersTable
):
    db_connector = AsyncDatabaseConnector(async_session_maker)
    yield KnowledgeTable(db_connector=db_connector, users_table=users_table)


@pytest.fixture(scope="class")
def memories_table(async_session_maker: async_sessionmaker[AsyncSession]):
    db_connector = AsyncDatabaseConnector(async_session_maker)
    yield MemoriesTable(db_connector=db_connector)


@pytest.fixture(scope="class")
def message_table(async_session_maker: async_sessionmaker[AsyncSession]):
    db_connector = AsyncDatabaseConnector(async_session_maker)
    yield MessageTable(db_connector=db_connector)


@pytest.fixture(scope="class")
def message_metrics_table(async_session_maker: async_sessionmaker[AsyncSession]):
    db_connector = AsyncDatabaseConnector(async_session_maker)
    yield MessageMetricsTable(db_connector=db_connector)


@pytest.fixture(scope="class")
def models_table(
    async_session_maker: async_sessionmaker[AsyncSession], users_table: UsersTable
):
    db_connector = AsyncDatabaseConnector(async_session_maker)
    yield ModelsTable(db_connector=db_connector, users_table=users_table)


@pytest.fixture(scope="class")
def prompts_table(
    async_session_maker: async_sessionmaker[AsyncSession], users_table: UsersTable
):
    db_connector = AsyncDatabaseConnector(async_session_maker)
    yield PromptsTable(db_connector=db_connector, users_table=users_table)


@pytest.fixture(scope="class")
def tag_table(async_session_maker: async_sessionmaker[AsyncSession]):
    db_connector = AsyncDatabaseConnector(async_session_maker)
    yield TagTable(db_connector=db_connector)


@pytest.fixture(scope="class")
def tools_table(
    async_session_maker: async_sessionmaker[AsyncSession], users_table: UsersTable
):
    db_connector = AsyncDatabaseConnector(async_session_maker)
    yield ToolsTable(db_connector=db_connector, users_table=users_table)


@pytest.fixture(scope="class")
def users_table(
    async_session_maker: async_sessionmaker[AsyncSession], chat_table: ChatTable
):
    db_connector = AsyncDatabaseConnector(async_session_maker)
    users_table = UsersTable(db_connector=db_connector, chats=chat_table)
    yield users_table
