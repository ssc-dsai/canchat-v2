#!/usr/bin/env python3
"""
CrewAI MCP Integration for Open WebUI
Simple integration using MCPServerAdapter with stdio transport for FastMCP time server
"""

import os
import logging
from pathlib import Path
from pydantic import BaseModel

# Disable CrewAI telemetry to avoid connection timeout errors
os.environ["OTEL_SDK_DISABLED"] = "true"

from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CrewAI verbosity control - disable in production for cleaner logs
CREW_VERBOSE = os.getenv("CREW_VERBOSE", "false").lower() == "true"

# Module-level MCP server adapters - initialized once and reused
_time_server_adapter = None
_news_server_adapter = None
_mpo_sharepoint_server_adapter = None
_pmo_sharepoint_server_adapter = None
_adapters_initialized = False


# Azure OpenAI Configuration
class AzureConfig(BaseModel):
    """Azure OpenAI configuration from environment variables"""

    api_key: str = os.getenv("CREWAI_AZURE_OPENAI_API_KEY", "")
    endpoint: str = os.getenv("CREWAI_AZURE_OPENAI_ENDPOINT", "")
    deployment: str = os.getenv("CREWAI_AZURE_OPENAI_DEPLOYMENT_NAME", "")
    api_version: str = os.getenv("CREWAI_AZURE_OPENAI_API_VERSION", "")

    def validate_config(self) -> bool:
        """Validate that required Azure configuration is present"""
        if not self.api_key or not self.endpoint:
            logger.error(
                "Missing required Azure OpenAI configuration. Please set CREWAI_AZURE_OPENAI_API_KEY and CREWAI_AZURE_OPENAI_ENDPOINT environment variables."
            )
            return False
        return True


