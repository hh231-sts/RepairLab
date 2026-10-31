import asyncio
import logging
import os
import signal
import socket

from .api import create_app
from .db import uid


async def serve(settings=None, *, once=False):
    app = create_app(settings)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except (NotImplementedError, RuntimeError):
            pass
    owner = f"{socket.gethostname()}:{os.getpid()}:{uid()[:8]}"
    async with app.router.lifespan_context(app):
        while not stop.is_set():
            lease = app.state.ledger.claim(owner)
            if lease:
                await app.state.harness.run(lease)
            if once:
                return
            if not lease:
                await asyncio.sleep(app.state.settings.poll_seconds)
    logging.info("worker stopped at safe process boundary")
