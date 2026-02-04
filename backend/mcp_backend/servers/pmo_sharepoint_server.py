#!/usr/bin/env python3
"""
PMO (Prime Minister Office) SharePoint MCP Server
"""

import logging
import sys
from pathlib import Path

# Ensure local imports work
sys.path.insert(0, str(Path(__file__).parent))

from generic_sharepoint_server_multi_dept import run_department_server

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - PMO-SharePoint - %(levelname)s - %(message)s",
    )

    run_department_server("PMO")