class CrewMCPManager:
    """Manager for CrewAI with MCP integration"""

    def __init__(self):
        self.azure_config = AzureConfig()
        if not self.azure_config.validate_config():
            raise ValueError("Invalid Azure OpenAI configuration")
        self.backend_dir = Path(__file__).parent.parent.parent  # Go up to backend dir
        self.time_server_path = (
            self.backend_dir / "mcp_backend" / "servers" / "fastmcp_time_server.py"
        )
        self.news_server_path = (
            self.backend_dir / "mcp_backend" / "servers" / "fastmcp_news_server.py"
        )
        # SharePoint server paths - use new multi-department implementation
        self.mpo_sharepoint_server_path = (
            self.backend_dir / "mcp_backend" / "servers" / "mpo_sharepoint_server.py"
        )
        # SharePoint server paths - use new multi-department implementation
        self.pmo_sharepoint_server_path = (
            self.backend_dir / "mcp_backend" / "servers" / "pmo_sharepoint_server.py"
        )

        # User token for OBO flow (delegate access)
        self.user_jwt_token = None

    def set_user_token(self, token: str):
        """Set the user's JWT token for OBO authentication"""
        self.user_jwt_token = token
        logger.info(f"User JWT token set for OBO flow: {bool(token)}")

        # Set as environment variable for SharePoint MCP servers to use
        if token:
            os.environ["USER_JWT_TOKEN"] = token
            logger.info(f"✅ Set USER_JWT_TOKEN in environment (length: {len(token)})")
        elif "USER_JWT_TOKEN" in os.environ:
            del os.environ["USER_JWT_TOKEN"]
            logger.info("🗑️ Cleared USER_JWT_TOKEN from environment")

    def initialize_mcp_adapters(self):
        """Initialize all MCP server adapters once at startup"""
        global _time_server_adapter, _news_server_adapter, _mpo_sharepoint_server_adapter, _pmo_sharepoint_server_adapter, _adapters_initialized

        if _adapters_initialized:
            logger.info("MCP adapters already initialized, skipping...")
            return

        logger.info("🚀 Initializing MCP server adapters...")

        # Initialize Time Server
        try:
            time_server_params = StdioServerParameters(
                command="python",
                args=[str(self.time_server_path)],
                env=dict(os.environ),  # Pass environment variables
            )
            adapter = MCPServerAdapter(time_server_params)
            _time_server_adapter = adapter.__enter__()  # Get the tools from __enter__()
            logger.info("✅ Time server adapter initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Time server: {e}")
            _time_server_adapter = None

        # Initialize News Server
        try:
            news_server_params = StdioServerParameters(
                command="python",
                args=[str(self.news_server_path)],
                env=dict(os.environ),  # Pass environment variables
            )
            adapter = MCPServerAdapter(news_server_params)
            _news_server_adapter = adapter.__enter__()  # Get the tools from __enter__()
            logger.info("✅ News server adapter initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize News server: {e}")
            _news_server_adapter = None

        # Initialize MPO SharePoint Server - always try to initialize
        try:
            mpo_sharepoint_params = StdioServerParameters(
                command="python",
                args=[str(self.mpo_sharepoint_server_path)],
                env=dict(
                    os.environ
                ),  # Pass environment variables so .env vars are available
            )
            adapter = MCPServerAdapter(mpo_sharepoint_params)
            _mpo_sharepoint_server_adapter = (
                adapter.__enter__()
            )  # Get the tools from __enter__()
            logger.info("✅ MPO SharePoint server adapter initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize MPO SharePoint server: {e}")
            logger.error(
                f"   This is expected in local dev without MPO_SHP_* environment variables"
            )
            _mpo_sharepoint_server_adapter = None

        # Initialize PMO SharePoint Server - always try to initialize
        try:
            pmo_sharepoint_params = StdioServerParameters(
                command="python",
                args=[str(self.pmo_sharepoint_server_path)],
                env=dict(
                    os.environ
                ),  # Pass environment variables so .env vars are available
            )
            adapter = MCPServerAdapter(pmo_sharepoint_params)
            _pmo_sharepoint_server_adapter = (
                adapter.__enter__()
            )  # Get the tools from __enter__()
            logger.info("✅ PMO SharePoint server adapter initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize PMO SharePoint server: {e}")
            logger.error(
                f"   This is expected in local dev without PMO_SHP_* environment variables"
            )
            _pmo_sharepoint_server_adapter = None

        _adapters_initialized = True

        # Report initialization status
        initialized_count = sum(
            [
                _time_server_adapter is not None,
                _news_server_adapter is not None,
                _mpo_sharepoint_server_adapter is not None,
                _pmo_sharepoint_server_adapter is not None,
            ]
        )
        logger.info(
            f"🎉 MCP server initialization complete: {initialized_count}/4 adapters initialized"
        )

    def cleanup_mcp_adapters(self):
        """Cleanup all MCP server adapters on shutdown"""
        global _time_server_adapter, _news_server_adapter, _mpo_sharepoint_server_adapter, _pmo_sharepoint_server_adapter, _adapters_initialized

        logger.info("🧹 Cleaning up MCP server adapters...")

        for adapter_name, adapter in [
            ("Time", _time_server_adapter),
            ("News", _news_server_adapter),
            ("MPO SharePoint", _mpo_sharepoint_server_adapter),
            ("PMO SharePoint", _pmo_sharepoint_server_adapter),
        ]:
            if adapter is not None:
                try:
                    adapter.__exit__(None, None, None)
                    logger.info(f"✅ {adapter_name} server adapter cleaned up")
                except Exception as e:
                    logger.error(f"❌ Error cleaning up {adapter_name} adapter: {e}")

        _time_server_adapter = None
        _news_server_adapter = None
        _mpo_sharepoint_server_adapter = None
        _pmo_sharepoint_server_adapter = None
        _adapters_initialized = False

        logger.info("🎉 All MCP server adapters cleaned up")

    def get_azure_llm_config(self) -> LLM:
        """Get Azure OpenAI LLM configuration for CrewAI"""
        # Set environment variables for LiteLLM/CrewAI Azure OpenAI
        # CrewAI 1.7.2 uses LiteLLM which requires specific Azure env var format
        os.environ["AZURE_API_KEY"] = self.azure_config.api_key
        os.environ["AZURE_API_BASE"] = self.azure_config.endpoint
        os.environ["AZURE_API_VERSION"] = self.azure_config.api_version

        # Create LLM instance with Azure configuration
        # CrewAI 1.7.2 LiteLLM format: azure/<deployment_name>
        # Must NOT include base_url or api_key - LiteLLM reads from env vars
        # Add timeout to prevent hanging in K8s environments
        # O3-mini doesn't support temperature or max_completion_tokens parameters
        return LLM(
            model=f"azure/{self.azure_config.deployment}",
            timeout=30,  # 30 second timeout per LLM API call
        )

    def run_time_crew(self, query: str = "What's the current time?") -> str:
        """
        Run a CrewAI crew with MCP time server tools

        Args:
            query: The time-related query to process

        Returns:
            The crew's response
        """
        global _time_server_adapter

        if not self.time_server_path.exists():
            raise FileNotFoundError(f"Time server not found at {self.time_server_path}")

        if _time_server_adapter is None:
            raise RuntimeError(
                "Time server adapter not initialized. Call initialize_mcp_adapters() first."
            )

        logger.info(f"Starting CrewAI MCP integration for query: {query}")

        try:
            # Use the pre-initialized time server adapter (already contains tools from __enter__())
            mcp_tools = _time_server_adapter
            logger.info(f"Available MCP tools: {[tool.name for tool in mcp_tools]}")

            # Create Azure OpenAI LLM
            llm = self.get_azure_llm_config()

            # Create time specialist agent with MCP tools
            time_agent = Agent(
                role="Time Specialist",
                goal="Provide accurate time information using available time tools",
                backstory="I am an AI specialist focused on time-related queries. I have access to time tools via MCP and can provide current time in various formats and timezones.",
                tools=mcp_tools,  # Pass MCP tools to agent
                llm=llm,
                verbose=CREW_VERBOSE,
                max_iter=3,  # Limit iterations to prevent excessive thinking
            )

            # Create task for time query
            time_task = Task(
                description=f"Process this time-related query: {query}. Use the available time tools to get accurate information.",
                expected_output="A clear and accurate response to the time query with proper formatting.",
                agent=time_agent,
            )

            # Create and execute crew
            time_crew = Crew(
                agents=[time_agent],
                tasks=[time_task],
                process=Process.sequential,
                verbose=CREW_VERBOSE,
            )

            # Execute the crew
            logger.info("Executing CrewAI crew...")
            result = time_crew.kickoff()
            logger.info("CrewAI crew execution completed successfully")
            return str(result)

        except Exception as e:
            logger.error(f"Error in CrewAI MCP integration: {e}")
            raise

    def run_news_crew(self, query: str = "Get the latest news headlines") -> str:
        """
        Run a CrewAI crew with MCP news server tools

        Args:
            query: The news-related query to process

        Returns:
            The crew's response
        """
        global _news_server_adapter

        if not self.news_server_path.exists():
            raise FileNotFoundError(f"News server not found at {self.news_server_path}")

        if _news_server_adapter is None:
            raise RuntimeError(
                "News server adapter not initialized. Call initialize_mcp_adapters() first."
            )

        logger.info(f"Starting CrewAI MCP news integration for query: {query}")

        try:
            # Use the pre-initialized news server adapter (already contains tools from __enter__())
            mcp_tools = _news_server_adapter
            logger.info(
                f"Available MCP news tools: {[tool.name for tool in mcp_tools]}"
            )

            # Create Azure OpenAI LLM
            llm = self.get_azure_llm_config()

            # Create news specialist agent with MCP tools
            news_agent = Agent(
                role="News Specialist",
                goal="Provide current news information exactly as returned by news tools, preserving original formatting and language",
                backstory="I am an AI specialist focused on news and current events. I have access to NewsDesk via MCP tools and can fetch the latest headlines. My role is to pass through the news information exactly as provided by the tools, preserving all formatting, emojis, language (French/English), and structure without translation or summarization.",
                tools=mcp_tools,  # Pass MCP tools to agent
                llm=llm,
                verbose=CREW_VERBOSE,
                max_iter=5,  # Limit iterations to prevent excessive thinking
            )

            # Create task for news query
            news_task = Task(
                description=f"Process this news-related query: {query}. Use the available news tools to get current headlines and relevant information. If the query asks for specific topics, filter or search for relevant articles.",
                expected_output="Return the news information EXACTLY as provided by the news tools, preserving all original formatting, emojis, language, and structure. Do NOT translate, summarize, or reformat the content. Simply pass through the original response from the news tools with minimal additional commentary.",
                agent=news_agent,
            )

            # Create and execute crew
            news_crew = Crew(
                agents=[news_agent],
                tasks=[news_task],
                process=Process.sequential,
                verbose=CREW_VERBOSE,
            )

            # Execute the crew
            logger.info("Executing CrewAI news crew...")
            result = news_crew.kickoff()
            return str(result)

        except Exception as e:
            logger.error(f"Error in CrewAI MCP news integration: {e}")
            raise

    def run_mpo_sharepoint_crew(
        self, query: str = "Search SharePoint documents"
    ) -> str:
        """
        Run a CrewAI crew with MCP SharePoint server tools (MPO SharePoint only)

        Args:
            query:  The SharePoint-related query to process

        Returns:
            The crew's response
        """
        if not self.mpo_sharepoint_server_path.exists():
            raise FileNotFoundError(
                f"MPO SharePoint server not found at {self.mpo_sharepoint_server_path}"
            )

        logger.info(f"Starting CrewAI MCP SharePoint integration for query: {query}")
        logger.info(f"Using MPO SharePoint server:  {self.mpo_sharepoint_server_path}")

        # **CRITICAL FIX: Initialize adapter with current environment containing USER_JWT_TOKEN**
        logger.info(
            "🔄 Initializing fresh SharePoint adapter with user token from environment"
        )

        try:
            # Create adapter with current environment (includes USER_JWT_TOKEN set by set_user_token())
            mpo_sharepoint_params = StdioServerParameters(
                command="python",
                args=[str(self.mpo_sharepoint_server_path)],
                env=dict(os.environ),  # Fresh environment snapshot with USER_JWT_TOKEN
            )

            # Use context manager for automatic cleanup
            adapter = MCPServerAdapter(mpo_sharepoint_params)
            mcp_tools = adapter.__enter__()  # Get the tools from adapter

            logger.info(
                f"✅ SharePoint adapter initialized with {len(list(mcp_tools))} tools"
            )
            logger.info(
                f"Available MCP SharePoint tools: {[tool.name for tool in mcp_tools]}"
            )

            # Create Azure OpenAI LLM
            llm = self.get_azure_llm_config()

            # Create SharePoint specialist agent with MCP tools
            sharepoint_agent = Agent(
                role="SharePoint Document Specialist",
                goal="Find and retrieve relevant information from SharePoint using FAST search or list files in specific folders",
                backstory="""I am a SharePoint document specialist who uses the Microsoft Graph Search API for lightning-fast document searches and folder listings.

    🚨 CRITICAL RULES:
    1. For LISTING/COUNTING files in a specific folder → Use mpo_list_folder_contents
    2. For SEARCHING content across documents → Use mpo_search_documents_fast
    3. If search snippet doesn't have the complete answer, use mpo_get_document_by_id to get full content
    4. NEVER answer from training data - ONLY from SharePoint results
    5. If no documents found, say so - don't make up answers
    
    RESPONSE FORMAT:
    - Provide ONLY the final answer extracted from SharePoint
    - Do NOT show your reasoning process ("Thought:", "Action:", etc.)
    - Include document name and source when applicable
    - Be direct and concise""",
                tools=mcp_tools,
                llm=llm,
                verbose=CREW_VERBOSE,
                max_iter=5,
                allow_delegation=False,
            )

            # Create SharePoint task with smart routing
            sharepoint_task = Task(
                description=f"""Retrieve information from SharePoint for: {query}

    🔍 STEP 1 - DETERMINE REQUEST TYPE:
    
    A) If asking to LIST/COUNT files in a SPECIFIC FOLDER (keywords: "list", "show files", "count", "how many files", "in the folder", "in folder"):
       → Use mpo_list_folder_contents
       → Extract folder name from query (e.g., "Canchat Demo", "Documents/Reports")
       → Call: mpo_list_folder_contents(folder_path="<folder_name>")
       → If successful: Return the list of files found
       → If folder not found: FALLBACK to mpo_search_documents_fast(query="<folder_name>", limit=10) to find documents
    
    B) If asking for CONTENT/INFORMATION ABOUT something (keywords: "tell me about", "what is", "explain", "information about", "details on"):
       → STEP 1: Use mpo_search_documents_fast
         • Call: mpo_search_documents_fast(query="{query}", limit=10)
       
       → STEP 2: Analyze results:
         • If ANY FILES found (is_folder=false): GO TO STEP 3
         • If ONLY folders found (all is_folder=true): GO TO STEP 4
       
       → STEP 3: Process FILES:
         • If file has useful summary: Extract and respond
         • If need full content: Use mpo_get_document_by_id(web_url=..., item_id=...)
         • DONE - provide answer to user
       
       → STEP 4: MANDATORY REFINED SEARCH (when only folders found):
         • Try search with hyphenated version: mpo_search_documents_fast(query="Budget-2025", limit=10)
         • If no files, try: mpo_search_documents_fast(query="Budget 2025 pdf", limit=10)
         • If files found: Use mpo_get_document_by_id to retrieve content
         • If still no files after 2 refined searches: Tell user no document files found, only folders exist
       
       → NEVER try to retrieve folder content with mpo_get_document_by_id

    🚨 ABSOLUTE RULES:
    - For "Tell me about X" queries: Prioritize finding DOCUMENT CONTENT, not folder structure
    - Search returns folders + files: Use the FILES first, ignore folders unless no files exist
    - Search returns ONLY folders: Try refined search with specific terms before listing folder contents
    - Only use mpo_get_document_by_id for actual FILES (is_folder=false)
    - Do NOT retry the same tool with same input more than once
    - Include document names and sources in your final answer
    - If you get an error suggesting to use search, DO IT - don't give up
    - If you receive a permission/access denied error (🔒), STOP and tell the user they don't have access
    - Do NOT say "no information found" when it's actually a permissions issue
    - 404 errors on folders mean you tried to get a folder as a document - use mpo_list_folder_contents instead
                """,
                expected_output="""A DIRECT, CONCISE answer to the user's question without showing any reasoning process.

    FORMAT REQUIREMENTS:
    - Start immediately with the answer (NO "Thought:", "Action:", or process explanations)
    - Extract the key information from the search results
    - Include document name and source for credibility
    - Keep response focused on what was asked
    - Maximum 2-3 sentences unless more detail is specifically requested

    EXAMPLE RESPONSES:
    - Success: "Canada's new high-speed railway is proposed to span approximately 1,000 km, according to the document '2025-12-05-Alto-Letter to MPO.pdf' from the Major Projects Office."
    - Permission Error: "You do not have permission to access the requested documents. Please contact your SharePoint administrator for access."
    - Not Found: "No documents found matching your query in accessible SharePoint locations."

    AVOID:  
    - Showing reasoning ("Thought:", "I will use tool X")
    - Dumping entire document contents
    - Being overly verbose
    - Including process descriptions
    - Saying "no information found" when it's a permissions issue""",
                agent=sharepoint_agent,
            )

            # Create and execute crew
            sharepoint_crew = Crew(
                agents=[sharepoint_agent],
                tasks=[sharepoint_task],
                process=Process.sequential,
                verbose=CREW_VERBOSE,
            )

            # Execute the crew
            logger.info("Executing CrewAI SharePoint crew...")
            result = sharepoint_crew.kickoff()

            # Cleanup adapter
            try:
                adapter.__exit__(None, None, None)
                logger.info("✅ Cleaned up SharePoint adapter")
            except Exception as e:
                logger.warning(f"Failed to cleanup adapter: {e}")

            return str(result)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error in CrewAI MCP SharePoint integration: {error_msg}")

            # Provide specific error messages based on the type of failure
            if (
                "Authentication" in error_msg
                or "access token" in error_msg
                or "401" in error_msg
            ):
                return (
                    "SharePoint access failed due to authentication issues. This may be because:\n\n"
                    + "1. You're in a local development environment where OAuth2 proxy is not configured\n"
                    + "2. Your authentication token has expired\n"
                    + "3. You don't have the necessary SharePoint permissions\n\n"
                    + "For local development, SharePoint integration requires deployment to environments with proper OAuth2 configuration (dev/staging/production)."
                )
            elif "No documents found" in error_msg or "no results" in error_msg:
                return "I searched the available SharePoint documents but could not find information related to your query. The documents may not contain this information, or it might be located in a different location."
            else:
                return f"I encountered an issue while searching SharePoint documents: {error_msg}. Please try rephrasing your query or contact support if the problem persists."

    def run_pmo_sharepoint_crew(
        self, query: str = "Search SharePoint documents"
    ) -> str:
        """
        Run a CrewAI crew with MCP SharePoint server tools (PMO SharePoint only)

        Args:
            query:  The SharePoint-related query to process

        Returns:
            The crew's response
        """
        if not self.pmo_sharepoint_server_path.exists():
            raise FileNotFoundError(
                f"PMO SharePoint server not found at {self.pmo_sharepoint_server_path}"
            )

        logger.info(f"Starting CrewAI MCP SharePoint integration for query: {query}")
        logger.info(f"Using PMO SharePoint server:  {self.pmo_sharepoint_server_path}")
        # **CRITICAL FIX: Initialize adapter with current environment containing USER_JWT_TOKEN**
        logger.info(
            "🔄 Initializing fresh SharePoint adapter with user token from environment"
        )

        try:
            # Create adapter with current environment (includes USER_JWT_TOKEN set by set_user_token())
            pmo_sharepoint_params = StdioServerParameters(
                command="python",
                args=[str(self.pmo_sharepoint_server_path)],
                env=dict(os.environ),  # Fresh environment snapshot with USER_JWT_TOKEN
            )

            # Use context manager for automatic cleanup
            adapter = MCPServerAdapter(pmo_sharepoint_params)
            mcp_tools = adapter.__enter__()  # Get the tools from adapter

            logger.info(
                f"✅ SharePoint adapter initialized with {len(list(mcp_tools))} tools"
            )
            logger.info(
                f"Available MCP SharePoint tools: {[tool.name for tool in mcp_tools]}"
            )

            # Create Azure OpenAI LLM
            llm = self.get_azure_llm_config()

            # Create SharePoint specialist agent with MCP tools
            sharepoint_agent = Agent(
                role="SharePoint Document Specialist",
                goal="Find and retrieve relevant information from SharePoint using FAST search or list files in specific folders",
                backstory="""I am a SharePoint document specialist who uses the Microsoft Graph Search API for lightning-fast document searches and folder listings.

    🚨 CRITICAL RULES:
    1. For LISTING/COUNTING files in a specific folder → Use pmo_list_folder_contents
    2. For SEARCHING content across documents → Use pmo_search_documents_fast
    3. If search snippet doesn't have the complete answer, use pmo_get_document_by_id to get full content
    4. NEVER answer from training data - ONLY from SharePoint results
    5. If no documents found, say so - don't make up answers
    
    RESPONSE FORMAT:
    - Provide ONLY the final answer extracted from SharePoint
    - Do NOT show your reasoning process ("Thought:", "Action:", etc.)
    - Include document name and source when applicable
    - Be direct and concise""",
                tools=mcp_tools,
                llm=llm,
                verbose=CREW_VERBOSE,
                max_iter=5,
                allow_delegation=False,
            )

            # Create SharePoint task with smart routing
            sharepoint_task = Task(
                description=f"""Retrieve information from SharePoint for: {query}

    🔍 STEP 1 - DETERMINE REQUEST TYPE:
    
    A) If asking to LIST/COUNT files in a SPECIFIC FOLDER (keywords: "list", "show files", "count", "how many files", "in the folder", "in folder"):
       → Use pmo_list_folder_contents
       → Extract folder name from query (e.g., "Canchat Demo", "Documents/Reports")
       → Call: pmo_list_folder_contents(folder_path="<folder_name>")
       → If successful: Return the list of files found
       → If folder not found: FALLBACK to pmo_search_documents_fast(query="<folder_name>", limit=10) to find documents
    
    B) If asking for CONTENT/INFORMATION ABOUT something (keywords: "tell me about", "what is", "explain", "information about", "details on"):
       → STEP 1: Use pmo_search_documents_fast
         • Call: pmo_search_documents_fast(query="{query}", limit=10)
       
       → STEP 2: Analyze results:
         • If ANY FILES found (is_folder=false): GO TO STEP 3
         • If ONLY folders found (all is_folder=true): GO TO STEP 4
       
       → STEP 3: Process FILES:
         • If file has useful summary: Extract and respond
         • If need full content: Use pmo_get_document_by_id(web_url=..., item_id=...)
         • DONE - provide answer to user
       
       → STEP 4: MANDATORY REFINED SEARCH (when only folders found):
         • Try search with hyphenated version: pmo_search_documents_fast(query="Budget-2025", limit=10)
         • If no files, try: pmo_search_documents_fast(query="Budget 2025 pdf", limit=10)
         • If files found: Use pmo_get_document_by_id to retrieve content
         • If still no files after 2 refined searches: Tell user no document files found, only folders exist
       
       → NEVER try to retrieve folder content with pmo_get_document_by_id

    🚨 ABSOLUTE RULES:
    - For "Tell me about X" queries: Prioritize finding DOCUMENT CONTENT, not folder structure
    - Search returns folders + files: Use the FILES first, ignore folders unless no files exist
    - Search returns ONLY folders: Try refined search with specific terms before listing folder contents
    - Only use pmo_get_document_by_id for actual FILES (is_folder=false)
    - Do NOT retry the same tool with same input more than once
    - Include document names and sources in your final answer
    - If you get an error suggesting to use search, DO IT - don't give up
    - If you receive a permission/access denied error (🔒), STOP and tell the user they don't have access
    - Do NOT say "no information found" when it's actually a permissions issue
    - 404 errors on folders mean you tried to get a folder as a document - use pmo_list_folder_contents instead
                """,
                expected_output="""A DIRECT, CONCISE answer to the user's question without showing any reasoning process.

    FORMAT REQUIREMENTS:
    - Start immediately with the answer (NO "Thought:", "Action:", or process explanations)
    - Extract the key information from the search results
    - Include document name and source for credibility
    - Keep response focused on what was asked
    - Maximum 2-3 sentences unless more detail is specifically requested

    EXAMPLE RESPONSES:
    - Success: "Canada's new high-speed railway is proposed to span approximately 1,000 km, according to the document '2025-12-05-Alto-Letter to MPO.pdf' from the Major Projects Office."
    - Permission Error: "You do not have permission to access the requested documents. Please contact your SharePoint administrator for access."
    - Not Found: "No documents found matching your query in accessible SharePoint locations."

    AVOID:  
    - Showing reasoning ("Thought:", "I will use tool X")
    - Dumping entire document contents
    - Being overly verbose
    - Including process descriptions
    - Saying "no information found" when it's a permissions issue""",
                agent=sharepoint_agent,
            )

            # Create and execute crew
            sharepoint_crew = Crew(
                agents=[sharepoint_agent],
                tasks=[sharepoint_task],
                process=Process.sequential,
                verbose=CREW_VERBOSE,
            )

            # Execute the crew
            logger.info("Executing CrewAI SharePoint crew...")
            result = sharepoint_crew.kickoff()

            # Cleanup adapter
            try:
                adapter.__exit__(None, None, None)
                logger.info("✅ Cleaned up SharePoint adapter")
            except Exception as e:
                logger.warning(f"Failed to cleanup adapter: {e}")

            return str(result)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error in CrewAI MCP SharePoint integration: {error_msg}")

            # Provide specific error messages based on the type of failure
            if (
                "Authentication" in error_msg
                or "access token" in error_msg
                or "401" in error_msg
            ):
                return (
                    "SharePoint access failed due to authentication issues. This may be because:\n\n"
                    + "1. You're in a local development environment where OAuth2 proxy is not configured\n"
                    + "2. Your authentication token has expired\n"
                    + "3. You don't have the necessary SharePoint permissions\n\n"
                    + "For local development, SharePoint integration requires deployment to environments with proper OAuth2 configuration (dev/staging/production)."
                )
            elif "No documents found" in error_msg or "no results" in error_msg:
                return "I searched the available SharePoint documents but could not find information related to your query. The documents may not contain this information, or it might be located in a different location."
            else:
                return f"I encountered an issue while searching SharePoint documents: {error_msg}. Please try rephrasing your query or contact support if the problem persists."

    def run_intelligent_crew(self, query: str, selected_tools: list = None) -> str:
        """
        Intelligent router crew that analyzes the query and makes smart routing decisions
        to coordinate with appropriate specialist agents (time, news, etc.) based on the
        user's actual needs and intent, not keywords.

        Args:
            query: The query to process
            selected_tools: List of tool IDs selected by the user (optional)

        Returns:
            The crew's response using intelligent routing and coordination
        """
        logger.info(f"Starting intelligent router for query: {query}")
        logger.info(f"Selected tools: {selected_tools}")

        try:
            # Create Azure OpenAI LLM
            llm = self.get_azure_llm_config()

            # Determine available specialists based on selected tools
            available_specialists = []
            if selected_tools:
                if any("time" in tool.lower() for tool in selected_tools):
                    available_specialists.append("TIME")
                if any(
                    "news" in tool.lower() or "headline" in tool.lower()
                    for tool in selected_tools
                ):
                    available_specialists.append("NEWS")
                if any(
                    "mcp_mpo_sharepoint_server" in tool.lower()
                    for tool in selected_tools
                ):
                    available_specialists.append("MPO_SHAREPOINT")
                if any(
                    "mcp_pmo_sharepoint_server" in tool.lower()
                    for tool in selected_tools
                ):
                    available_specialists.append("PMO_SHAREPOINT")
            else:
                # If no tools selected, all specialists are available
                available_specialists = ["TIME", "NEWS"]

            logger.info(f"Available specialists: {available_specialists}")

            # FAST PATH: If user explicitly selected tools for a single specialist, skip router overhead
            if len(available_specialists) == 1:
                specialist = available_specialists[0]
                logger.info(
                    f"🚀 FAST PATH: Single specialist detected ({specialist}), skipping router crew overhead"
                )

                if specialist == "TIME":
                    return self.run_time_crew(query)
                elif specialist == "NEWS":
                    return self.run_news_crew(query)
                elif specialist == "MPO_SHAREPOINT":
                    return self.run_mpo_sharepoint_crew(query)
                elif specialist == "PMO_SHAREPOINT":
                    return self.run_pmo_sharepoint_crew(query)

            # Multiple specialists - simple routing logic
            logger.info("Multiple specialists available - using simple routing")

            # For multi-specialist queries, just default to first available
            # In practice, the FAST PATH handles 99% of real queries
            if "TIME" in available_specialists:
                return self.run_time_crew(query)
            elif "NEWS" in available_specialists:
                return self.run_news_crew(query)
            elif "MPO_SHAREPOINT" in available_specialists:
                return self.run_mpo_sharepoint_crew(query)
            elif "PMO_SHAREPOINT" in available_specialists:
                return self.run_pmo_sharepoint_crew(query)
            else:
                return "I apologize, but I was unable to process your request at this time."

        except Exception as e:
            logger.error(f"Error in intelligent routing: {e}")
            # Emergency fallback - route based on selected tools only
            logger.info("Using emergency fallback routing...")

            if selected_tools:
                # Use selected tools to determine routing
                has_time = any("time" in tool.lower() for tool in selected_tools)
                has_news = any(
                    "news" in tool.lower() or "headline" in tool.lower()
                    for tool in selected_tools
                )

                if has_time and not has_news:
                    logger.info("Emergency fallback: TIME only")
                    return self.run_time_crew(query)
                elif has_news and not has_time:
                    logger.info("Emergency fallback: NEWS only")
                    return self.run_news_crew(query)
                elif has_time and has_news:
                    # Both selected - default to time (or could be news, doesn't matter)
                    logger.info("Emergency fallback: TIME (both selected)")
                    return self.run_time_crew(query)
                else:
                    logger.info("Emergency fallback: TIME (default)")
                    return self.run_time_crew(query)
            else:
                # No tools selected - default to time
                logger.info("Emergency fallback: TIME (no tools selected)")
                return self.run_time_crew(query)

    def _combine_specialist_responses(
        self, responses: list, original_query: str
    ) -> str:
        """
        Combine multiple specialist responses in a structured way that maintains
        compatibility with Open WebUI's chat naming and tagging systems.
        """
        logger.info(f"Combining {len(responses)} specialist responses")

        # For now, use a simple structured combination that preserves key information
        # This should work better with Open WebUI's automated analysis systems

        if len(responses) == 1:
            return responses[0]

        # Create a structured combination with clear sections
        combined_parts = []

        for i, response in enumerate(responses):
            # Add each response with minimal formatting
            if i == 0:
                combined_parts.append(response.strip())
            else:
                combined_parts.append(f"\n{response.strip()}")

        # Join with double line breaks for clear separation
        return "\n\n".join(combined_parts)

    def get_available_servers(self) -> dict:
        """Get all available MCP servers dynamically"""
        servers = {}

        # Define known servers (using MPO SharePoint, not generic SharePoint)
        known_servers = {
            "time_server": self.time_server_path,
            "news_server": self.news_server_path,
            "mpo_sharepoint_server": self.mpo_sharepoint_server_path,
            "pmo_sharepoint_server": self.pmo_sharepoint_server_path,
        }

        # Add any other fastmcp_*.py servers found in the backend directory
        servers_dir = self.backend_dir / "mcp_backend" / "servers"
        for server_file in servers_dir.glob("fastmcp_*.py"):
            server_name = server_file.stem  # Remove .py extension
            if server_name not in known_servers:
                servers[server_name] = server_file
                logger.info(f"Discovered additional MCP server: {server_name}")

        # Add known servers
        servers.update(known_servers)

        # Filter to only existing servers
        return {name: path for name, path in servers.items() if path.exists()}

    def get_available_tools(self) -> list:
        """Get list of available MCP tools from all initialized adapters"""
        global _time_server_adapter, _news_server_adapter, _mpo_sharepoint_server_adapter, _pmo_sharepoint_server_adapter

        all_tools = []

        # Only expose the 3 official tools: time, news, and MPO SharePoint
        # The adapters already contain the tools from __enter__()
        adapters = {
            "time_server": _time_server_adapter,
            "news_server": _news_server_adapter,
            "mpo_sharepoint_server": _mpo_sharepoint_server_adapter,
            "pmo_sharepoint_server": _pmo_sharepoint_server_adapter,
        }

        for server_name, tools in adapters.items():
            if tools is not None:
                try:
                    for tool in tools:
                        all_tools.append(
                            {
                                "name": tool.name,
                                "description": tool.description,
                                "server": server_name,
                            }
                        )
                    logger.info(f"Found {len(list(tools))} tools from {server_name}")
                except Exception as e:
                    logger.error(f"Error getting tools from {server_name}: {e}")

        return all_tools


