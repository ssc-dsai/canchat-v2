from open_webui.internal.db import ASYNC_DATABASE_CONNECTOR
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

"""
Instantiates the database table services to split off definition code from runtime code.
"""
CHANNELS = ChannelTable(ASYNC_DATABASE_CONNECTOR)
DOMAINS = DomainTable(ASYNC_DATABASE_CONNECTOR)
EXPORT_LOGS = ExportLogsTable(ASYNC_DATABASE_CONNECTOR)
FEEDBACKS = FeedbackTable(ASYNC_DATABASE_CONNECTOR)
FILES = FilesTable(ASYNC_DATABASE_CONNECTOR)
MEMORIES = MemoriesTable(ASYNC_DATABASE_CONNECTOR)
MESSAGE_METRICS = MessageMetricsTable(ASYNC_DATABASE_CONNECTOR)
MESSAGES = MessageTable(ASYNC_DATABASE_CONNECTOR)
TAGS = TagTable(ASYNC_DATABASE_CONNECTOR)

# Dependant on TagTable
CHATS = ChatTable(ASYNC_DATABASE_CONNECTOR, TAGS)

# Dependant on ChatTable
FOLDERS = FolderTable(ASYNC_DATABASE_CONNECTOR, CHATS)
USERS = UsersTable(ASYNC_DATABASE_CONNECTOR, CHATS)

# Dependant on UserTable
FUNCTIONS = FunctionsTable(ASYNC_DATABASE_CONNECTOR, USERS)
GROUPS = GroupTable(ASYNC_DATABASE_CONNECTOR, USERS)
KNOWLEDGES = KnowledgeTable(ASYNC_DATABASE_CONNECTOR, USERS)
MODELS = ModelsTable(ASYNC_DATABASE_CONNECTOR, USERS)
PROMPTS = PromptsTable(ASYNC_DATABASE_CONNECTOR, USERS)
TOOLS = ToolsTable(ASYNC_DATABASE_CONNECTOR, USERS)

# Dependant on GroupTable
AUTHS = AuthsTable(ASYNC_DATABASE_CONNECTOR, GROUPS, USERS)
