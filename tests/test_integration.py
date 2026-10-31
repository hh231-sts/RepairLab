import asyncio
import json
import os
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from repairlab.api import create_app
from repairlab.config import Settings
from repairlab.db import AgentRow, ArtifactRow, ReceiptRow, RunRow
from repairlab.domain import ToolCall, digest
from repairlab.knowledge import DeterministicEmbedding
from repairlab.ledger import LeaseLost
from repairlab.scripts import FIXED_CODE
from repairlab.storage import atomic_write
from sqlalchemy import select, text

from .conftest import ROOT

pytestmark = pytest.mark.integration


@pytest.fixture
async def real_app(tmp_path):
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL required; real PostgreSQL and Docker are not substituted")
    settings = Settings(
        database_url=url,
        data_root=tmp_path / "data",
        repository_root=ROOT / "fixtures/repos",
        task_root=ROOT / "fixtures/tasks",
        api_token="integration-token",
        lease_seconds=6,
        tool_timeout=30,
    )
    instance = create_app(settings)
    async with instance.router.lifespan_context(instance):
        yield instance


@pytest.mark.parametrize(
    "strategy,script_name,expected",
    [
        ("single", "repair", "succeeded"),
        ("adaptive", "repair", "succeeded"),
        ("single", "wrong", "failed"),
        ("single", "empty", "failed"),
    ],
)
async def test_postgres_docker_mcp_full_flow(real_app, strategy, script_name, expected):
    app = real_app
    demo = await app.state.platform.demo(app.state.tools.sandbox)
    run = app.state.platform.submit(demo["issue"]["id"], strategy=strategy, script_name=script_name)
    lease = app.state.ledger.claim("real-worker")
    assert lease and lease.run_id == run["id"]
    await app.state.harness.run(lease)
    detail = app.state.platform.detail(run["id"])
    assert detail["status"] == expected, detail["terminal_reason"]
    assert detail["spent"] == 0 and detail["model_source"] == "scripted"
    if expected == "succeeded":
        assert detail["verifications"][0]["passed"]
        assert any(r["name"] == "search" and r["status"] == "succeeded" for r in detail["receipts"])
        with app.state.db.sessions() as session:
            assert (
                session.execute(
                    text("SELECT count(*) FROM checkpoints WHERE thread_id=:id"),
                    {"id": run["id"] + "-supervisor"},
                ).scalar()
                > 0
            )


async def test_pg_claim_takeover_late_result_and_duplicate(real_app):
    app = real_app
    demo = await app.state.platform.demo(app.state.tools.sandbox)
    run = app.state.platform.submit(demo["issue"]["id"])
    with ThreadPoolExecutor(max_workers=8) as pool:
        claims = list(pool.map(app.state.ledger.claim, [f"concurrent-{i}" for i in range(8)]))
    assert sum(c is not None for c in claims) == 1
    old = next(c for c in claims if c)
    agent = run["id"] + "-supervisor"
    call = ToolCall(id="test", name="run_tests", arguments={"paths": ["tests"]})
    first = await app.state.tools.execute(old, agent, 0, 0, call)
    duplicate = await app.state.tools.execute(old, agent, 0, 0, call)
    assert first == duplicate
    with app.state.db.transaction() as session:
        session.get(RunRow, run["id"]).lease_until = time.time() - 1
    new = app.state.ledger.claim("replacement")
    with pytest.raises(LeaseLost):
        await app.state.tools.execute(
            old,
            agent,
            1,
            0,
            ToolCall(
                id="late", name="write_file", arguments={"path": "src/calculator.py", "content": "late"}
            ),
        )
    assert new.epoch > old.epoch
    app.state.ledger.end(new, "failed", "integration_cleanup")
    await app.state.tools.sandbox.stop(
        "repairlab-" + digest([run["id"], agent, 0, 0, call.model_dump()])[:40]
    )


