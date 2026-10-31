import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class RetrievalClient:
    def __init__(self, settings):
        self.settings = settings

    async def search(self, project_id: str, commit: str, query: str):
        env = {
            key: value
            for key, value in os.environ.items()
            if key in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP"}
        }
        env.update(
            {
                "DATABASE_URL": self.settings.database_url,
                "DATA_ROOT": str(self.settings.data_root.resolve()),
                "MODEL_CALLS_ENABLED": "false",
                "EMBEDDING_ENABLED": "false",
            }
        )
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "repairlab.mcp_server", "--project", project_id, "--commit", commit],
            env=env,
        )
        async with stdio_client(params) as (reader, writer), ClientSession(reader, writer) as session:
            await session.initialize()
            available = await session.list_tools()
            if [t.name for t in available.tools] != ["search"]:
                raise RuntimeError("unexpected MCP retrieval capabilities")
            result = await session.call_tool("search", {"query": query, "limit": 10})
            if result.isError:
                raise RuntimeError("MCP retrieval failed")
            if result.structuredContent:
                return result.structuredContent.get("result", result.structuredContent)
            return [json.loads(block.text) for block in result.content if block.type == "text"]
