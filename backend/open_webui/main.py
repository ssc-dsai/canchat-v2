import asyncio
import json
import logging
import mimetypes
import os
import sys
import time

from contextlib import asynccontextmanager
from urllib.parse import urlencode, parse_qs, urlparse
from pydantic import BaseModel
from sqlalchemy import text


from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
    status,
    applications,
)

from fastapi.openapi.docs import get_swagger_ui_html

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import Response, StreamingResponse


from open_webui.socket.main import (
    app as socket_app,
    periodic_usage_pool_cleanup,
)
from open_webui.routers import (
    audio,
    images,
    ollama,
    openai,
    retrieval,
    pipelines,
    tasks,
    auths,
    channels,
    chats,
    folders,
    configs,
    groups,
    files,
    functions,
    memories,
    metrics,
    models,
    knowledge,
    prompts,
    evaluations,
    tools,
    users,
    jira,
    utils,
)
from mcp_backend.routers import mcp, crew_mcp

from open_webui.routers.retrieval import (
    get_embedding_function,
    get_ef,
    get_rf,
)

from open_webui.internal.db import Session

from open_webui.models.functions import Functions
from open_webui.models.models import Models
from open_webui.models.users import Users

from open_webui.config import (
    # Ollama
    DOCS_URL,
    DOCS_URL_FR,
    TRAINING_URL,
    TRAINING_URL_FR,
    ENABLE_OLLAMA_API,
    OLLAMA_BASE_URLS,
    OLLAMA_API_CONFIGS,
    # MCP (Model Context Protocol)
    ENABLE_MCP_API,
    MCP_BASE_URLS,
    MCP_API_CONFIGS,
    # OpenAI
    ENABLE_OPENAI_API,
    OPENAI_API_BASE_URLS,
    OPENAI_API_KEYS,
    OPENAI_API_CONFIGS,
    # Image
    AUTOMATIC1111_API_AUTH,
    AUTOMATIC1111_BASE_URL,
    AUTOMATIC1111_CFG_SCALE,
    AUTOMATIC1111_SAMPLER,
    AUTOMATIC1111_SCHEDULER,
    COMFYUI_BASE_URL,
    COMFYUI_API_KEY,
    COMFYUI_WORKFLOW,
    COMFYUI_WORKFLOW_NODES,
    ENABLE_IMAGE_GENERATION,
    ENABLE_IMAGE_PROMPT_GENERATION,
    IMAGE_GENERATION_ENGINE,
    IMAGE_GENERATION_MODEL,
    IMAGE_SIZE,
    IMAGE_STEPS,
    IMAGES_OPENAI_API_BASE_URL,
    IMAGES_OPENAI_API_KEY,
    # Audio
    AUDIO_STT_ENGINE,
    AUDIO_STT_MODEL,
    AUDIO_STT_OPENAI_API_BASE_URL,
    AUDIO_STT_OPENAI_API_KEY,
    AUDIO_TTS_API_KEY,
    AUDIO_TTS_ENGINE,
    AUDIO_TTS_MODEL,
    AUDIO_TTS_OPENAI_API_BASE_URL,
    AUDIO_TTS_OPENAI_API_KEY,
    AUDIO_TTS_SPLIT_ON,
    AUDIO_TTS_VOICE,
    AUDIO_TTS_AZURE_SPEECH_REGION,
    AUDIO_TTS_AZURE_SPEECH_OUTPUT_FORMAT,
    SURVEY_URL,
    SURVEY_URL_FR,
    WHISPER_MODEL,
    RAG_TEMPLATE,
    RAG_FULL_CONTEXT,
    RAG_EMBEDDING_MODEL,
    RAG_EMBEDDING_MODEL_AUTO_UPDATE,
    RAG_RERANKING_MODEL,
    RAG_RERANKING_MODEL_AUTO_UPDATE,
    RAG_EMBEDDING_ENGINE,
    RAG_EMBEDDING_BATCH_SIZE,
    RAG_RELEVANCE_THRESHOLD,
    RAG_FILE_MAX_COUNT,
    RAG_FILE_MAX_SIZE,
    RAG_OPENAI_API_BASE_URL,
    RAG_OPENAI_API_KEY,
    RAG_OLLAMA_BASE_URL,
    RAG_OLLAMA_API_KEY,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    CONTENT_EXTRACTION_ENGINE,
    TIKA_SERVER_URL,
    RAG_TOP_K,
    RAG_TEXT_SPLITTER,
    TIKTOKEN_ENCODING_NAME,
    PDF_EXTRACT_IMAGES,
    YOUTUBE_LOADER_LANGUAGE,
    YOUTUBE_LOADER_PROXY_URL,
    # Retrieval (Web Search)
    RAG_WEB_SEARCH_ENGINE,
    RAG_WEB_SEARCH_RESULT_COUNT,
    RAG_WEB_SEARCH_CONCURRENT_REQUESTS,
    RAG_WEB_SEARCH_DOMAIN_FILTER_LIST,
    JINA_API_KEY,
    SEARCHAPI_API_KEY,
    SEARCHAPI_ENGINE,
    SEARXNG_QUERY_URL,
    SERPER_API_KEY,
    SERPLY_API_KEY,
    SERPSTACK_API_KEY,
    SERPSTACK_HTTPS,
    TAVILY_API_KEY,
    BING_SEARCH_V7_ENDPOINT,
    BING_SEARCH_V7_SUBSCRIPTION_KEY,
    BRAVE_SEARCH_API_KEY,
    KAGI_SEARCH_API_KEY,
    MOJEEK_SEARCH_API_KEY,
    GOOGLE_PSE_API_KEY,
    GOOGLE_PSE_ENGINE_ID,
    GOOGLE_DRIVE_CLIENT_ID,
    GOOGLE_DRIVE_API_KEY,
    ENABLE_RAG_HYBRID_SEARCH,
    ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION,
    ENABLE_RAG_WEB_SEARCH,
    BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL,
    ENABLE_GOOGLE_DRIVE_INTEGRATION,
    WEBUI_AUTH,
    WEBUI_NAME,
    WEBUI_BANNERS,
    WEBHOOK_URL,
    ADMIN_EMAIL,
    SHOW_ADMIN_DETAILS,
    JWT_EXPIRES_IN,
    ENABLE_SIGNUP,
    ENABLE_LOGIN_FORM,
    ENABLE_API_KEY,
    ENABLE_API_KEY_ENDPOINT_RESTRICTIONS,
    API_KEY_ALLOWED_ENDPOINTS,
    ENABLE_CHANNELS,
    ENABLE_COMMUNITY_SHARING,
    ENABLE_MESSAGE_RATING,
    ENABLE_EVALUATION_ARENA_MODELS,
    USER_PERMISSIONS,
    DEFAULT_USER_ROLE,
    DEFAULT_PROMPT_SUGGESTIONS,
    DEFAULT_MODELS,
    MODEL_ORDER_LIST,
    EVALUATION_ARENA_MODELS,
    # WebUI (OAuth)
    ENABLE_OAUTH_ROLE_MANAGEMENT,
    OAUTH_ROLES_CLAIM,
    OAUTH_EMAIL_CLAIM,
    OAUTH_PICTURE_CLAIM,
    OAUTH_USERNAME_CLAIM,
    OAUTH_ALLOWED_ROLES,
    OAUTH_ADMIN_ROLES,
    # WebUI (LDAP)
    ENABLE_LDAP,
    LDAP_SERVER_LABEL,
    LDAP_SERVER_HOST,
    LDAP_SERVER_PORT,
    LDAP_ATTRIBUTE_FOR_MAIL,
    LDAP_ATTRIBUTE_FOR_USERNAME,
    LDAP_SEARCH_FILTERS,
    LDAP_SEARCH_BASE,
    LDAP_APP_DN,
    LDAP_APP_PASSWORD,
    LDAP_USE_TLS,
    LDAP_CA_CERT_FILE,
    LDAP_CIPHERS,
    # Misc
    ENV,
    CACHE_DIR,
    STATIC_DIR,
    FRONTEND_BUILD_DIR,
    CORS_ALLOW_ORIGIN,
    DEFAULT_LOCALE,
    OAUTH_PROVIDERS,
    WEBUI_URL,
    # Admin
    ENABLE_ADMIN_CHAT_ACCESS,
    ENABLE_ADMIN_EXPORT,
    # Tasks
    TASK_MODEL,
    TASK_MODEL_EXTERNAL,
    ENABLE_TAGS_GENERATION,
    ENABLE_SEARCH_QUERY_GENERATION,
    ENABLE_RETRIEVAL_QUERY_GENERATION,
    ENABLE_AUTOCOMPLETE_GENERATION,
    TITLE_GENERATION_PROMPT_TEMPLATE,
    TAGS_GENERATION_PROMPT_TEMPLATE,
    IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE,
    TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE,
    QUERY_GENERATION_PROMPT_TEMPLATE,
    AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE,
    AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH,
    AppConfig,
    reset_config,
    # Jira
    JIRA_API_URL,
    JIRA_USERNAME,
    JIRA_API_TOKEN,
    JIRA_PROJECT_KEY,
)
from open_webui.env import (
    CHANGELOG,
    GLOBAL_LOG_LEVEL,
    SAFE_MODE,
    SRC_LOG_LEVELS,
    VERSION,
    WEBUI_BUILD_HASH,
    WEBUI_SECRET_KEY,
    WEBUI_SESSION_COOKIE_SAME_SITE,
    WEBUI_SESSION_COOKIE_SECURE,
    WEBUI_AUTH_TRUSTED_EMAIL_HEADER,
    WEBUI_AUTH_TRUSTED_NAME_HEADER,
    ENABLE_WEBSOCKET_SUPPORT,
    BYPASS_MODEL_ACCESS_CONTROL,
    RESET_CONFIG_ON_START,
)


