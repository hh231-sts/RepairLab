"""Offline, manifest-driven benchmark import and real-container admission preflight."""

import json
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from .domain import TaskContract, digest
from .storage import PolicyError, atomic_write, safe_path

REPOSITORIES = {"pytest-dev/pytest", "sphinx-doc/sphinx", "sympy/sympy"}


async def build_environment(platform, package_path: str, sandbox):
    package = Path(package_path).resolve()
    allowed = [
        platform.settings.task_root.resolve(),
        (platform.settings.data_root / "task_imports").resolve(),
    ]
    if (
        not any(package.is_relative_to(root) for root in allowed)
        or not (package / "environment/Dockerfile").is_file()
    ):
        raise PolicyError("environment builds require an admin-owned task package")
    manifest = {
        p.relative_to(package / "environment").as_posix(): digest(p.read_bytes())
        for p in (package / "environment").rglob("*")
        if p.is_file()
    }
    image = "repairlab-task:" + digest(manifest)[:24]
    await sandbox.command("build", "-t", image, str(package / "environment"), timeout=300)
    result = {"image": image, "image_hash": await sandbox.image_hash(image), "recipe_hash": digest(manifest)}
    atomic_write(package / "build-result.json", json.dumps(result, indent=2).encode())
    return result


def freeze_selection(selection_path: str):
    path = Path(selection_path)
    selection = json.loads(path.read_text("utf-8"))
    admitted, excluded, seen = [], list(selection["exclusions"]), set()
    for candidate in selection["candidates"]:
        manifest_path = Path(candidate["manifest"])
        preflight_path = manifest_path.parent / "preflight.json"
        if not preflight_path.exists() or not (result := json.loads(preflight_path.read_text("utf-8"))).get(
            "admitted"
        ):
            excluded.append(
                {"instance_id": candidate["instance_id"], "reason": "preflight_missing_or_failed"}
            )
            continue
        if candidate["instance_id"] in seen:
            continue
        seen.add(candidate["instance_id"])
        manifest = json.loads(manifest_path.read_text("utf-8"))
        admitted.append(
            {
                **candidate,
                "created_at": manifest["created_at"],
                "issue_id": result["issue"]["id"],
                "preflight_hash": digest(preflight_path.read_bytes()),
                "environment_hash": result["environment_hash"],
            }
        )
    splits: dict[str, list[dict]] = {"development": [], "regression": [], "final": []}
    for repo in sorted(REPOSITORIES):
        items = sorted(
            [x for x in admitted if x["repo"] == repo], key=lambda x: (x["created_at"], x["instance_id"])
        )
        if len(items) != 12:
            raise PolicyError(
                f"freeze requires 12 preflight-admitted tasks per repository: {repo} has {len(items)}"
            )
        splits["development"] += items[:6]
        splits["regression"] += items[6:9]
        splits["final"] += items[9:12]
    frozen = {
        "dataset_revision": selection["dataset_revision"],
        "splits": splits,
        "exclusions": excluded,
        "selection_hash": digest(path.read_bytes()),
        "formal_runs_completed": 0,
    }
    atomic_write(path.parent / "frozen.json", json.dumps(frozen, indent=2).encode())
    return frozen


def apply_unified(folder: Path, patch: str):
    # Trusted dataset/admin patch only; git apply rejects paths outside this temporary checkout.
    # Reject traversal explicitly as well as relying on git's default safe-path checks.
    for name in re.findall(r"^(?:\+\+\+ b/|--- a/)(.+)$", patch, re.M):
        safe_path(folder, name)
    result = subprocess.run(
        ["git", "apply", "--check", "-"], cwd=folder, input=patch.encode("utf-8"), capture_output=True
    )
    if result.returncode:
        raise PolicyError("dataset patch cannot be applied: " + result.stderr.decode(errors="replace")[:1000])
    subprocess.run(
        ["git", "apply", "-"], cwd=folder, input=patch.encode("utf-8"), check=True, capture_output=True
    )