async def test_pg_crash_after_write_and_workspace_loss(real_app):
    app = real_app
    demo = await app.state.platform.demo(app.state.tools.sandbox)
    run = app.state.platform.submit(demo["issue"]["id"])
    lease = app.state.ledger.claim("before-crash")
    agent_id = run["id"] + "-supervisor"
    call = ToolCall(
        id="write", name="write_file", arguments={"path": "src/calculator.py", "content": FIXED_CODE}
    )
    key = digest([run["id"], agent_id, 0, 0, call.model_dump()])
    with app.state.db.transaction() as session:
        workspace = app.state.tools.workspace(
            session, session.get(RunRow, run["id"]), session.get(AgentRow, agent_id)
        )
        plan = {
            "before": digest((workspace / "src/calculator.py").read_bytes()),
            "after": digest(FIXED_CODE.encode()),
        }
        session.add(
            ReceiptRow(
                id=key,
                run_id=run["id"],
                agent_id=agent_id,
                epoch=lease.epoch,
                name="write_file",
                arguments=call.arguments,
                plan=plan,
                status="intent",
            )
        )
    atomic_write(workspace / "src/calculator.py", FIXED_CODE.encode())
    with app.state.db.transaction() as session:
        session.get(RunRow, run["id"]).lease_until = 0
    lease = app.state.ledger.claim("after-crash")
    result = await app.state.tools.execute(lease, agent_id, 0, 0, call)
    with app.state.db.sessions() as session:
        payload = app.state.platform.store.read(session.get(ArtifactRow, result["artifact_id"]))
        assert b'"reconciled": true' in payload
    # Simulate loss of the writable workspace volume after the durable receipt exists.
    assert workspace.resolve().is_relative_to(app.state.settings.data_root.resolve())
    shutil.rmtree(workspace)
    verification = await app.state.harness.verifier.verify(lease)
    assert verification.passed
    app.state.ledger.end(lease, "succeeded", "reconciled_and_verified")


async def test_container_network_and_secret_isolation(real_app, tmp_path):
    sandbox = real_app.state.tools.sandbox
    workspace = tmp_path / "isolated"
    workspace.mkdir()
    (workspace / "test_isolation.py").write_text(
        """import os,socket,pathlib
def test_isolated():
    assert 'DEEPSEEK_API_KEY' not in os.environ
    assert not pathlib.Path('/var/run/docker.sock').exists()
    assert not pathlib.Path('/verifier').exists()
    try:
        socket.create_connection(('1.1.1.1',443),timeout=0.2)
    except OSError:
        pass
    else:
        raise AssertionError('network escaped')
    try:
        pathlib.Path('/workspace/mutation').write_text('forbidden')
    except OSError:
        pass
    else:
        raise AssertionError('workspace was writable')
""",
        "utf-8",
    )
    action = digest([str(tmp_path), "isolation"])
    result = await sandbox.test(
        workspace, real_app.state.settings.sandbox_image, ["test_isolation.py"], action, 20
    )
    await sandbox.stop("repairlab-" + action[:40])
    assert result["exit_code"] == 0, result


async def test_pgvector_fts(real_app):
    app = real_app
    demo = await app.state.platform.demo(app.state.tools.sandbox)
    project = demo["project"]
    knowledge = app.state.platform.knowledge
    knowledge.index(project["id"], DeterministicEmbedding())
    results = knowledge.search(project["id"], project["commit"], "clamp", embedding=DeterministicEmbedding())
    assert results and results[0]["score"] > 0
    assert (
        knowledge.search("other-project", project["commit"], "clamp", embedding=DeterministicEmbedding())
        == []
    )


@pytest.mark.parametrize("phase", ["before", "after", "after-result"])
async def test_real_worker_process_crash_recovery(real_app, phase):
    app = real_app
    demo = await app.state.platform.demo(app.state.tools.sandbox)
    run = app.state.platform.submit(demo["issue"]["id"])
    settings = app.state.settings
    env = {
        k: v
        for k, v in os.environ.items()
        if k in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERPROFILE", "APPDATA", "LOCALAPPDATA"}
    }
    env.update(
        {
            "DATABASE_URL": settings.database_url,
            "DATA_ROOT": str(settings.data_root.resolve()),
            "REPOSITORY_ROOT": str(settings.repository_root),
            "TASK_ROOT": str(settings.task_root),
            "MODEL_CALLS_ENABLED": "false",
            "EMBEDDING_ENABLED": "false",
            "LANGSMITH_TRACING": "false",
        }
    )
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "tests.crash_worker",
        phase,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, err = await asyncio.wait_for(process.communicate(), 90)
    assert process.returncode == 73, err.decode(errors="replace")
    with app.state.db.transaction() as session:
        crashed = session.get(RunRow, run["id"])
        assert crashed.status == "running"
        crashed.lease_until = 0
    lease = app.state.ledger.claim("recovered-process")
    await app.state.harness.run(lease)
    detail = app.state.platform.detail(run["id"])
    assert detail["status"] == "succeeded", detail["terminal_reason"]
    writes = [r for r in detail["receipts"] if r["name"] == "write_file"]
    assert len(writes) == 1 and writes[0]["status"] == "succeeded"


