import json
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from repairlab.db import AgentRow, ArtifactRow, IssueRow, ReceiptRow, RunRow
from repairlab.domain import Experiment, ToolCall, digest
from repairlab.knowledge import DeterministicEmbedding
from repairlab.ledger import LeaseLost, RunStopped
from repairlab.scripts import FIXED_CODE
from repairlab.storage import PolicyError, atomic_write, safe_path
from sqlalchemy import select

from .conftest import execute


@pytest.mark.parametrize("strategy", ["single", "parallel", "fixed", "adaptive"])
async def test_harness_with_unit_sandbox(app, demo, strategy):
    result = await execute(app, demo["issue"], strategy)
    assert result["status"] == "succeeded", result["terminal_reason"]
    assert result["spent"] == 0 and result["reserved"] == 0
    assert result["model_source"] == "scripted"
    assert result["verifications"][0]["patch_hash"] == result["patch_hash"]
    assert all(a["status"] == "accepted" for a in result["agents"] if a["parent_id"])
    if strategy == "adaptive":
        assert len(result["agents"]) == 4
        assert any(r["name"] == "integrate" for r in result["receipts"])
    exported = app.state.platform.export(result["id"])
    assert exported["events"] and exported["artifact_content"]
    assert (app.state.settings.data_root / "checkpoints.db").stat().st_size > 0


@pytest.mark.parametrize(
    "script_name,reason", [("empty", "empty_patch"), ("wrong", "tests_failed"), ("injection", "tool_error")]
)
async def test_invalid_completion(app, demo, script_name, reason):
    result = await execute(app, demo["issue"], script_name=script_name)
    assert result["status"] == "failed" and result["terminal_reason"] == reason


async def test_no_model_bypass(client, demo):
    response = await client.post(
        "/api/runs", json={"issue_id": demo["issue"]["id"], "model_source": "deepseek"}
    )
    assert response.status_code == 409
    response = await client.post(f"/api/projects/{demo['project']['id']}/index?vectors=real", json={})
    assert response.status_code == 409
    response = await client.post(
        "/api/experiments",
        json={"name": "formal", "issue_ids": [demo["issue"]["id"]], "strategies": ["single"], "formal": True},
    )
    assert response.status_code == 409
    assert (await client.get("/health")).json()["model_calls_enabled"] is False


async def test_pause_resume_cancel_retry(client, app, demo):
    run = app.state.platform.submit(demo["issue"]["id"])
    assert (await client.post(f"/api/runs/{run['id']}/control/pause")).json()["status"] == "paused"
    assert app.state.ledger.claim("worker") is None
    await client.post(f"/api/runs/{run['id']}/control/resume")
    lease = app.state.ledger.claim("worker")
    await client.post(f"/api/runs/{run['id']}/control/cancel")
    with pytest.raises(RunStopped):
        app.state.ledger.safe_point(lease)
    assert app.state.platform.detail(run["id"])["status"] == "cancelled"
    retry = (await client.post(f"/api/runs/{run['id']}/control/retry")).json()
    assert retry["id"] != run["id"] and retry["retry_of"] == run["id"]


async def test_concurrent_claim_and_fencing(app, demo):
    run = app.state.platform.submit(demo["issue"]["id"])
    with ThreadPoolExecutor(max_workers=6) as pool:
        claims = list(pool.map(app.state.ledger.claim, [f"w{i}" for i in range(6)]))
    assert len([x for x in claims if x]) == 1
    old = next(x for x in claims if x)
    with app.state.db.transaction() as session:
        session.get(RunRow, run["id"]).lease_until = time.time() - 10
    new = app.state.ledger.claim("takeover")
    assert new.epoch == old.epoch + 1
    with pytest.raises(LeaseLost):
        app.state.ledger.heartbeat(old)
    app.state.ledger.end(new, "failed", "test_cleanup")


async def test_write_reconciliation_after_crash(app, demo):
    run = app.state.platform.submit(demo["issue"]["id"])
    lease = app.state.ledger.claim("writer")
    agent_id = run["id"] + "-supervisor"
    call = ToolCall(
        id="write", name="write_file", arguments={"path": "src/calculator.py", "content": FIXED_CODE}
    )
    key = digest([run["id"], agent_id, 0, 0, call.model_dump()])
    with app.state.db.transaction() as session:
        agent = session.get(AgentRow, agent_id)
        workspace = app.state.tools.workspace(session, session.get(RunRow, run["id"]), agent)
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
                name=call.name,
                arguments=call.arguments,
                status="intent",
                plan=plan,
            )
        )
    atomic_write(workspace / "src/calculator.py", FIXED_CODE.encode())
    result = await app.state.tools.execute(lease, agent_id, 0, 0, call)
    again = await app.state.tools.execute(lease, agent_id, 0, 0, call)
    assert result == again
    with app.state.db.sessions() as session:
        artifact = session.get(ArtifactRow, result["artifact_id"])
        assert json.loads(app.state.platform.store.read(artifact))["reconciled"]
        assert len(list(session.scalars(select(ReceiptRow).where(ReceiptRow.run_id == run["id"])))) == 1


