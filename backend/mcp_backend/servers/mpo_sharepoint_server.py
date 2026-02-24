#!/usr/bin/env python3
"""
MPO (Major Projects Office) SharePoint MCP Server

Single-department MCP server for MPO SharePoint.
Uses the generic SharePoint MCP server framework.

Required environment variables:
- Global:
  - SHP_USE_DELEGATED_ACCESS
  - SHP_OBO_SCOPE

- MPO-specific:
  - MPO_SHP_ID_APP
  - MPO_SHP_ID_APP_SECRET
  - MPO_SHP_TENANT_ID
  - MPO_SHP_SITE_URL
  - MPO_SHP_ORG_NAME
  - MPO_SHP_DOC_LIBRARY
  - MPO_SHP_DEFAULT_SEARCH_FOLDERS
"""

import asyncio
import logging
import sys
from pathlib import Path

# Ensure local imports work
sys.path.insert(0, str(Path(__file__).parent))

from generic_sharepoint_server_multi_dept import run_department_server

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - MPO-SharePoint - %(levelname)s - %(message)s",
    )

    run_department_server("MPO")