async def test_real_container_cancel_race_and_timeout(real_app):
    app = real_app
    demo = await app.state.platform.demo(app.state.tools.sandbox)
    run = app.state.platform.submit(demo["issue"]["id"])
    lease = app.state.ledger.claim("cancel-race")
    agent = run["id"] + "-supervisor"
    with app.state.db.transaction() as session:
        workspace = app.state.tools.workspace(
            session, session.get(RunRow, run["id"]), session.get(AgentRow, agent)
        )
    (workspace / "tests/test_slow.py").write_text(
        "import time\ndef test_slow():\n    time.sleep(15)\n", "utf-8"
    )
    call = ToolCall(id="slow", name="run_tests", arguments={"paths": ["tests/test_slow.py"]})
    key = digest([run["id"], agent, 0, 0, call.model_dump()])
    action = asyncio.create_task(app.state.tools.execute(lease, agent, 0, 0, call))
    for _ in range(60):
        state = await app.state.tools.sandbox.inspect("repairlab-" + key[:40])
        if state and state["State"]["Status"] == "running":
            break
        await asyncio.sleep(0.1)
    app.state.ledger.control(run["id"], "cancel")
    await action
    from repairlab.ledger import RunStopped

    with pytest.raises(RunStopped):
        app.state.ledger.safe_point(lease)
    assert app.state.platform.detail(run["id"])["status"] == "cancelled"
    await app.state.tools.sandbox.stop("repairlab-" + key[:40])
    from repairlab.sandbox import SandboxError

    timeout_key = digest([run["id"], "timeout"])
    with pytest.raises(SandboxError, match="timeout"):
        await app.state.tools.sandbox.test(
            workspace, app.state.settings.sandbox_image, ["tests/test_slow.py"], timeout_key, 1
        )
    await app.state.tools.sandbox.stop("repairlab-" + timeout_key[:40])


async def test_synthetic_dataset_real_container_admission(real_app, tmp_path):
    from repairlab.tasks import import_swebench, preflight

    from .test_tasks import synthetic_manifest

    platform = real_app.state.platform
    path = synthetic_manifest(platform, tmp_path)
    selection = import_swebench(platform, str(path), "a" * 40)
    report = await preflight(platform, selection["candidates"][0]["manifest"], real_app.state.tools.sandbox)
    assert report["admitted"], report["results"]
    assert all(x["matches"] for x in report["results"])
    assert len(report["results"]) == 6


async def test_lost_readonly_container_reconciles_same_action(real_app):
    app = real_app
    demo = await app.state.platform.demo(app.state.tools.sandbox)
    run = app.state.platform.submit(demo["issue"]["id"])
    lease = app.state.ledger.claim("container-loss")
    agent_id = run["id"] + "-supervisor"
    call = ToolCall(id="public-test", name="run_tests", arguments={"paths": ["tests"]})
    result = await app.state.tools.execute(lease, agent_id, 0, 0, call)
    key = digest([run["id"], agent_id, 0, 0, call.model_dump()])
    await app.state.tools.sandbox.stop("repairlab-" + key[:40])
    with app.state.db.transaction() as session:
        receipt = session.get(ReceiptRow, key)
        receipt.status, receipt.result = "intent", None
    replay = await app.state.tools.execute(lease, agent_id, 0, 0, call)
    assert replay["exit_code"] == result["exit_code"] == 1
    with app.state.db.sessions() as session:
        assert len(list(session.scalars(select(ReceiptRow).where(ReceiptRow.run_id == run["id"])))) == 1
    app.state.ledger.end(lease, "failed", "readonly_container_loss_reconciled")
    await app.state.tools.sandbox.stop("repairlab-" + key[:40])