async def test_stale_verification_and_forged_child(app, demo):
    run = app.state.platform.submit(demo["issue"]["id"], strategy="adaptive")
    lease = app.state.ledger.claim("worker")
    child_id = run["id"] + "-forged"
    with app.state.db.transaction() as session:
        session.add(
            AgentRow(
                id=child_id,
                run_id=run["id"],
                parent_id=run["id"] + "-supervisor",
                key="forged",
                role="implementation",
                status="running",
                request={"scope": ["src/"], "deliverables": ["patch"], "artifacts": ["nonexistent"]},
            )
        )
    await app.state.harness._finish_child(lease, child_id)
    with app.state.db.sessions() as session:
        assert session.get(AgentRow, child_id).status == "rejected"
        contract = app.state.ledger.contract(session, session.get(RunRow, run["id"]))
    with pytest.raises(PolicyError, match="stale"):
        await app.state.harness.verifier._record(
            lease, contract, "old-patch", True, "forged", "env", "verifier", {}
        )


async def test_budget_and_uncertain_model_call(app, demo):
    run = app.state.platform.submit(demo["issue"]["id"])
    lease = app.state.ledger.claim("worker")
    app.state.ledger.reserve(lease, "call-a", [], "scripted")
    with pytest.raises(RunStopped, match="uncertain_model_call"):
        app.state.ledger.reserve(lease, "call-a", [], "scripted")
    with app.state.db.transaction() as session:
        session.get(RunRow, run["id"]).calls = 60
    with pytest.raises(RunStopped, match="budget_exhausted"):
        app.state.ledger.reserve(lease, "call-b", [], "scripted")


async def test_sse_resume_export_auth(client, app, demo):
    result = await execute(app, demo["issue"])
    response = await client.get(
        f"/api/runs/{result['id']}/events?follow=false", headers={"Last-Event-ID": "3"}
    )
    seqs = [int(line[4:]) for line in response.text.splitlines() if line.startswith("id: ")]
    assert seqs and min(seqs) > 3 and len(seqs) == len(set(seqs))
    assert (await client.get(f"/api/runs/{result['id']}/export")).json()["artifact_content"]
    assert (await client.get("/api/projects", headers={"Authorization": "bad"})).status_code == 401
    assert (await client.get("/api/artifacts/nonexistent")).status_code == 404


async def test_search_project_scope_vectors_and_memory_guards(app, demo):
    knowledge = app.state.platform.knowledge
    project = demo["project"]
    knowledge.index(project["id"], DeterministicEmbedding())
    results = knowledge.search(project["id"], project["commit"], "clamp", embedding=DeterministicEmbedding())
    assert results and all(r["project_id"] == project["id"] for r in results)
    assert results[0]["line"] >= 1 and results[0]["commit"] == project["commit"]
    assert knowledge.search("another-project", project["commit"], "clamp") == []
    from repairlab.domain import MemoryEntry

    with pytest.raises(PolicyError):
        knowledge.create_memory(
            MemoryEntry(
                project_id=project["id"],
                content="def answer(): pass",
                source_artifacts=["fake"],
                applicable_versions=["fixture-v1"],
                invalidation_conditions="new version",
            )
        )


async def test_experiment_isolation(app, demo):
    experiment = app.state.platform.create_experiment(
        Experiment(
            name="scripted comparison", issue_ids=[demo["issue"]["id"]], strategies=["single", "adaptive"]
        )
    )
    runs = app.state.platform.launch_experiment(experiment["id"])
    assert len(runs) == 2 and all(r["memory_snapshot"] == [] for r in runs)
    with pytest.raises(PolicyError):
        app.state.platform.launch_experiment(experiment["id"])
    report = app.state.platform.experiment_report(experiment["id"])
    assert report["scripted_test"] and not report["formal_model_evidence"]


@pytest.mark.parametrize(
    "path",
    [
        "../file",
        "/etc/passwd",
        "C:/secret",
        ".env",
        ".aws/credentials",
        "src/../../foo",
        "src\\foo",
        "src/secret.key",
    ],
)
def test_paths(tmp_path, path):
    with pytest.raises(PolicyError):
        safe_path(tmp_path, path)


async def test_task_contract_tamper(app, demo):
    app.state.platform.submit(demo["issue"]["id"])
    lease = app.state.ledger.claim("worker")
    with app.state.db.transaction() as session:
        issue = session.get(IssueRow, demo["issue"]["id"])
        issue.contract = {**issue.contract, "allowed_paths": ["private/"]}
    with pytest.raises(ValueError, match="immutable"):
        app.state.ledger.safe_point(lease)