from open_webui.utils.models import (
    get_all_models,
    get_all_base_models,
    check_model_access,
)
from open_webui.utils.chat import (
    generate_chat_completion as chat_completion_handler,
    chat_completed as chat_completed_handler,
    chat_action as chat_action_handler,
)
from open_webui.utils.middleware import process_chat_payload, process_chat_response
from open_webui.utils.access_control import has_access

from open_webui.utils.auth import (
    decode_token,
    get_admin_user,
    get_verified_user,
)
from open_webui.utils.oauth import oauth_manager
from open_webui.utils.security_headers import SecurityHeadersMiddleware

from open_webui.tasks import stop_task, list_tasks  # Import from tasks.py

if SAFE_MODE:
    print("SAFE MODE ENABLED")
    Functions.deactivate_all_functions()

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except (HTTPException, StarletteHTTPException) as ex:
            if ex.status_code == 404:
                # Don't serve index.html for API routes
                if path.startswith(
                    ("api/", "mcp/", "ollama/", "openai/", "ws/", "health", "oauth/")
                ):
                    raise ex
                return await super().get_response("index.html", scope)
            else:
                raise ex


print(
    rf"""
  ___                    __        __   _     _   _ ___
 / _ \ _ __   ___ _ __   \ \      / /__| |__ | | | |_ _|
| | | | '_ \ / _ \ '_ \   \ \ /\ / / _ \ '_ \| | | || |
| |_| | |_) |  __/ | | |   \ V  V /  __/ |_) | |_| || |
 \___/| .__/ \___|_| |_|    \_/\_/ \___|_.__/ \___/|___|
      |_|


v{VERSION} - building the best open-source AI user interface.
{f"Commit: {WEBUI_BUILD_HASH}" if WEBUI_BUILD_HASH != "dev-build" else ""}
https://github.com/open-webui/open-webui
"""
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if RESET_CONFIG_ON_START:
        reset_config()

    # Start Redis server if not already running (only in development)
    redis_process = None
    try:
        import subprocess
        import socket
        from open_webui.env import REDIS_URL, REDIS_AUTO_START
        from urllib.parse import urlparse
        
        # Parse Redis URL to get host and port
        parsed_url = urlparse(REDIS_URL)
        redis_host = parsed_url.hostname or 'localhost'
        redis_port = parsed_url.port or 6379
        
        # Check if Redis is already running
        def is_redis_running():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((redis_host, redis_port))
                sock.close()
                return result == 0
            except:
                return False
        
        if not is_redis_running():
            if REDIS_AUTO_START:
                log.info(f"🚀 Starting Redis server on {redis_host}:{redis_port}")
                redis_process = subprocess.Popen(
                    ['redis-server', '--port', str(redis_port), '--bind', redis_host],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                # Give Redis a moment to start
                await asyncio.sleep(2)
                
                if is_redis_running():
                    log.info("✅ Redis server started successfully")
                    app.state.redis_process = redis_process
                else:
                    log.warning("⚠️ Redis server may not have started properly")
            else:
                log.info("⚠️ Redis auto-start disabled. Expecting external Redis service.")
                log.info(f"💡 Configure REDIS_URL={REDIS_URL} to point to your Redis service")
        else:
            log.info("✅ Redis server already running")
            
    except Exception as e:
        log.warning(f"⚠️ Could not start Redis server: {e}")
        if REDIS_AUTO_START:
            log.info("💡 Please ensure Redis is running manually: redis-server")
        else:
            log.info("💡 Please ensure your Redis service is available")
    # Initialize FastMCP manager
    try:
        from mcp_backend.management.mcp_manager import get_mcp_manager

        app.state.mcp_manager = get_mcp_manager()
        log.info("FastMCP manager initialized")

        # Initialize all MCP servers (built-in and external) if enabled
        if app.state.config.ENABLE_MCP_API:
            await app.state.mcp_manager.initialize_all_servers()
            log.info("All MCP servers initialized")

            # Note: Built-in MCP servers use stdio transport and are managed internally
            # External MCP servers are loaded from database and managed via API

    except Exception as e:
        log.error(f"Failed to initialize FastMCP manager: {e}")

    # Start periodic cleanup task in background (should not affect app lifecycle)
    cleanup_task = asyncio.create_task(periodic_usage_pool_cleanup())

    # Add task completion callback to log if it exits
    def on_cleanup_done(task):
        try:
            if task.cancelled():
                log.info("Periodic usage pool cleanup task was cancelled")
            elif task.exception():
                log.error(
                    f"Periodic usage pool cleanup task failed: {task.exception()}"
                )
            else:
                log.info("Periodic usage pool cleanup task completed")
        except Exception as e:
            log.error(f"Error in cleanup task callback: {e}")

    cleanup_task.add_done_callback(on_cleanup_done)

    try:
        yield
    finally:
        # Cancel the cleanup task if it's still running
        if not cleanup_task.done():
            log.info("Cancelling periodic usage pool cleanup task")
            cleanup_task.cancel()
            try:
                await cleanup_task
            except asyncio.CancelledError:
                log.info("Periodic usage pool cleanup task cancelled successfully")
            except Exception as e:
                log.error(f"Error cancelling cleanup task: {e}")

        # Cleanup MCP manager and all its server processes
        if hasattr(app.state, "mcp_manager") and app.state.mcp_manager:
            try:
                await app.state.mcp_manager.cleanup()
                log.info("MCP manager cleanup completed")
            except Exception as e:
                log.error(f"Error during MCP manager cleanup: {e}")

        # Cleanup Redis server if we started it
        if hasattr(app.state, "redis_process") and app.state.redis_process:
            try:
                log.info("🛑 Shutting down Redis server")
                app.state.redis_process.terminate()
                app.state.redis_process.wait(timeout=5)
                log.info("✅ Redis server shutdown completed")
            except Exception as e:
                log.warning(f"⚠️ Error shutting down Redis server: {e}")
                try:
                    app.state.redis_process.kill()
                except:
                    pass


app = FastAPI(
    docs_url="/docs" if ENV == "dev" else None,
    openapi_url="/openapi.json" if ENV == "dev" else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.state.config = AppConfig()


########################################
#
# OLLAMA
#
########################################


app.state.config.ENABLE_OLLAMA_API = ENABLE_OLLAMA_API
app.state.config.OLLAMA_BASE_URLS = OLLAMA_BASE_URLS
app.state.config.OLLAMA_API_CONFIGS = OLLAMA_API_CONFIGS

app.state.OLLAMA_MODELS = {}

########################################
#
# MCP (Model Context Protocol)
#
########################################

app.state.config.ENABLE_MCP_API = ENABLE_MCP_API
app.state.config.MCP_BASE_URLS = MCP_BASE_URLS
app.state.config.MCP_API_CONFIGS = MCP_API_CONFIGS

app.state.MCP_TOOLS = {}

########################################
#
# OPENAI
#
########################################

app.state.config.ENABLE_OPENAI_API = ENABLE_OPENAI_API
app.state.config.OPENAI_API_BASE_URLS = OPENAI_API_BASE_URLS
app.state.config.OPENAI_API_KEYS = OPENAI_API_KEYS
app.state.config.OPENAI_API_CONFIGS = OPENAI_API_CONFIGS

app.state.OPENAI_MODELS = {}

########################################
#
# WEBUI
#
########################################

app.state.config.WEBUI_URL = WEBUI_URL
app.state.config.ENABLE_SIGNUP = ENABLE_SIGNUP
app.state.config.ENABLE_LOGIN_FORM = ENABLE_LOGIN_FORM

app.state.config.ENABLE_API_KEY = ENABLE_API_KEY
app.state.config.ENABLE_API_KEY_ENDPOINT_RESTRICTIONS = (
    ENABLE_API_KEY_ENDPOINT_RESTRICTIONS
)
app.state.config.API_KEY_ALLOWED_ENDPOINTS = API_KEY_ALLOWED_ENDPOINTS

app.state.config.JWT_EXPIRES_IN = JWT_EXPIRES_IN

app.state.config.SHOW_ADMIN_DETAILS = SHOW_ADMIN_DETAILS
app.state.config.ADMIN_EMAIL = ADMIN_EMAIL


app.state.config.DEFAULT_MODELS = DEFAULT_MODELS
app.state.config.DEFAULT_PROMPT_SUGGESTIONS = DEFAULT_PROMPT_SUGGESTIONS
app.state.config.DEFAULT_USER_ROLE = DEFAULT_USER_ROLE

app.state.config.USER_PERMISSIONS = USER_PERMISSIONS
app.state.config.WEBHOOK_URL = WEBHOOK_URL
app.state.config.BANNERS = WEBUI_BANNERS
app.state.config.MODEL_ORDER_LIST = MODEL_ORDER_LIST


app.state.config.ENABLE_CHANNELS = ENABLE_CHANNELS
app.state.config.ENABLE_COMMUNITY_SHARING = ENABLE_COMMUNITY_SHARING
app.state.config.ENABLE_MESSAGE_RATING = ENABLE_MESSAGE_RATING

app.state.config.ENABLE_EVALUATION_ARENA_MODELS = ENABLE_EVALUATION_ARENA_MODELS
app.state.config.EVALUATION_ARENA_MODELS = EVALUATION_ARENA_MODELS

app.state.config.OAUTH_USERNAME_CLAIM = OAUTH_USERNAME_CLAIM
app.state.config.OAUTH_PICTURE_CLAIM = OAUTH_PICTURE_CLAIM
app.state.config.OAUTH_EMAIL_CLAIM = OAUTH_EMAIL_CLAIM

app.state.config.ENABLE_OAUTH_ROLE_MANAGEMENT = ENABLE_OAUTH_ROLE_MANAGEMENT
app.state.config.OAUTH_ROLES_CLAIM = OAUTH_ROLES_CLAIM
app.state.config.OAUTH_ALLOWED_ROLES = OAUTH_ALLOWED_ROLES
app.state.config.OAUTH_ADMIN_ROLES = OAUTH_ADMIN_ROLES

app.state.config.ENABLE_LDAP = ENABLE_LDAP
app.state.config.LDAP_SERVER_LABEL = LDAP_SERVER_LABEL
app.state.config.LDAP_SERVER_HOST = LDAP_SERVER_HOST
app.state.config.LDAP_SERVER_PORT = LDAP_SERVER_PORT
app.state.config.LDAP_ATTRIBUTE_FOR_MAIL = LDAP_ATTRIBUTE_FOR_MAIL
app.state.config.LDAP_ATTRIBUTE_FOR_USERNAME = LDAP_ATTRIBUTE_FOR_USERNAME
app.state.config.LDAP_APP_DN = LDAP_APP_DN
app.state.config.LDAP_APP_PASSWORD = LDAP_APP_PASSWORD
app.state.config.LDAP_SEARCH_BASE = LDAP_SEARCH_BASE
app.state.config.LDAP_SEARCH_FILTERS = LDAP_SEARCH_FILTERS
app.state.config.LDAP_USE_TLS = LDAP_USE_TLS
app.state.config.LDAP_CA_CERT_FILE = LDAP_CA_CERT_FILE
app.state.config.LDAP_CIPHERS = LDAP_CIPHERS


app.state.AUTH_TRUSTED_EMAIL_HEADER = WEBUI_AUTH_TRUSTED_EMAIL_HEADER
app.state.AUTH_TRUSTED_NAME_HEADER = WEBUI_AUTH_TRUSTED_NAME_HEADER

app.state.TOOLS = {}
app.state.FUNCTIONS = {}


########################################
#
# RETRIEVAL
#
########################################


app.state.config.TOP_K = RAG_TOP_K
app.state.config.RELEVANCE_THRESHOLD = RAG_RELEVANCE_THRESHOLD
app.state.config.FILE_MAX_SIZE = RAG_FILE_MAX_SIZE
app.state.config.FILE_MAX_COUNT = RAG_FILE_MAX_COUNT


app.state.config.RAG_FULL_CONTEXT = RAG_FULL_CONTEXT
app.state.config.ENABLE_RAG_HYBRID_SEARCH = ENABLE_RAG_HYBRID_SEARCH
app.state.config.ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION = (
    ENABLE_RAG_WEB_LOADER_SSL_VERIFICATION
)

app.state.config.CONTENT_EXTRACTION_ENGINE = CONTENT_EXTRACTION_ENGINE
app.state.config.TIKA_SERVER_URL = TIKA_SERVER_URL

app.state.config.TEXT_SPLITTER = RAG_TEXT_SPLITTER
app.state.config.TIKTOKEN_ENCODING_NAME = TIKTOKEN_ENCODING_NAME

app.state.config.CHUNK_SIZE = CHUNK_SIZE
app.state.config.CHUNK_OVERLAP = CHUNK_OVERLAP

app.state.config.RAG_EMBEDDING_ENGINE = RAG_EMBEDDING_ENGINE
app.state.config.RAG_EMBEDDING_MODEL = RAG_EMBEDDING_MODEL
app.state.config.RAG_EMBEDDING_BATCH_SIZE = RAG_EMBEDDING_BATCH_SIZE
app.state.config.RAG_RERANKING_MODEL = RAG_RERANKING_MODEL
app.state.config.RAG_TEMPLATE = RAG_TEMPLATE

app.state.config.RAG_OPENAI_API_BASE_URL = RAG_OPENAI_API_BASE_URL
app.state.config.RAG_OPENAI_API_KEY = RAG_OPENAI_API_KEY

app.state.config.RAG_OLLAMA_BASE_URL = RAG_OLLAMA_BASE_URL
app.state.config.RAG_OLLAMA_API_KEY = RAG_OLLAMA_API_KEY

app.state.config.PDF_EXTRACT_IMAGES = PDF_EXTRACT_IMAGES

app.state.config.YOUTUBE_LOADER_LANGUAGE = YOUTUBE_LOADER_LANGUAGE
app.state.config.YOUTUBE_LOADER_PROXY_URL = YOUTUBE_LOADER_PROXY_URL


app.state.config.ENABLE_RAG_WEB_SEARCH = ENABLE_RAG_WEB_SEARCH
app.state.config.BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL = (
    BYPASS_WEB_SEARCH_EMBEDDING_AND_RETRIEVAL
)
app.state.config.RAG_WEB_SEARCH_ENGINE = RAG_WEB_SEARCH_ENGINE
app.state.config.RAG_WEB_SEARCH_DOMAIN_FILTER_LIST = RAG_WEB_SEARCH_DOMAIN_FILTER_LIST

app.state.config.ENABLE_GOOGLE_DRIVE_INTEGRATION = ENABLE_GOOGLE_DRIVE_INTEGRATION
app.state.config.SEARXNG_QUERY_URL = SEARXNG_QUERY_URL
app.state.config.GOOGLE_PSE_API_KEY = GOOGLE_PSE_API_KEY
app.state.config.GOOGLE_PSE_ENGINE_ID = GOOGLE_PSE_ENGINE_ID
app.state.config.BRAVE_SEARCH_API_KEY = BRAVE_SEARCH_API_KEY
app.state.config.KAGI_SEARCH_API_KEY = KAGI_SEARCH_API_KEY
app.state.config.MOJEEK_SEARCH_API_KEY = MOJEEK_SEARCH_API_KEY
app.state.config.SERPSTACK_API_KEY = SERPSTACK_API_KEY
app.state.config.SERPSTACK_HTTPS = SERPSTACK_HTTPS
app.state.config.SERPER_API_KEY = SERPER_API_KEY
app.state.config.SERPLY_API_KEY = SERPLY_API_KEY
app.state.config.TAVILY_API_KEY = TAVILY_API_KEY
app.state.config.SEARCHAPI_API_KEY = SEARCHAPI_API_KEY
app.state.config.SEARCHAPI_ENGINE = SEARCHAPI_ENGINE
app.state.config.JINA_API_KEY = JINA_API_KEY
app.state.config.BING_SEARCH_V7_ENDPOINT = BING_SEARCH_V7_ENDPOINT
app.state.config.BING_SEARCH_V7_SUBSCRIPTION_KEY = BING_SEARCH_V7_SUBSCRIPTION_KEY

app.state.config.RAG_WEB_SEARCH_RESULT_COUNT = RAG_WEB_SEARCH_RESULT_COUNT
app.state.config.RAG_WEB_SEARCH_CONCURRENT_REQUESTS = RAG_WEB_SEARCH_CONCURRENT_REQUESTS

app.state.EMBEDDING_FUNCTION = None
app.state.ef = None
app.state.rf = None

app.state.YOUTUBE_LOADER_TRANSLATION = None


try:
    app.state.ef = get_ef(
        app.state.config.RAG_EMBEDDING_ENGINE,
        app.state.config.RAG_EMBEDDING_MODEL,
        RAG_EMBEDDING_MODEL_AUTO_UPDATE,
    )

    app.state.rf = get_rf(
        app.state.config.RAG_RERANKING_MODEL,
        RAG_RERANKING_MODEL_AUTO_UPDATE,
    )
except Exception as e:
    log.error(f"Error updating models: {e}")
    pass


app.state.EMBEDDING_FUNCTION = get_embedding_function(
    app.state.config.RAG_EMBEDDING_ENGINE,
    app.state.config.RAG_EMBEDDING_MODEL,
    app.state.ef,
    (
        app.state.config.RAG_OPENAI_API_BASE_URL
        if app.state.config.RAG_EMBEDDING_ENGINE == "openai"
        else app.state.config.RAG_OLLAMA_BASE_URL
    ),
    (
        app.state.config.RAG_OPENAI_API_KEY
        if app.state.config.RAG_EMBEDDING_ENGINE == "openai"
        else app.state.config.RAG_OLLAMA_API_KEY
    ),
    app.state.config.RAG_EMBEDDING_BATCH_SIZE,
)


########################################
#
# IMAGES
#
########################################

app.state.config.IMAGE_GENERATION_ENGINE = IMAGE_GENERATION_ENGINE
app.state.config.ENABLE_IMAGE_GENERATION = ENABLE_IMAGE_GENERATION
app.state.config.ENABLE_IMAGE_PROMPT_GENERATION = ENABLE_IMAGE_PROMPT_GENERATION

app.state.config.IMAGES_OPENAI_API_BASE_URL = IMAGES_OPENAI_API_BASE_URL
app.state.config.IMAGES_OPENAI_API_KEY = IMAGES_OPENAI_API_KEY

app.state.config.IMAGE_GENERATION_MODEL = IMAGE_GENERATION_MODEL

app.state.config.AUTOMATIC1111_BASE_URL = AUTOMATIC1111_BASE_URL
app.state.config.AUTOMATIC1111_API_AUTH = AUTOMATIC1111_API_AUTH
app.state.config.AUTOMATIC1111_CFG_SCALE = AUTOMATIC1111_CFG_SCALE
app.state.config.AUTOMATIC1111_SAMPLER = AUTOMATIC1111_SAMPLER
app.state.config.AUTOMATIC1111_SCHEDULER = AUTOMATIC1111_SCHEDULER
app.state.config.COMFYUI_BASE_URL = COMFYUI_BASE_URL
app.state.config.COMFYUI_API_KEY = COMFYUI_API_KEY
app.state.config.COMFYUI_WORKFLOW = COMFYUI_WORKFLOW
app.state.config.COMFYUI_WORKFLOW_NODES = COMFYUI_WORKFLOW_NODES

app.state.config.IMAGE_SIZE = IMAGE_SIZE
app.state.config.IMAGE_STEPS = IMAGE_STEPS


########################################
#
# AUDIO
#
########################################

app.state.config.STT_OPENAI_API_BASE_URL = AUDIO_STT_OPENAI_API_BASE_URL
app.state.config.STT_OPENAI_API_KEY = AUDIO_STT_OPENAI_API_KEY
app.state.config.STT_ENGINE = AUDIO_STT_ENGINE
app.state.config.STT_MODEL = AUDIO_STT_MODEL

app.state.config.WHISPER_MODEL = WHISPER_MODEL

app.state.config.TTS_OPENAI_API_BASE_URL = AUDIO_TTS_OPENAI_API_BASE_URL
app.state.config.TTS_OPENAI_API_KEY = AUDIO_TTS_OPENAI_API_KEY
app.state.config.TTS_ENGINE = AUDIO_TTS_ENGINE
app.state.config.TTS_MODEL = AUDIO_TTS_MODEL
app.state.config.TTS_VOICE = AUDIO_TTS_VOICE
app.state.config.TTS_API_KEY = AUDIO_TTS_API_KEY
app.state.config.TTS_SPLIT_ON = AUDIO_TTS_SPLIT_ON


app.state.config.TTS_AZURE_SPEECH_REGION = AUDIO_TTS_AZURE_SPEECH_REGION
app.state.config.TTS_AZURE_SPEECH_OUTPUT_FORMAT = AUDIO_TTS_AZURE_SPEECH_OUTPUT_FORMAT


app.state.faster_whisper_model = None
app.state.speech_synthesiser = None
app.state.speech_speaker_embeddings_dataset = None


########################################
#
# TASKS
#
########################################


app.state.config.TASK_MODEL = TASK_MODEL
app.state.config.TASK_MODEL_EXTERNAL = TASK_MODEL_EXTERNAL


app.state.config.ENABLE_SEARCH_QUERY_GENERATION = ENABLE_SEARCH_QUERY_GENERATION
app.state.config.ENABLE_RETRIEVAL_QUERY_GENERATION = ENABLE_RETRIEVAL_QUERY_GENERATION
app.state.config.ENABLE_AUTOCOMPLETE_GENERATION = ENABLE_AUTOCOMPLETE_GENERATION
app.state.config.ENABLE_TAGS_GENERATION = ENABLE_TAGS_GENERATION


app.state.config.TITLE_GENERATION_PROMPT_TEMPLATE = TITLE_GENERATION_PROMPT_TEMPLATE
app.state.config.TAGS_GENERATION_PROMPT_TEMPLATE = TAGS_GENERATION_PROMPT_TEMPLATE
app.state.config.IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE = (
    IMAGE_PROMPT_GENERATION_PROMPT_TEMPLATE
)

app.state.config.TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE = (
    TOOLS_FUNCTION_CALLING_PROMPT_TEMPLATE
)
app.state.config.QUERY_GENERATION_PROMPT_TEMPLATE = QUERY_GENERATION_PROMPT_TEMPLATE
app.state.config.AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE = (
    AUTOCOMPLETE_GENERATION_PROMPT_TEMPLATE
)
app.state.config.AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH = (
    AUTOCOMPLETE_GENERATION_INPUT_MAX_LENGTH
)

########################################
#
# Help
#
########################################
app.state.config.DOCS_URL = DOCS_URL
app.state.config.DOCS_URL_FR = DOCS_URL_FR
app.state.config.SURVEY_URL = SURVEY_URL
app.state.config.SURVEY_URL_FR = SURVEY_URL_FR
app.state.config.TRAINING_URL = TRAINING_URL
app.state.config.TRAINING_URL_FR = TRAINING_URL_FR


########################################
#
# Jira Integration
#
########################################

app.state.config.JIRA_API_URL = JIRA_API_URL
app.state.config.JIRA_USERNAME = JIRA_USERNAME
app.state.config.JIRA_API_TOKEN = JIRA_API_TOKEN
app.state.config.JIRA_PROJECT_KEY = JIRA_PROJECT_KEY


########################################
#
# Jira Integration
#
########################################

app.state.config.JIRA_API_URL = JIRA_API_URL
app.state.config.JIRA_USERNAME = JIRA_USERNAME
app.state.config.JIRA_API_TOKEN = JIRA_API_TOKEN
app.state.config.JIRA_PROJECT_KEY = JIRA_PROJECT_KEY


########################################
#
# WEBUI
#
########################################

app.state.MODELS = {}


class RedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Check if the request is a GET request
        if request.method == "GET":
            path = request.url.path
            query_params = dict(parse_qs(urlparse(str(request.url)).query))

            # Check for the specific watch path and the presence of 'v' parameter
            if path.endswith("/watch") and "v" in query_params:
                video_id = query_params["v"][0]  # Extract the first 'v' parameter
                encoded_video_id = urlencode({"youtube": video_id})
                redirect_url = f"/?{encoded_video_id}"
                return RedirectResponse(url=redirect_url)

        # Proceed with the normal flow of other requests
        response = await call_next(request)
        return response


# Add the middleware to the app
app.add_middleware(RedirectMiddleware)
app.add_middleware(SecurityHeadersMiddleware)


@app.middleware("http")
async def commit_session_after_request(request: Request, call_next):
    try:
        response = await call_next(request)
        # log.debug("Commit session after request")
        Session.commit()

        # Ensure we always return a response
        if response is None:
            # Don't log errors for streaming endpoints or websockets - this is expected
            if "/ws/" in request.url.path or "stream" in request.url.path or "/api/chat/completions" in request.url.path:
                log.debug(f"Streaming/WebSocket endpoint returned None response for {request.url.path} (expected)")
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={"detail": "Streaming response completed"},
                )
            else:
                log.error(
                    f"No response generated in commit_session_after_request for {request.url.path}"
                )
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"detail": "No response generated"},
                )
        return response
    except Exception as e:
        # Only silence "No response returned" errors for streaming endpoints
        if "No response returned" in str(e) and (
            request.url.path.startswith("/api/chat/") or 
            request.url.path.startswith("/api/models") or
            request.url.path.startswith("/ws/")
        ):
            # This is expected for streaming responses, don't log as error
            pass
        else:
            log.error(
                f"Error in commit_session_after_request middleware for {request.url.path}: {e}"
            )
        try:
            Session.rollback()
        except Exception as rollback_error:
            log.error(f"Error during session rollback: {rollback_error}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )


@app.middleware("http")
async def check_url(request: Request, call_next):
    start_time = int(time.time())
    request.state.enable_api_key = app.state.config.ENABLE_API_KEY

    try:
        response = await call_next(request)

        # Ensure we always return a response
        if response is None:
            log.error(
                f"No response generated in check_url middleware for {request.url.path}"
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "No response generated"},
            )

        process_time = int(time.time()) - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
    except Exception as e:
        log.error(f"Error in check_url middleware for {request.url.path}: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )


@app.middleware("http")
async def inspect_websocket(request: Request, call_next):
    # Log all socket.io requests for debugging
    if "/ws/socket.io" in request.url.path:
        log.debug(f"Socket.io request: {request.url.path}?{request.url.query}")
        log.debug(f"Transport: {request.query_params.get('transport')}")
        log.debug(
            f"Headers: Upgrade={request.headers.get('Upgrade')}, Connection={request.headers.get('Connection')}"
        )

    # Only apply WebSocket validation for actual WebSocket upgrade requests
    if (
        "/ws/socket.io" in request.url.path
        and request.query_params.get("transport") == "websocket"
    ):
        upgrade = (request.headers.get("Upgrade") or "").lower()
        connection = (request.headers.get("Connection") or "").lower().split(",")
        # Check that there's the correct headers for an upgrade, else reject the connection
        # This is to work around this upstream issue: https://github.com/miguelgrinberg/python-engineio/issues/367
        if upgrade != "websocket" or "upgrade" not in connection:
            log.warning(
                f"Invalid WebSocket upgrade request: upgrade={upgrade}, connection={connection}"
            )
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Invalid WebSocket upgrade request"},
            )

    try:
        response = await call_next(request)
        # Ensure we always return a response
        if response is None:
            # Don't log errors for streaming endpoints or websockets - this is expected
            if "/ws/" in request.url.path or "stream" in request.url.path or "/api/chat/completions" in request.url.path or "/api/models" in request.url.path:
                log.debug(f"Streaming/WebSocket/Model endpoint returned None response for {request.url.path} (expected)")
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={"detail": "Streaming response completed"},
                )
            else:
                log.error(f"No response generated for {request.url.path}")
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"detail": "No response generated"},
                )
        return response
    except Exception as e:
        # Only silence "No response returned" errors for streaming endpoints
        if "No response returned" in str(e) and (
            request.url.path.startswith("/api/chat/") or 
            request.url.path.startswith("/api/models") or
            request.url.path.startswith("/ws/")
        ):
            # This is expected for streaming responses, don't log as error
            pass
        else:
            log.error(f"Error in inspect_websocket middleware for {request.url.path}: {e}")
        # For WebSocket upgrade requests, return a proper error response
        if (
            "/ws/socket.io" in request.url.path
            and request.query_params.get("transport") == "websocket"
        ):
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "WebSocket connection failed"},
            )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGIN,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.mount("/ws", socket_app)


