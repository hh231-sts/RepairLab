import json
import socket

import pytest
from repairlab.context import EvidenceCompressor
from repairlab.db import AgentRow, MemoryRow, ModelCallRow, RunRow
from repairlab.domain import DelegationRequest, Experiment, MemoryEntry
from repairlab.ledger import RunStopped
from repairlab.storage import PolicyError, safe_path
from sqlalchemy import select

from .conftest import execute


async def test_submission_idempotency(client, demo):
    data = {"issue_id": demo["issue"]["id"], "strategy": "single"}
    headers = {"Idempotency-Key": "repeat-request"}
    first = await client.post("/api/runs", json=data, headers=headers)
    second = await client.post("/api/runs", json=data, headers=headers)
    assert first.json()["id"] == second.json()["id"]
    invalid = await client.post("/api/runs", json={**data, "strategy": "adaptive"}, headers=headers)
    assert invalid.status_code == 409


async def test_experiment_launch_is_atomic(app, demo):
    experiment = app.state.platform.create_experiment(
        Experiment(name="atomic", issue_ids=[demo["issue"]["id"]], strategies=["single", "adaptive"])
    )
    with app.state.db.transaction() as session:
        from repairlab.db import ExperimentRow

        row = session.get(ExperimentRow, experiment["id"])
        row.config = {**row.config, "issue_ids": [demo["issue"]["id"], "missing"]}
    with pytest.raises(KeyError):
        app.state.platform.launch_experiment(experiment["id"])
    with app.state.db.sessions() as session:
        assert not list(session.scalars(select(RunRow).where(RunRow.experiment_id == experiment["id"])))


async def test_lease_pause_resume_mid_execution(app, demo):
    run = app.state.platform.submit(demo["issue"]["id"])
    lease = app.state.ledger.claim("before-pause")
    app.state.ledger.control(run["id"], "pause")
    await app.state.harness.run(lease)
    assert app.state.platform.detail(run["id"])["status"] == "paused"
    app.state.ledger.control(run["id"], "resume")
    await app.state.harness.run(app.state.ledger.claim("after-resume"))
    assert app.state.platform.detail(run["id"])["status"] == "succeeded"


async def test_delegation_limits_and_nonexistent_evidence(app, demo):
    run = app.state.platform.submit(demo["issue"]["id"], strategy="adaptive")
    lease = app.state.ledger.claim("worker")
    request = DelegationRequest(
        key="investigation",
        role="code_investigation",
        objective="Locate code",
        scope=["src/"],
        deliverables=["note"],
        hypothesis="Boundary mismatch",
        evidence=["nonexistent"],
    )
    with pytest.raises(PolicyError, match="nonexistent"):
        await app.state.harness._delegate(lease, run["id"] + "-supervisor", [request], None, "adaptive")
    with pytest.raises(PolicyError, match="two"):
        await app.state.harness._delegate(lease, run["id"] + "-supervisor", [request] * 3, None, "adaptive")
    with app.state.db.transaction() as session:
        for i in range(4):
            session.add(
                AgentRow(
                    id=f"{run['id']}-child{i}",
                    run_id=run["id"],
                    parent_id=run["id"] + "-supervisor",
                    key=f"child{i}",
                    role="code_investigation",
                )
            )
    request.evidence = ["issue"]
    with pytest.raises(PolicyError, match="four"):
        await app.state.harness._delegate(lease, run["id"] + "-supervisor", [request], None, "adaptive")


async def test_missing_usage_preserves_reservation(app, demo):
    run = app.state.platform.submit(demo["issue"]["id"])
    lease = app.state.ledger.claim("worker")
    with app.state.db.transaction() as session:
        row = session.get(RunRow, run["id"])
        row.reserved = 1.25
        session.add(
            ModelCallRow(
                id="uncertain",
                run_id=run["id"],
                source="deepseek",
                reserved=1.25,
                status="reserved",
                metadata_json={},
            )
        )
    with app.state.db.transaction() as session:
        row = app.state.ledger.fenced(session, lease)
        app.state.ledger.settle_in_session(session, row, "uncertain", None)
    with app.state.db.sessions() as session:
        assert session.get(RunRow, run["id"]).reserved == 1.25
        assert session.get(ModelCallRow, "uncertain").status == "usage_missing"


async def test_deadline_and_spend_cannot_succeed(app, demo):
    run = app.state.platform.submit(demo["issue"]["id"])
    lease = app.state.ledger.claim("worker")
    with app.state.db.transaction() as session:
        session.get(RunRow, run["id"]).spent = 6
    with pytest.raises(RunStopped, match="budget_exceeded"):
        app.state.ledger.safe_point(lease)
    assert app.state.platform.detail(run["id"])["status"] == "failed"


