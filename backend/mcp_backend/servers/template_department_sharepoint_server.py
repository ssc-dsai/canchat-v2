#!/usr/bin/env python3
"""
TEMPLATE: Department SharePoint MCP Server

Adding a new SharePoint department requires ONLY two things:
  1. A copy of this file named {dept}_sharepoint_server.py  (e.g. fin_sharepoint_server.py)
  2. The {DEPT}_SHP_* environment variables set in your .env / secret store

No changes to mcp_manager.py, crew_mcp_integration.py, the MCP router, or
any frontend code are needed — new servers are discovered and registered
automatically at startup.

To create the server file:
  1. Copy this file and rename it to: {dept_lower}_sharepoint_server.py
  2. Replace {DEPT_UPPER} with the department prefix (e.g., FIN, IT, HR)
  3. Add the required environment variables (see below)

Environment variables required for {DEPT_UPPER}:
- Global: SHP_USE_DELEGATED_ACCESS, SHP_OBO_SCOPE (shared across all departments)
- Department-specific:
  - {DEPT_UPPER}_SHP_ID_APP: Azure AD application client ID
  - {DEPT_UPPER}_SHP_ID_APP_SECRET: Azure AD application client secret
  - {DEPT_UPPER}_SHP_TENANT_ID: Azure AD tenant ID
  - {DEPT_UPPER}_SHP_SITE_URL: SharePoint site URL
  - {DEPT_UPPER}_SHP_ORG_NAME: Department name for tool descriptions
  - {DEPT_UPPER}_SHP_DOC_LIBRARY: Default document library path (optional)
  - {DEPT_UPPER}_SHP_DEFAULT_SEARCH_FOLDERS: Default search folders (optional)

Example for Finance Department (DEPT_UPPER = FIN):
  - FIN_SHP_ID_APP=''
  - FIN_SHP_ID_APP_SECRET=''
  - FIN_SHP_TENANT_ID=''
  - FIN_SHP_SITE_URL=''
  - FIN_SHP_ORG_NAME='Finance Department'
  - FIN_SHP_DOC_LIBRARY='Finance'
  - FIN_SHP_DEFAULT_SEARCH_FOLDERS='Finance/Reports,Finance/Policies,Finance/Budgets'
"""

import logging
import sys
from pathlib import Path

# Add local modules to path
sys.path.insert(0, str(Path(__file__).parent))

# Import the multi-department generic server
from generic_sharepoint_server_multi_dept import run_department_server

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - {DEPT_UPPER}-SharePoint - %(levelname)s - %(message)s",
    )
    # Replace {DEPT_UPPER} with the department prefix, e.g. "FIN"
    run_department_server("{DEPT_UPPER}")


# ONBOARDING CHECKLIST FOR NEW DEPARTMENT:
#
# □ 1. Copy this template and rename file to: {dept_lower}_sharepoint_server.py
# □ 2. Replace all {DEPT_UPPER} placeholders with department prefix (e.g., FIN, IT, HR)
# □ 3. Replace all {dept_lower} placeholders with lowercase department prefix
# □ 4. Add department environment variables to .env.example:
#      - {DEPT_UPPER}_SHP_ID_APP=''
#      - {DEPT_UPPER}_SHP_ID_APP_SECRET=''
#      - {DEPT_UPPER}_SHP_TENANT_ID=''
#      - {DEPT_UPPER}_SHP_SITE_URL=''
#      - {DEPT_UPPER}_SHP_ORG_NAME='Department Name'
#      - {DEPT_UPPER}_SHP_DOC_LIBRARY='' (optional)
#      - {DEPT_UPPER}_SHP_DEFAULT_SEARCH_FOLDERS='' (optional)
# □ 5. Add department environment variables to your local .env file
# □ 6. The server is discovered and started automatically — no other code changes needed.