app.include_router(ollama.router, prefix="/ollama", tags=["ollama"])
app.include_router(openai.router, prefix="/openai", tags=["openai"])
app.include_router(
    mcp.router, prefix="/mcp", tags=["mcp"]
)  # For verification endpoints used by GUI
app.include_router(mcp.router, prefix="/api/v1/mcp", tags=["mcp"])  # For tools API
app.include_router(
    crew_mcp.router, prefix="/api/v1/crew-mcp", tags=["crew-mcp"]
)  # CrewAI MCP integration


app.include_router(pipelines.router, prefix="/api/v1/pipelines", tags=["pipelines"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(images.router, prefix="/api/v1/images", tags=["images"])
app.include_router(audio.router, prefix="/api/v1/audio", tags=["audio"])
app.include_router(retrieval.router, prefix="/api/v1/retrieval", tags=["retrieval"])

app.include_router(configs.router, prefix="/api/v1/configs", tags=["configs"])

app.include_router(auths.router, prefix="/api/v1/auths", tags=["auths"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])


app.include_router(channels.router, prefix="/api/v1/channels", tags=["channels"])
app.include_router(chats.router, prefix="/api/v1/chats", tags=["chats"])

app.include_router(models.router, prefix="/api/v1/models", tags=["models"])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["knowledge"])
app.include_router(prompts.router, prefix="/api/v1/prompts", tags=["prompts"])
app.include_router(tools.router, prefix="/api/v1/tools", tags=["tools"])

app.include_router(memories.router, prefix="/api/v1/memories", tags=["memories"])
app.include_router(folders.router, prefix="/api/v1/folders", tags=["folders"])
app.include_router(groups.router, prefix="/api/v1/groups", tags=["groups"])
app.include_router(files.router, prefix="/api/v1/files", tags=["files"])
app.include_router(functions.router, prefix="/api/v1/functions", tags=["functions"])
app.include_router(
    evaluations.router, prefix="/api/v1/evaluations", tags=["evaluations"]
)
app.include_router(utils.router, prefix="/api/v1/utils", tags=["utils"])
app.include_router(jira.router, prefix="/api/v1/jira", tags=["jira"])
app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["metrics"])
app.include_router(crew_mcp.router, prefix="/api/v1/crew-mcp", tags=["crew-mcp"])


