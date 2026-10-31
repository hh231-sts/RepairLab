import socket
from pathlib import Path

import httpx
import pytest
from repairlab.api import create_app
from repairlab.config import Settings

ROOT = Path(__file__).resolve().parents[1]
NETWORK_AUDIT = {"real_model_http_attempts": 0, "mock_model_http_requests": 0}


@pytest.fixture(autouse=True)
def deny_external_network(monkeypatch, request):
    original = socket.socket.connect

    def guarded(sock, address):
        # asyncio's Windows self-pipe also uses a loopback socket pair.
        if isinstance(address, tuple) and address[0] in {"127.0.0.1", "::1", "localhost"}:
            return original(sock, address)
        raise AssertionError(f"external network forbidden in tests: {address}")

    monkeypatch.setattr(socket.socket, "connect", guarded)
    original_send = httpx.AsyncClient.send

    async def guarded_send(client, req, *args, **kwargs):
        if req.url.host == "api.deepseek.com":
            if not isinstance(client._transport, httpx.MockTransport):
                NETWORK_AUDIT["real_model_http_attempts"] += 1
                raise AssertionError("real model HTTP is forbidden")
            NETWORK_AUDIT["mock_model_http_requests"] += 1
        return await original_send(client, req, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "send", guarded_send)
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("MODEL_CALLS_ENABLED", "false")
    monkeypatch.setenv("EMBEDDING_ENABLED", "false")


def pytest_sessionfinish(session, exitstatus):
    import json
    import os

    folder = ROOT / ".cache"
    folder.mkdir(exist_ok=True)
    (folder / os.environ.get("NETWORK_AUDIT_FILE", "network-audit-unit.json")).write_text(
        json.dumps(NETWORK_AUDIT, indent=2), "utf-8"
    )


class SandboxDouble:
    """Harness unit double. Does not execute repository code on the host."""

    def __init__(self):
        self.calls = []

    async def image_hash(self, image):
        return "sha256:unit-test-image"

    async def test(self, workspace, image, paths, action_id, timeout, verifier=None, cancelled=None):
        self.calls.append(action_id)
        text = (workspace / "src/calculator.py").read_text()
        passed = "if low > high:" in text and "return max(low, min(value, high))" in text
        return {"exit_code": 0 if passed else 1, "stdout": "UNIT DOUBLE ONLY", "stderr": ""}

    async def stop(self, name):
        pass


class RetrievalDouble:
    def __init__(self, knowledge):
        self.knowledge = knowledge

    async def search(self, project_id, commit, query):
        return self.knowledge.search(project_id, commit, query)


@pytest.fixture
async def app(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{(tmp_path / 'ledger.db').as_posix()}",
        data_root=tmp_path / "data",
        repository_root=ROOT / "fixtures/repos",
        task_root=ROOT / "fixtures/tasks",
        api_token="test-token",
    )
    instance = create_app(settings, sandbox=SandboxDouble())
    instance.state.tools.retrieval = RetrievalDouble(instance.state.platform.knowledge)
    async with instance.router.lifespan_context(instance):
        yield instance


@pytest.fixture
async def client(app):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": "Bearer test-token"},
    ) as c:
        yield c


@pytest.fixture
async def demo(app):
    return await app.state.platform.demo(app.state.tools.sandbox)


async def execute(app, issue, strategy="single", script_name="repair"):
    run = app.state.platform.submit(issue["id"], strategy=strategy, script_name=script_name)
    lease = app.state.ledger.claim("unit-worker")
    assert lease and lease.run_id == run["id"]
    await app.state.harness.run(lease)
    return app.state.platform.detail(run["id"])
