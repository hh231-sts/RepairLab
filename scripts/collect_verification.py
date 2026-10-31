"""Archive executed test results and dependency versions; never manufacture missing results."""

import importlib.metadata
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from repairlab.domain import digest

root = Path(__file__).resolve().parents[1]
destination = root / "docs/verification"
destination.mkdir(parents=True, exist_ok=True)
results = {}
for name, source in [
    ("unit", "unit-results.xml"),
    ("integration", "integration-acceptance.xml"),
]:
    path = root / ".cache" / source
    tree = ET.parse(path)
    suites = list(tree.getroot().iter("testsuite"))
    summary = {
        key: sum(int(s.attrib.get(key, 0)) for s in suites)
        for key in ("tests", "failures", "errors", "skipped")
    }
    summary["passed"] = summary["tests"] - summary["failures"] - summary["errors"] - summary["skipped"]
    if summary["failures"] or summary["errors"]:
        raise RuntimeError(f"cannot archive as passed: {name} {summary}")
    shutil.copyfile(path, destination / source)
    results[name] = summary
frontend_path = root / "frontend/test-results/results.json"
frontend = json.loads(frontend_path.read_text("utf-8"))
if frontend["stats"]["unexpected"] or frontend["stats"]["flaky"]:
    raise RuntimeError("frontend has failed or flaky tests")
shutil.copyfile(frontend_path, destination / "e2e-results.json")
results["e2e"] = frontend["stats"]
for name in [
    "network-audit-unit.json",
    "network-audit-integration-acceptance.json",
    "network-audit-integration-extra-pass.json",
]:
    data = json.loads((root / ".cache" / name).read_text("utf-8"))
    if data["real_model_http_attempts"]:
        raise RuntimeError("unexpected real model HTTP attempt")
    shutil.copyfile(root / ".cache" / name, destination / name)
for name in ["overview.png", "workspace.png", "mobile.png", "projects.png"]:
    path = root / "frontend/test-results" / name
    if path.exists():
        shutil.copyfile(path, destination / name)
report = {
    "captured_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
    "python": sys.version,
    "dependencies": {
        name: importlib.metadata.version(name)
        for name in [
            "fastapi",
            "pydantic",
            "sqlalchemy",
            "psycopg",
            "langgraph",
            "langgraph-checkpoint-postgres",
            "mcp",
            "pgvector",
            "pytest",
        ]
    },
    "lock_hashes": {
        name: digest((root / name).read_bytes()) for name in ["uv.lock", "frontend/package-lock.json"]
    },
    "tests": results,
    "real_model_calls": 0,
    "embedding_weights_loaded": False,
    "real_benchmark_tasks_admitted": 0,
    "formal_model_experiments_completed": 0,
    "limits": [
        "Windows symlink creation unavailable; one test skipped",
        "WSL user-distribution startup not executed",
        "Harbor CLI not executed",
        "Real model and E5 protocol/quality validation deferred",
    ],
}
(destination / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), "utf-8")
print(json.dumps(report["tests"], ensure_ascii=False))