async def test_changed_patch_rejects_old_real_verification(real_app):
    app = real_app
    demo = await app.state.platform.demo(app.state.tools.sandbox)
    run = app.state.platform.submit(demo["issue"]["id"])
    lease = app.state.ledger.claim("patch-version")
    agent_id = run["id"] + "-supervisor"
    await app.state.tools.execute(
        lease,
        agent_id,
        0,
        0,
        ToolCall(
            id="correct", name="write_file", arguments={"path": "src/calculator.py", "content": FIXED_CODE}
        ),
    )
    prior = await app.state.harness.verifier.verify(lease)
    assert prior.passed
    await app.state.tools.execute(
        lease,
        agent_id,
        1,
        0,
        ToolCall(
            id="wrong",
            name="write_file",
            arguments={
                "path": "src/calculator.py",
                "content": "def clamp(value, low, high):\n    return low\n",
            },
        ),
    )
    from repairlab.storage import PolicyError

    with app.state.db.sessions() as session:
        contract = app.state.ledger.contract(session, session.get(RunRow, run["id"]))
    with pytest.raises(PolicyError, match="stale"):
        await app.state.harness.verifier._record(
            lease,
            contract,
            prior.patch_hash,
            True,
            "old_result",
            prior.environment_hash,
            prior.verifier_hash,
            {},
        )
    current = await app.state.harness.verifier.verify(lease)
    assert not current.passed and current.patch_hash != prior.patch_hash
    app.state.ledger.end(lease, "failed", "tests_failed")


async def test_public_regression_is_part_of_independent_scoring(real_app):
    app = real_app
    demo = await app.state.platform.demo(app.state.tools.sandbox)
    run = app.state.platform.submit(demo["issue"]["id"])
    lease = app.state.ledger.claim("regression-scoring")
    # Hidden fixture cases pass, but the existing public case value=11 regresses.
    wrong = FIXED_CODE.replace(
        "    return max(low, min(value, high))",
        "    if value == 11:\n        return 9\n    return max(low, min(value, high))",
    )
    await app.state.tools.execute(
        lease,
        run["id"] + "-supervisor",
        0,
        0,
        ToolCall(
            id="regression", name="write_file", arguments={"path": "src/calculator.py", "content": wrong}
        ),
    )
    result = await app.state.harness.verifier.verify(lease)
    assert not result.passed and result.reason == "tests_failed"
    app.state.ledger.end(lease, "failed", result.reason)


async def test_mock_deepseek_details_with_real_database_and_verifier(real_app, monkeypatch):
    import httpx
    from repairlab import harness as harness_module
    from repairlab.models import DeepSeekAdapter

    app = real_app
    settings = app.state.settings
    settings.model_calls_enabled = True
    settings.deepseek_api_key = "mock"
    settings.price_snapshot = "mock-nested-usage-regression"
    settings.input_cny_per_million = 2
    settings.output_cny_per_million = 8
    settings.global_budget_cny = 2000
    responses = [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "inspect",
                    "function": {"name": "read_file", "arguments": json.dumps({"path": "src/calculator.py"})},
                }
            ],
        },
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "repair",
                    "function": {
                        "name": "write_file",
                        "arguments": json.dumps({"path": "src/calculator.py", "content": FIXED_CODE}),
                    },
                }
            ],
        },
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "public-test",
                    "function": {"name": "run_tests", "arguments": json.dumps({"paths": ["tests"]})},
                }
            ],
        },
        {"role": "assistant", "content": "Request independent verification", "tool_calls": None},
    ]
    usage = {
        "prompt_tokens": 100,
        "completion_tokens": 10,
        "total_tokens": 110,
        "prompt_tokens_details": {"cached_tokens": 0},
        "completion_tokens_details": {"reasoning_tokens": 0},
    }
    observed = []

    def respond(request):
        observed.append(json.loads(request.content))
        return httpx.Response(
            200, json={"choices": [{"message": responses[len(observed) - 1]}], "usage": usage}
        )

    adapter = DeepSeekAdapter(
        settings.model_copy(update={"deepseek_api_key": "mock"}), httpx.MockTransport(respond)
    )
    monkeypatch.setattr(harness_module, "select_model", lambda *args: adapter)
    demo = await app.state.platform.demo(app.state.tools.sandbox)
    run = app.state.platform.submit(demo["issue"]["id"], model_source="deepseek")
    await app.state.harness.run(app.state.ledger.claim("mock-schema-integration"))
    detail = app.state.platform.detail(run["id"])
    assert detail["status"] == "succeeded", detail["terminal_reason"]
    assert detail["calls"] == len(observed) == 4
    assert detail["reserved"] == pytest.approx(0)
    assert detail["spent"] == pytest.approx(0.00112)
    assert detail["verifications"][0]["passed"]
    assert all(
        call["status"] == "settled" and call["metadata_json"]["usage"] == usage
        for call in detail["model_calls"]
    )