def import_swebench(platform, manifest_path: str, revision: str):
    """Import fixed local rows; no downloads, model calls, or assumed preflight success.

    Manifest: {dataset_sha256, rows:[{instance:<official row>, repository:<local path>,
    image:<prebuilt pinned image>, public_tests:[...], hidden_tests:[...]}]}.
    Environments and test paths are admin-reviewed; dependency recipes differ per historical task.
    """
    if not revision or not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise PolicyError("dataset revision must be a frozen 40-character SHA")
    raw = Path(manifest_path).read_bytes()
    manifest = json.loads(raw)
    records, exclusions, seen = [], [], set()
    rows = sorted(manifest["rows"], key=lambda x: (x["instance"]["created_at"], x["instance"]["instance_id"]))
    counts: dict[str, int] = {}
    output = platform.settings.data_root / "task_imports" / digest(raw)
    output.mkdir(parents=True, exist_ok=True)
    for row in rows:
        item = row["instance"]
        instance_id, repo = item["instance_id"], item["repo"]
        reason = None
        issue_key = (repo, item.get("problem_statement", "").strip())
        pr_key = (repo, item.get("patch", "").strip())
        instance_key = (repo, instance_id)
        if repo not in REPOSITORIES:
            reason = "repository_not_selected"
        elif instance_key in seen or issue_key in seen or pr_key in seen:
            reason = "duplicate_issue_or_patch"
        elif counts.get(repo, 0) >= 12:
            reason = "quota_reached_pending_preflight"
        if reason:
            exclusions.append({"instance_id": instance_id, "reason": reason})
            continue
        seen.update([instance_key, issue_key, pr_key])
        project = platform.register_project(
            repo + " @ " + item["base_commit"][:8], row["repository"], item["base_commit"]
        )
        package = output / re.sub(r"[^a-zA-Z0-9_-]", "_", instance_id)
        package.mkdir()
        base = platform.store.root / "snapshots" / project["snapshot_hash"]
        with tempfile.TemporaryDirectory() as tmp:
            repaired = Path(tmp) / "repo"
            shutil.copytree(base, repaired)
            apply_unified(repaired, item["patch"])
            allowed = row.get("allowed_paths") or sorted(
                {p.split("/")[0] + "/" for p in re.findall(r"^\+\+\+ b/(.+)$", item["patch"], re.M)}
            )
            changes = platform.store.changes(repaired, project["snapshot_hash"], allowed)
        # Hidden tests are kept as a complete test-patch overlay; never indexed or mounted to agents.
        verifier = package / "verifier"
        shutil.copytree(base, verifier)
        apply_unified(verifier, item["test_patch"])
        for test in row["hidden_tests"]:
            safe_path(verifier, test.split("::")[0])
        reference = package / "reference.json"
        atomic_write(reference, json.dumps(changes).encode())
        data = {
            "instance_id": instance_id,
            "dataset_revision": revision,
            "dataset_manifest_hash": digest(raw),
            "project": project,
            "image": row["image"],
            "public_tests": row["public_tests"],
            "hidden_tests": row["hidden_tests"],
            "allowed_paths": allowed,
            "verifier": str(verifier.resolve()),
            "reference": str(reference.resolve()),
            "problem_statement": item["problem_statement"],
            "created_at": item["created_at"],
            "source": "SWE-bench_Verified",
            "preflight": "not_run",
        }
        atomic_write(package / "manifest.json", json.dumps(data, indent=2).encode())
        # Harbor layout exports for an independent runner. Test overlay is applied after agent execution.
        atomic_write(package / "instruction.md", item["problem_statement"].encode())
        atomic_write(
            package / "task.toml",
            b'version = "1.0"\n[metadata]\ncategory = "code-repair"\n[agent]\ntimeout_sec = 1200\n[verifier]\ntimeout_sec = 300\n[environment]\ncpus = 1\nmemory_mb = 512\n',
        )
        atomic_write(
            package / "environment" / "Dockerfile",
            ("FROM " + row["image"] + "\nWORKDIR /workspace\nCOPY repo/ /workspace/\n").encode(),
        )
        shutil.copytree(base, package / "environment" / "repo")
        atomic_write(package / "solution" / "reference.patch", item["patch"].encode())
        atomic_write(
            package / "solution" / "solve.sh",
            b"#!/bin/sh\nset -eu\ncd /workspace\ngit apply /solution/reference.patch\n",
        )
        # JSON argv avoids shell interpolation of dataset paths.
        atomic_write(
            package / "tests" / "run.py",
            (
                "import json,subprocess,pathlib\n"
                + "p=subprocess.run("
                + repr(["python", "-m", "pytest", "-q", *row["hidden_tests"]])
                + ",cwd='/workspace')\n"
                + "pathlib.Path('/logs/verifier').mkdir(parents=True,exist_ok=True)\npathlib.Path('/logs/verifier/reward.txt').write_text('1' if p.returncode==0 else '0')\n"
            ).encode(),
        )
        atomic_write(
            package / "tests" / "test.sh",
            b"#!/bin/sh\nset -eu\ncp -R /tests/overlay/. /workspace/\npython /tests/run.py\n",
        )
        for p in verifier.rglob("*"):
            if p.is_file():
                relative = p.relative_to(verifier).as_posix()
                original = base / relative
                if not original.exists() or p.read_bytes() != original.read_bytes():
                    atomic_write(safe_path(package / "tests" / "overlay", relative), p.read_bytes())
        records.append(
            {
                "instance_id": instance_id,
                "repo": repo,
                "manifest": str(package / "manifest.json"),
                "preflight": "not_run",
            }
        )
        counts[repo] = counts.get(repo, 0) + 1
    report = {
        "dataset_revision": revision,
        "manifest_hash": digest(raw),
        "candidates": records,
        "exclusions": exclusions,
        "admitted": 0,
        "note": "No task admitted before independent preflight. Splits freeze only after 12 admitted tasks/repository.",
    }
    atomic_write(output / "selection.json", json.dumps(report, indent=2).encode())
    return report


