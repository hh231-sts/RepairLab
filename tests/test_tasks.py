import difflib
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from repairlab.scripts import FIXED_CODE
from repairlab.storage import PolicyError
from repairlab.tasks import freeze_selection, import_swebench, preflight

from .conftest import ROOT


def synthetic_manifest(platform, tmp_path):
    """Synthetic import fixture; never described as a real SWE-bench admission."""
    root = tmp_path / "repositories"
    repo = root / "synthetic"
    shutil.copytree(ROOT / "fixtures/repos/calculator", repo)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@localhost",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-qm",
            "Synthetic fixture",
        ],
        check=True,
    )
    commit = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    before = (repo / "src/calculator.py").read_text("utf-8")
    patch = "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            FIXED_CODE.splitlines(keepends=True),
            fromfile="a/src/calculator.py",
            tofile="b/src/calculator.py",
        )
    )
    hidden = "import pytest\nfrom src.calculator import clamp\ndef test_regression():\n    with pytest.raises(ValueError):\n        clamp(0, 10, 2)\n"
    test_patch = "".join(
        difflib.unified_diff(
            [], hidden.splitlines(keepends=True), fromfile="/dev/null", tofile="b/tests/test_regression.py"
        )
    )
    instance = {
        "instance_id": "pytest-dev__pytest-synthetic-fixture",
        "repo": "pytest-dev/pytest",
        "base_commit": commit,
        "problem_statement": "SYNTHETIC TEST: reversed bounds raise ValueError",
        "patch": patch,
        "test_patch": test_patch,
        "created_at": "2020-01-01T00:00:00Z",
    }
    row = {
        "instance": instance,
        "repository": "synthetic",
        "image": platform.settings.sandbox_image,
        "public_tests": ["tests"],
        "hidden_tests": ["tests/test_regression.py"],
    }
    manifest_path = tmp_path / "synthetic-import.json"
    manifest_path.write_text(json.dumps({"rows": [row, row]}), "utf-8")
    platform.settings.repository_root = root
    return manifest_path


async def test_offline_import_preflight_and_insufficient_freeze(app, tmp_path):
    platform = app.state.platform
    path = synthetic_manifest(platform, tmp_path)
    selection = import_swebench(platform, str(path), "a" * 40)
    assert selection["admitted"] == 0 and len(selection["candidates"]) == 1
    assert selection["exclusions"][0]["reason"] == "duplicate_issue_or_patch"
    package_manifest = selection["candidates"][0]["manifest"]
    report = await preflight(platform, package_manifest, app.state.tools.sandbox)
    assert report["admitted"] and len(report["results"]) == 6
    assert report["issue"]["contract"]["versions"]["dataset"] == "a" * 40
    folder = Path(package_manifest).parent
    assert (folder / "task.toml").is_file() and (folder / "solution/solve.sh").is_file()
    selection_path = folder.parent / "selection.json"
    with pytest.raises(PolicyError, match="12"):
        freeze_selection(str(selection_path))
    assert not (folder.parent / "frozen.json").exists()


def test_dataset_revision_must_be_fixed(app, tmp_path):
    with pytest.raises(PolicyError, match="revision"):
        import_swebench(app.state.platform, "unused", "main")
