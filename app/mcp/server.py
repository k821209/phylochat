"""PhyloChat MCP server — stdio transport for Claude Code integration."""

import asyncio
import sys
from pathlib import Path

# Ensure project root is on sys.path so `app.*` imports work
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp.server import Server
from mcp.server.stdio import stdio_server

from app.mcp.tools import register_tools
from app.mcp.resources import register_resources

server = Server("phylochat")
register_tools(server)
register_resources(server)


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