async def test_stale_and_private_experience(app, demo):
    result = await execute(app, demo["issue"])
    project = demo["project"]
    artifacts = result["artifacts"]
    private = next(a for a in artifacts if a["kind"] == "verification")
    entry = MemoryEntry(
        project_id=project["id"],
        content="Validate input ordering using public evidence before choosing a repair.",
        source_artifacts=[private["id"]],
        applicable_versions=["fixture-v1"],
        invalidation_conditions="changed API contract",
    )
    with pytest.raises(PolicyError, match="public evidence"):
        app.state.platform.knowledge.create_memory(entry)
    public = next(a for a in artifacts if a["kind"] == "read_file")
    entry.source_artifacts = [public["id"]]
    memory = app.state.platform.knowledge.create_memory(entry)
    assert (
        app.state.platform.knowledge.frozen_memories(app.state.db.sessions(), project["id"], "fixture-v1")
        == []
    )
    with pytest.raises(PolicyError, match="two distinct"):
        app.state.platform.knowledge.validate_memory(memory["id"], [result["id"]])
    with app.state.db.transaction() as session:
        row = session.get(MemoryRow, memory["id"])
        row.status = "validated"
    with app.state.db.sessions() as session:
        assert app.state.platform.knowledge.frozen_memories(session, project["id"], "new-version") == []


def test_compression_keeps_constraints_evidence_hypotheses():
    summary = EvidenceCompressor().compress(
        [
            {"role": "user", "content": "Keep API backward compatible"},
            {"role": "assistant", "content": "Hypothesis: bounds are reversed"},
            {"role": "tool", "tool_call_id": "x", "content": json.dumps({"artifact_id": "evidence-id"})},
        ]
    )
    assert "Keep API backward compatible" in summary["constraints"]
    assert "Hypothesis: bounds are reversed" in summary["unverified_hypotheses"]
    assert "evidence-id" in summary["evidence"][0]["observation"]


def test_external_network_is_blocked():
    with socket.socket() as sock, pytest.raises(AssertionError, match="external network"):
        sock.connect(("203.0.113.1", 443))


def test_symlink_escape(tmp_path):
    try:
        (tmp_path / "link").symlink_to(tmp_path.parent, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation not permitted on this Windows account")
    with pytest.raises(PolicyError):
        safe_path(tmp_path, "link/outside")


async def test_document_version_and_input_snapshot(app, demo):
    knowledge = app.state.platform.knowledge
    project = demo["project"]
    knowledge.add_document(
        project["id"], "docs/contract.md", "v1", "Bounds are inclusive; inverted bounds raise ValueError."
    )
    with pytest.raises(PolicyError, match="immutable"):
        knowledge.add_document(project["id"], "docs/contract.md", "v1", "changed contents")
    from repairlab.domain import TaskContract

    contract = TaskContract.model_validate(demo["issue"]["contract"])
    saved = app.state.platform.create_issue(contract)
    assert saved["contract"]["materials"][0]["version"] == "v1"
    knowledge.add_document(project["id"], "docs/contract.md", "v2", "A later document revision.")
    assert saved["contract"]["materials"][0]["content"].startswith("Bounds")
    with pytest.raises(PolicyError):
        knowledge.add_document(project["id"], "hidden/answers.md", "v1", "private")


async def test_global_budget_gate(app, demo):
    from repairlab.db import BudgetRow

    app.state.platform.submit(demo["issue"]["id"])
    lease = app.state.ledger.claim("budget-worker")
    with app.state.db.transaction() as session:
        pool = session.get(BudgetRow, "global")
        pool.spent = pool.limit_cny + 1
    with pytest.raises(RunStopped, match="global_budget_exhausted"):
        app.state.ledger.reserve(lease, "over-global-budget", [], "scripted")


@pytest.mark.parametrize("control", ["cancel", "deadline"])
async def test_pending_model_obeys_cancel_and_deadline(app, demo, control):
    import asyncio
    import time

    from repairlab.models import ScriptedModelAdapter

    run = app.state.platform.submit(demo["issue"]["id"])
    lease = app.state.ledger.claim("pending-model")
    task = asyncio.create_task(
        app.state.harness._await_model(lease, ScriptedModelAdapter([{"finish": True}], delay=30), [], 0)
    )
    await asyncio.sleep(0)
    if control == "cancel":
        app.state.ledger.control(run["id"], "cancel")
    else:
        with app.state.db.transaction() as session:
            session.get(RunRow, run["id"]).started_at = time.time() - 1201
    with pytest.raises(RunStopped, match="cancelled|deadline_exceeded"):
        await asyncio.wait_for(task, 2)
