"""Only invoked by integration tests to terminate a real worker at durable-action boundaries."""

import asyncio
import os
import sys

from repairlab.api import create_app
from repairlab.tools import ToolExecutor


async def main():
    phase = sys.argv[1]
    original_perform = ToolExecutor._perform
    original_execute = ToolExecutor.execute

    async def perform(self, lease, agent_id, call, *args):
        if call.name == "write_file" and phase == "before":
            os._exit(73)
        result = await original_perform(self, lease, agent_id, call, *args)
        if call.name == "write_file" and phase == "after":
            os._exit(73)
        return result

    async def execute(self, lease, agent_id, cursor, index, call):
        result = await original_execute(self, lease, agent_id, cursor, index, call)
        if call.name == "write_file" and phase == "after-result":
            os._exit(73)
        return result

    ToolExecutor._perform, ToolExecutor.execute = perform, execute
    app = create_app()
    async with app.router.lifespan_context(app):
        lease = app.state.ledger.claim("crash-worker")
        if not lease:
            raise RuntimeError("no queued test run")
        await app.state.harness.run(lease)


if __name__ == "__main__":
    asyncio.run(main())