##################################
#
# Chat Endpoints
#
##################################


@app.get("/api/models")
async def get_models(request: Request, user=Depends(get_verified_user)):
    def get_filtered_models(models, user):
        filtered_models = []
        for model in models:
            if model.get("arena"):
                if has_access(
                    user.id,
                    type="read",
                    access_control=model.get("info", {})
                    .get("meta", {})
                    .get("access_control", {}),
                ):
                    filtered_models.append(model)
                continue

            model_info = Models.get_model_by_id(model["id"])
            if model_info:
                if user.id == model_info.user_id or has_access(
                    user.id, type="read", access_control=model_info.access_control
                ):
                    filtered_models.append(model)

        return filtered_models

    models = await get_all_models(request)

    # Filter out filter pipelines
    models = [
        model
        for model in models
        if "pipeline" not in model or model["pipeline"].get("type", None) != "filter"
    ]

    model_order_list = request.app.state.config.MODEL_ORDER_LIST
    if model_order_list:
        model_order_dict = {model_id: i for i, model_id in enumerate(model_order_list)}
        # Sort models by order list priority, with fallback for those not in the list
        models.sort(
            key=lambda x: (model_order_dict.get(x["id"], float("inf")), x["name"])
        )

    # Filter out models that the user does not have access to
    # Apply filtering for both regular users and analysts
    if (
        user.role == "user" or user.role == "analyst" or user.role == "global_analyst"
    ) and not BYPASS_MODEL_ACCESS_CONTROL:
        models = get_filtered_models(models, user)

    log.debug(
        f"/api/models returned filtered models accessible to the user: {json.dumps([model['id'] for model in models])}"
    )
    return {"data": models}