async def _preflight(platform, manifest_path: str, sandbox):
    path = Path(manifest_path)
    manifest = json.loads(path.read_text("utf-8"))
    project, image = manifest["project"], manifest["image"]
    reference = json.loads(Path(manifest["reference"]).read_text("utf-8"))
    verifier_path = Path(manifest["verifier"])
    environment_hash = await sandbox.image_hash(image)
    verifier_manifest = {
        p.relative_to(verifier_path).as_posix(): digest(p.read_bytes())
        for p in verifier_path.rglob("*")
        if p.is_file()
    }
    verifier_hash = digest(verifier_manifest)
    results = []
    # Test-patch overlay is applied only inside independent scoring copies. Source files from
    # the overlay must not overwrite the submitted repair; only changed test files are copied.
    base = platform.store.root / "snapshots" / project["snapshot_hash"]
    test_overlay = {}
    for p in verifier_path.rglob("*"):
        if p.is_file():
            relative = p.relative_to(verifier_path).as_posix()
            original = base / relative
            if not original.exists() or p.read_bytes() != original.read_bytes():
                if any(
                    relative == s.rstrip("/") or relative.startswith(s) for s in manifest["allowed_paths"]
                ):
                    raise PolicyError("hidden test patch overlaps repair scope; review task manually")
                test_overlay[relative] = p.read_bytes()
    if not reference or not test_overlay:
        raise PolicyError("reference and hidden test patch must be nonempty")
    invalid = {
        next(iter(reference)): {
            **next(iter(reference.values())),
            "after": "raise RuntimeError('known invalid patch')\n",
        }
    }
    for label, changes, expected in [
        ("original", {}, False),
        ("empty", {}, False),
        ("invalid", invalid, False),
        ("reference", reference, True),
        ("reference_repeat", reference, True),
        ("original_repeat", {}, False),
    ]:
        with tempfile.TemporaryDirectory(dir=platform.store.root / "workspaces") as tmp:
            workspace = Path(tmp) / "repo"
            platform.store.materialize(
                workspace, project["snapshot_hash"], changes, manifest["allowed_paths"]
            )
            for name, data in test_overlay.items():
                atomic_write(safe_path(workspace, name), data)
            action = digest([manifest["instance_id"], label, environment_hash, verifier_hash])
            scored_paths = list(dict.fromkeys([*manifest["public_tests"], *manifest["hidden_tests"]]))
            result = await sandbox.test(workspace, environment_hash, scored_paths, action, 300)
            await sandbox.stop("repairlab-" + action[:40])
            passed = result["exit_code"] == 0
            results.append(
                {
                    "case": label,
                    "expected_pass": expected,
                    "passed": passed,
                    "matches": passed == expected,
                    "output": result,
                }
            )
    admitted = all(x["matches"] for x in results)
    report = {
        "admitted": admitted,
        "results": results,
        "environment_hash": environment_hash,
        "verifier_hash": verifier_hash,
    }
    if admitted:
        # Freeze only the changed tests. Runtime mounts tests separately after execution ends.
        verifier_id = digest([manifest["instance_id"], verifier_hash])
        target = platform.store.root / "verifiers" / verifier_id
        if not target.exists():
            target.mkdir()
            for name, data in test_overlay.items():
                atomic_write(safe_path(target, name), data)
        runtime_hash = digest(
            {
                p.relative_to(target).as_posix(): digest(p.read_bytes())
                for p in target.rglob("*")
                if p.is_file()
            }
        )
        contract = TaskContract(
            project_id=project["id"],
            title=manifest["instance_id"],
            description=manifest["problem_statement"],
            base_commit=project["commit"],
            snapshot_hash=project["snapshot_hash"],
            environment=environment_hash,
            allowed_paths=manifest["allowed_paths"],
            public_tests=manifest["public_tests"],
            source="swebench",
            source_id=manifest["instance_id"],
            verifier_id=verifier_id,
            versions={
                "harness": "0.1.0",
                "tools": "1",
                "environment": environment_hash,
                "verifier": runtime_hash,
                "dataset": manifest["dataset_revision"],
                "hidden_tests": json.dumps(manifest["hidden_tests"]),
            },
        )
        report["issue"] = platform.create_issue(contract)
    encoded = json.dumps(report, indent=2).encode()
    atomic_write(path.parent / f"preflight-{time.time_ns()}.json", encoded)
    atomic_write(path.parent / "preflight.json", encoded)
    return report


async def preflight(platform, manifest_path: str, sandbox):
    try:
        return await _preflight(platform, manifest_path, sandbox)
    except (RuntimeError, ValueError, OSError, KeyError) as exc:
        report = {"admitted": False, "results": [], "error": type(exc).__name__, "detail": str(exc)[:2000]}
        encoded = json.dumps(report, indent=2).encode()
        atomic_write(Path(manifest_path).parent / f"preflight-{time.time_ns()}.json", encoded)
        atomic_write(Path(manifest_path).parent / "preflight.json", encoded)
        return report