async def test_real_database_mixed_model_calls_and_delegation(real_app, monkeypatch):
    import httpx
    from repairlab import harness as harness_module
    from repairlab.models import DeepSeekAdapter

    app = real_app
    settings = app.state.settings
    settings.model_calls_enabled = True
    settings.deepseek_api_key = "mock"
    settings.price_snapshot = "mixed-call-mock"
    settings.input_cny_per_million = 2
    settings.output_cny_per_million = 8
    from repairlab.domain import ToolCall

    request = {
        "key": "investigation",
        "role": "code_investigation",
        "objective": "Inspect source",
        "scope": ["src/"],
        "deliverables": ["note"],
        "hypothesis": "Missing boundary check",
        "evidence": ["issue"],
    }
    parent = [
        [
            ToolCall(id="read", name="read_file", arguments={"path": "src/calculator.py"}),
            ToolCall(id="delegate", name="delegate", arguments=request),
            ToolCall(id="note", name="note", arguments={"text": "Keep source and child evidence."}),
        ],
        [
            ToolCall(
                id="fix", name="write_file", arguments={"path": "src/calculator.py", "content": FIXED_CODE}
            )
        ],
        [],
    ]
    child = [
        [ToolCall(id="child-read", name="read_file", arguments={"path": "src/calculator.py"})],
        [
            ToolCall(
                id="child-note", name="note", arguments={"text": "Source lacks inverted bounds validation."}
            )
        ],
        [],
    ]

    class Adapter:
        async def complete(self, messages, tools, *, cursor=0):
            role = json.loads(messages[0]["content"])["role"]
            calls = (parent if role == "supervisor" else child)[cursor]
            if role == "supervisor" and cursor == 1:
                assert [m.get("tool_call_id") for m in messages[-3:]] == ["read", "delegate", "note"]
            message = {"role": "assistant", "content": "Request verification", "tool_calls": None}
            if calls:
                message["tool_calls"] = [
                    {
                        "id": c.id,
                        "type": "function",
                        "function": {"name": c.name, "arguments": json.dumps(c.arguments)},
                    }
                    for c in calls
                ]
            body = {
                "choices": [{"message": message}],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 10,
                    "prompt_tokens_details": {"cached_tokens": 0},
                },
            }
            adapter = DeepSeekAdapter(
                settings, httpx.MockTransport(lambda request: httpx.Response(200, json=body))
            )
            return await adapter.complete(messages, tools, cursor=cursor)

    monkeypatch.setattr(harness_module, "select_model", lambda *args: Adapter())
    demo = await app.state.platform.demo(app.state.tools.sandbox)
    run = app.state.platform.submit(
        demo["issue"]["id"],
        model_source="deepseek",
        strategy="adaptive",
        limits={"max_cost_cny": 1, "max_calls": 20, "max_seconds": 600},
    )
    await app.state.harness.run(app.state.ledger.claim("mixed-model-integration"))
    detail = app.state.platform.detail(run["id"])
    assert detail["status"] == "succeeded", detail["terminal_reason"]
    assert detail["calls"] == 6 and detail["reserved"] == pytest.approx(0)
    assert all(call["status"] == "settled" for call in detail["model_calls"])
    assert any(
        receipt["name"] == "delegate" and receipt["status"] == "succeeded" for receipt in detail["receipts"]
    )