@app.get("/api/models/base")
async def get_base_models(request: Request, user=Depends(get_admin_user)):
    models = await get_all_base_models(request)
    return {"data": models}


@app.post("/api/chat/completions")
async def chat_completion(
    request: Request,
    form_data: dict,
    user=Depends(get_verified_user),
):
    if not request.app.state.MODELS:
        await get_all_models(request)

    tasks = form_data.pop("background_tasks", None)
    try:
        model_id = form_data.get("model", None)
        if model_id not in request.app.state.MODELS:
            raise Exception("Model not found")
        model = request.app.state.MODELS[model_id]

        # Check if user has access to the model
        if not BYPASS_MODEL_ACCESS_CONTROL and user.role == "user":
            try:
                check_model_access(user, model)
            except Exception as e:
                raise e

        metadata = {
            "user_id": user.id,
            "chat_id": form_data.pop("chat_id", None),
            "message_id": form_data.pop("id", None),
            "session_id": form_data.pop("session_id", None),
            "tool_ids": form_data.get("tool_ids", None),
            "files": form_data.get("files", None),
            "features": form_data.get("features", None),
        }
        form_data["metadata"] = metadata

        form_data, events = await process_chat_payload(
            request, form_data, metadata, user, model
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    try:
        response = await chat_completion_handler(request, form_data, user)
        return await process_chat_response(
            request, response, form_data, user, events, metadata, tasks
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# Alias for chat_completion (Legacy)
generate_chat_completions = chat_completion
generate_chat_completion = chat_completion


@app.post("/api/chat/completed")
async def chat_completed(
    request: Request, form_data: dict, user=Depends(get_verified_user)
):
    try:
        return await chat_completed_handler(request, form_data, user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@app.post("/api/chat/actions/{action_id}")
async def chat_action(
    request: Request, action_id: str, form_data: dict, user=Depends(get_verified_user)
):
    try:
        return await chat_action_handler(request, action_id, form_data, user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@app.post("/api/tasks/stop/{task_id}")
async def stop_task_endpoint(task_id: str, user=Depends(get_verified_user)):
    try:
        result = await stop_task(task_id)  # Use the function from tasks.py
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@app.get("/api/tasks")
async def list_tasks_endpoint(user=Depends(get_verified_user)):
    return {"tasks": list_tasks()}  # Use the function from tasks.py


##################################
#
# Config Endpoints
#
##################################


@app.get("/api/config")
async def get_app_config(request: Request):
    user = None
    if "token" in request.cookies:
        token = request.cookies.get("token")
        try:
            data = decode_token(token)
        except Exception as e:
            log.debug(e)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        if data is not None and "id" in data:
            user = Users.get_user_by_id(data["id"])

    onboarding = False
    if user is None:
        user_count = Users.get_num_users()
        onboarding = user_count == 0

    return {
        **({"onboarding": True} if onboarding else {}),
        "status": True,
        "name": WEBUI_NAME,
        "version": VERSION,
        "default_locale": str(DEFAULT_LOCALE),
        "oauth": {
            "providers": {
                name: config.get("name", name)
                for name, config in OAUTH_PROVIDERS.items()
            }
        },
        "features": {
            "auth": WEBUI_AUTH,
            "auth_trusted_header": bool(app.state.AUTH_TRUSTED_EMAIL_HEADER),
            "enable_ldap": app.state.config.ENABLE_LDAP,
            "enable_api_key": app.state.config.ENABLE_API_KEY,
            "enable_signup": app.state.config.ENABLE_SIGNUP,
            "enable_login_form": app.state.config.ENABLE_LOGIN_FORM,
            "enable_websocket": ENABLE_WEBSOCKET_SUPPORT,
            **(
                {
                    "enable_channels": app.state.config.ENABLE_CHANNELS,
                    "enable_web_search": app.state.config.ENABLE_RAG_WEB_SEARCH,
                    "enable_google_drive_integration": app.state.config.ENABLE_GOOGLE_DRIVE_INTEGRATION,
                    "enable_image_generation": app.state.config.ENABLE_IMAGE_GENERATION,
                    "enable_community_sharing": app.state.config.ENABLE_COMMUNITY_SHARING,
                    "enable_message_rating": app.state.config.ENABLE_MESSAGE_RATING,
                    "enable_admin_export": ENABLE_ADMIN_EXPORT,
                    "enable_admin_chat_access": ENABLE_ADMIN_CHAT_ACCESS,
                }
                if user is not None
                else {}
            ),
        },
        "google_drive": {
            "client_id": GOOGLE_DRIVE_CLIENT_ID.value,
            "api_key": GOOGLE_DRIVE_API_KEY.value,
        },
        **(
            {
                "default_models": app.state.config.DEFAULT_MODELS,
                "default_prompt_suggestions": app.state.config.DEFAULT_PROMPT_SUGGESTIONS,
                "docs_url": app.state.config.DOCS_URL,
                "docs_url_fr": app.state.config.DOCS_URL_FR,
                "survey_url": app.state.config.SURVEY_URL,
                "survey_url_fr": app.state.config.SURVEY_URL_FR,
                "training_url": app.state.config.TRAINING_URL,
                "training_url_fr": app.state.config.TRAINING_URL_FR,
                "audio": {
                    "tts": {
                        "engine": app.state.config.TTS_ENGINE,
                        "voice": app.state.config.TTS_VOICE,
                        "split_on": app.state.config.TTS_SPLIT_ON,
                    },
                    "stt": {
                        "engine": app.state.config.STT_ENGINE,
                    },
                },
                "file": {
                    "max_size": app.state.config.FILE_MAX_SIZE,
                    "max_count": app.state.config.FILE_MAX_COUNT,
                },
                "permissions": {**app.state.config.USER_PERMISSIONS},
            }
            if user is not None
            else {}
        ),
    }


class UrlForm(BaseModel):
    url: str


@app.get("/api/webhook")
async def get_webhook_url(user=Depends(get_admin_user)):
    return {
        "url": app.state.config.WEBHOOK_URL,
    }


@app.post("/api/webhook")
async def update_webhook_url(form_data: UrlForm, user=Depends(get_admin_user)):
    app.state.config.WEBHOOK_URL = form_data.url
    app.state.WEBHOOK_URL = app.state.config.WEBHOOK_URL
    return {"url": app.state.config.WEBHOOK_URL}


@app.get("/api/version")
async def get_app_version():
    return {
        "version": VERSION,
    }


@app.get("/api/changelog")
async def get_app_changelog():
    return {key: CHANGELOG[key] for idx, key in enumerate(CHANGELOG) if idx < 5}


############################
# OAuth Login & Callback
############################

# SessionMiddleware is used by authlib for oauth
if len(OAUTH_PROVIDERS) > 0:
    app.add_middleware(
        SessionMiddleware,
        secret_key=WEBUI_SECRET_KEY,
        session_cookie="oui-session",
        same_site=WEBUI_SESSION_COOKIE_SAME_SITE,
        https_only=WEBUI_SESSION_COOKIE_SECURE,
    )


@app.get("/oauth/{provider}/login")
async def oauth_login(provider: str, request: Request):
    return await oauth_manager.handle_login(provider, request)


# OAuth login logic is as follows:
# 1. Attempt to find a user with matching subject ID, tied to the provider
# 2. If OAUTH_MERGE_ACCOUNTS_BY_EMAIL is true, find a user with the email address provided via OAuth
#    - This is considered insecure in general, as OAuth providers do not always verify email addresses
# 3. If there is no user, and ENABLE_OAUTH_SIGNUP is true, create a user
#    - Email addresses are considered unique, so we fail registration if the email address is already taken
@app.get("/oauth/{provider}/callback")
async def oauth_callback(provider: str, request: Request, response: Response):
    return await oauth_manager.handle_callback(provider, request, response)


@app.get("/opensearch.xml")
async def get_opensearch_xml():
    xml_content = rf"""
    <OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/" xmlns:moz="http://www.mozilla.org/2006/browser/search/">
    <ShortName>{WEBUI_NAME}</ShortName>
    <Description>Search {WEBUI_NAME}</Description>
    <InputEncoding>UTF-8</InputEncoding>
    <Image width="16" height="16" type="image/x-icon">{app.state.config.WEBUI_URL}/static/favicon.png</Image>
    <Url type="text/html" method="get" template="{app.state.config.WEBUI_URL}/?q={"{searchTerms}"}"/>
    <moz:SearchForm>{app.state.config.WEBUI_URL}</moz:SearchForm>
    </OpenSearchDescription>
    """
    return Response(content=xml_content, media_type="application/xml")


@app.get("/health")
async def healthcheck():
    return {"status": True}


@app.get("/health/db")
async def healthcheck_with_db():
    try:
        Session.execute(text("SELECT 1;")).all()
        return {"status": True}
    except Exception as e:
        log.error(f"Database health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed",
        )


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/cache", StaticFiles(directory=CACHE_DIR), name="cache")


def swagger_ui_html(*args, **kwargs):
    return get_swagger_ui_html(
        *args,
        **kwargs,
        swagger_js_url="/static/swagger-ui/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui/swagger-ui.css",
        swagger_favicon_url="/static/swagger-ui/favicon.png",
    )


applications.get_swagger_ui_html = swagger_ui_html

if os.path.exists(FRONTEND_BUILD_DIR):
    mimetypes.add_type("text/javascript", ".js")
    app.mount(
        "/",
        SPAStaticFiles(directory=FRONTEND_BUILD_DIR, html=True),
        name="spa-static-files",
    )
else:
    log.warning(
        f"Frontend build directory not found at '{FRONTEND_BUILD_DIR}'. Serving API only."
    )
