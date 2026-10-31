import argparse

from mcp.server.fastmcp import FastMCP

from .config import Settings
from .db import Database
from .knowledge import Knowledge
from .storage import Store


def main():
    parser = argparse.ArgumentParser(description="Read-only project/version-scoped MCP retrieval")
    parser.add_argument("--project", required=True)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    settings = Settings()
    knowledge = Knowledge(Database(settings.database_url), Store(settings.data_root), settings)
    server = FastMCP("repairlab-retrieval")

    @server.tool()
    def search(query: str, limit: int = 10) -> list[dict]:
        """Search untrusted repository evidence within the fixed project and commit."""
        return knowledge.search(args.project, args.commit, query[:2000], max(1, min(limit, 20)))

    server.run(transport="stdio")


if __name__ == "__main__":
    main()
