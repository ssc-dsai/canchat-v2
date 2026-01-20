#!/usr/bin/env python3
"""
PMO (Prime Minister's Office) SharePoint MCP Server

This server provides SharePoint document search and retrieval capabilities
specifically for the Prime Minister's Office (PMO) using the multi-department
generic SharePoint server framework.

Environment variables required:
- Global: SHP_USE_DELEGATED_ACCESS, SHP_OBO_SCOPE
- PMO-specific: PMO_SHP_ID_APP, PMO_SHP_ID_APP_SECRET, PMO_SHP_TENANT_ID,
  PMO_SHP_SITE_URL, PMO_SHP_ORG_NAME, PMO_SHP_DOC_LIBRARY, PMO_SHP_DEFAULT_SEARCH_FOLDERS
"""

import logging
import sys
from pathlib import Path

# Add local modules to path
sys.path.insert(0, str(Path(__file__).parent))

# Import the multi-department generic server components
from generic_sharepoint_server_multi_dept import initialize_department_server, mcp

def setup_pmo_server():
    """Initialize the PMO SharePoint server configuration"""
    try:
        logging.info("Setting up PMO SharePoint MCP Server")

        # Initialize server for PMO department
        success = initialize_department_server("PMO")
        if not success:
            logging.error(
                "Failed to initialize PMO SharePoint server - will continue with no tools"
            )
            logging.warning("Server will run but tools will not be available")
            # Don't return False - let the server run even if init fails
            # This allows the process to stay alive for debugging
            return True  # Changed from False

        logging.info("PMO SharePoint MCP Server configuration complete")
        return True

    except Exception as e:
        logging.error(f"Error setting up PMO SharePoint server: {e}", exc_info=True)
        logging.warning("Server will run but tools will not be available")
        # Don't fail - let the server run for debugging
        return True  # Changed from False


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - PMO-SharePoint - %(levelname)s - %(message)s",
    )

    # Setup the server configuration
    if setup_pmo_server():
        logging.info("Starting PMO SharePoint MCP Server with stdio transport")
        # Run the server directly like other FastMCP servers
        mcp.run()
    else:
        logging.error("Failed to setup PMO SharePoint server")
        sys.exit(1)
