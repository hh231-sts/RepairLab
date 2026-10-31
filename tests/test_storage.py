import shutil
import subprocess
import time

import pytest
from repairlab.db import AgentRow, RunRow
from repairlab.domain import ToolCall
from repairlab.scripts import FIXED_CODE
from repairlab.storage import PolicyError, Store, atomic_write


def test_byte_exact_snapshot_binary_and_no_newline_patch(tmp_path):
    root = tmp_path / "repos"
    repo = root / "fixture"
    (repo / "src").mkdir(parents=True)
    (repo / "src/value.txt").write_bytes(b"original\r\n")
    (repo / "image.png").write_bytes(b"\x89PNG\0\xff")
    data = tmp_path / "data"
    (data / "snapshots").mkdir(parents=True)
    store = Store(data)
    _, sha = store.snapshot(repo, root, "fixture-v1")
    store.verify_snapshot(sha)
    baseline = data / "snapshots" / sha
    assert (baseline / "image.png").read_bytes() == b"\x89PNG\0\xff"
    assert (baseline / "src/value.txt").read_bytes() == b"original\r\n"
    workspace = store.workspace("r", "a", sha)
    atomic_write(workspace / "src/value.txt", b"updated without newline")
    changes = store.changes(workspace, sha, ["src/"])
    target = tmp_path / "patched"
    store.materialize(target, sha, changes, ["src/"])
    assert (target / "src/value.txt").read_bytes() == b"updated without newline"
    fresh = tmp_path / "git-apply"
    shutil.copytree(baseline, fresh)
    patch = store.diff(sha, changes).encode()
    result = subprocess.run(["git", "apply", "-"], cwd=fresh, input=patch, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert (fresh / "src/value.txt").read_bytes() == b"updated without newline"
    atomic_write(baseline / "src/value.txt", b"tampered")
    with pytest.raises(PolicyError, match="digest mismatch"):
        store.verify_snapshot(sha)


async def test_old_generation_cannot_mutate_takeover_workspace(app, demo):
    run = app.state.platform.submit(demo["issue"]["id"])
    old = app.state.ledger.claim("old")
    agent_id = run["id"] + "-supervisor"
    call = ToolCall(
        id="write", name="write_file", arguments={"path": "src/calculator.py", "content": FIXED_CODE}
    )
    await app.state.tools.execute(old, agent_id, 0, 0, call)
    with app.state.db.transaction() as session:
        row = session.get(RunRow, run["id"])
        old_workspace = app.state.tools.workspace(session, row, session.get(AgentRow, agent_id))
        row.lease_until = time.time() - 1
    new = app.state.ledger.claim("replacement")
    with app.state.db.transaction() as session:
        current = app.state.tools.workspace(
            session, session.get(RunRow, run["id"]), session.get(AgentRow, agent_id)
        )
    assert current != old_workspace
    atomic_write(old_workspace / "src/calculator.py", b"late stale process mutation")
    assert (current / "src/calculator.py").read_text("utf-8") == FIXED_CODE
    assert new.epoch > old.epoch
