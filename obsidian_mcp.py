#!/usr/bin/env python3
"""Back-compat entrypoint. Prefer: mcp-starter serve"""
from mcp_starter.server import main

if __name__ == "__main__":
    main()