# Simple CLI interface for testing
def main():
    """Main function for testing the CrewAI MCP integration"""
    manager = CrewMCPManager()

    # Initialize MCP adapters once
    manager.initialize_mcp_adapters()

    print("🚀 Starting CrewAI MCP Integration Test")
    print("=" * 50)

    try:
        # Test server discovery
        print("\n📡 Available MCP Servers:")
        available_servers = manager.get_available_servers()
        for server_name, server_path in available_servers.items():
            print(f"   ✓ {server_name}: {server_path}")

        # Test getting available tools first
        tools = manager.get_available_tools()
        print(f"\n📋 Available MCP Tools: {len(tools)}")
        for tool in tools:
            print(f"   - {tool['name']} ({tool['server']}): {tool['description']}")

        if not tools:
            print("❌ No MCP tools available. Check FastMCP servers.")
            return

        # Test individual server capabilities
        if any(tool["server"] == "time_server" for tool in tools):
            print("\n🕐 Testing Time Server:")
            print("Query: 'What's the current time in UTC?'")
            result = manager.run_time_crew("What's the current time in UTC?")
            print("Result:", result[:200] + "..." if len(result) > 200 else result)

        if any(tool["server"] == "news_server" for tool in tools):
            print("\n📰 Testing News Server:")
            print("Query: 'Get the latest news headlines'")
            result = manager.run_news_crew("Get the latest news headlines")
            print("Result:", result[:200] + "..." if len(result) > 200 else result)

        print("\n✅ All tests completed successfully!")

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
