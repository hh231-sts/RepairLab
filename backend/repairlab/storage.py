import difflib
import fnmatch
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path, PurePosixPath

from sqlalchemy import select

from .db import ArtifactRow
from .domain import digest


class PolicyError(ValueError):
    pass


SECRET_PARTS = {".git", ".ssh", ".aws", ".codex", ".agents", "node_modules", "__pycache__", ".venv"}


def relative_path(value: str) -> str:
    p = PurePosixPath(value)
    if (
        not value
        or p.is_absolute()
        or "\\" in value
        or ":" in value
        or any(x in {"..", "."} for x in value.split("/"))
    ):
        raise PolicyError("path must be a normalized relative POSIX path")
    if any(x.lower() in SECRET_PARTS or x.lower().startswith(".env") for x in p.parts):
        raise PolicyError("secret or control directory is not accessible")
    if any(
        fnmatch.fnmatch(p.name.lower(), pattern)
        for pattern in ("*.pem", "*.key", "*credentials*", "*secret*")
    ):
        raise PolicyError("secret file is not accessible")
    return str(p)


def safe_path(root: Path, value: str) -> Path:
    relative_path(value)
    root = root.resolve()
    path = root / value
    for part in [path, *path.parents]:
        if part == root:
            break
        if part.is_symlink():
            raise PolicyError("symlinks are forbidden")
    if not path.resolve().is_relative_to(root):
        raise PolicyError("path escaped workspace")
    return path


def within_scope(path: str, scopes: list[str]) -> bool:
    relative_path(path)
    return any(path == s.rstrip("/") or (s.endswith("/") and path.startswith(s)) for s in scopes)


def atomic_write(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, prefix=".repairlab-")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, (path.stat().st_mode & 0o777) if path.exists() else 0o644)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class Store:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def put(self, session, run_id: str, agent_id: str, kind: str, data: bytes, metadata=None) -> ArtifactRow:
        sha = digest(data)
        path = self.root / "artifacts" / sha[:2] / sha
        if not path.exists():
            atomic_write(path, data)
        existing = session.scalar(
            select(ArtifactRow).where(
                ArtifactRow.run_id == run_id,
                ArtifactRow.agent_id == agent_id,
                ArtifactRow.kind == kind,
                ArtifactRow.sha256 == sha,
            )
        )
        if existing:
            return existing
        row = ArtifactRow(
            run_id=run_id,
            agent_id=agent_id,
            kind=kind,
            sha256=sha,
            size=len(data),
            metadata_json=metadata or {},
        )
        session.add(row)
        session.flush()
        return row

    def read(self, artifact: ArtifactRow) -> bytes:
        data = (self.root / "artifacts" / artifact.sha256[:2] / artifact.sha256).read_bytes()
        if digest(data) != artifact.sha256:
            raise PolicyError("artifact digest mismatch")
        return data

    def snapshot(self, repository: Path, allowed_root: Path, commit: str | None) -> tuple[str, str]:
        repo = repository.resolve()
        if not repo.is_relative_to(allowed_root.resolve()) or not repo.is_dir():
            raise PolicyError("repository must be under REPOSITORY_ROOT")
        files: dict[str, bytes] = {}
        modes: dict[str, int] = {}
        if (repo / ".git").exists():
            if not commit or not re.fullmatch(r"[a-fA-F0-9]{7,40}", commit):
                raise PolicyError("a fixed hexadecimal git commit is required")
            resolved = subprocess.run(
                ["git", "-C", str(repo), "rev-parse", "--verify", f"{commit}^{{commit}}"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            listing = subprocess.run(
                ["git", "-C", str(repo), "ls-tree", "-rz", resolved], check=True, capture_output=True
            ).stdout
            for item in listing.split(b"\0"):
                if not item:
                    continue
                meta, filename = item.split(b"\t", 1)
                name = filename.decode("utf-8")
                try:
                    relative_path(name)
                except PolicyError:
                    continue
                if meta.startswith(b"120000") or not meta.startswith(b"100"):
                    continue
                content = subprocess.run(
                    ["git", "-C", str(repo), "show", f"{resolved}:{name}"], check=True, capture_output=True
                ).stdout
                if len(content) > 20_000_000:
                    raise PolicyError("snapshot file exceeds 20 MB resource limit")
                files[name] = content
                modes[name] = 0o755 if meta.startswith(b"100755") else 0o644
            commit = resolved
        else:
            if commit not in (None, "fixture-v1"):
                raise PolicyError("non-git directories only support fixture-v1")
            for path in sorted(repo.rglob("*")):
                if not path.is_file() or path.is_symlink():
                    continue
                name = path.relative_to(repo).as_posix()
                try:
                    relative_path(name)
                except PolicyError:
                    continue
                if path.stat().st_size > 20_000_000:
                    raise PolicyError("snapshot file exceeds 20 MB resource limit")
                files[name] = path.read_bytes()
                modes[name] = 0o755 if path.stat().st_mode & 0o111 else 0o644
            commit = "fixture-v1"
        if not files:
            raise PolicyError("empty repository snapshot")
        if sum(map(len, files.values())) > 300_000_000:
            raise PolicyError("snapshot exceeds 300 MB resource limit")
        sha = digest({name: digest(content) for name, content in files.items()})
        folder = self.root / "snapshots" / sha
        if not folder.exists():
            staged = Path(tempfile.mkdtemp(prefix="snapshot-", dir=folder.parent))
            try:
                for name, content in files.items():
                    path = safe_path(staged, name)
                    atomic_write(path, content)
                    path.chmod(modes[name])
                try:
                    os.rename(staged, folder)
                except OSError:
                    if not folder.is_dir():
                        raise
                    self.verify_snapshot(sha)
            finally:
                if staged.exists():
                    shutil.rmtree(staged)
        return commit, sha

    def verify_snapshot(self, snapshot_hash):
        folder = self.root / "snapshots" / snapshot_hash
        manifest = {
            p.relative_to(folder).as_posix(): digest(p.read_bytes()) for p in folder.rglob("*") if p.is_file()
        }
        if not manifest or digest(manifest) != snapshot_hash:
            raise PolicyError("immutable repository snapshot digest mismatch")

    def workspace(self, run_id: str, agent_id: str, snapshot_hash: str, session=None, epoch=0) -> Path:
        # Old executors retain only their old generation; a lease takeover rebuilds from
        # confirmed receipts, so a disconnected process cannot mutate the new workspace.
        path = self.root / "workspaces" / run_id / agent_id / f"lease-{epoch}"
        if not path.exists():
            self.verify_snapshot(snapshot_hash)
            shutil.copytree(self.root / "snapshots" / snapshot_hash, path)
            if session is not None:
                from .db import ReceiptRow

                receipts = session.scalars(
                    select(ReceiptRow)
                    .where(
                        ReceiptRow.run_id == run_id,
                        ReceiptRow.agent_id == agent_id,
                        ReceiptRow.status == "succeeded",
                    )
                    .order_by(ReceiptRow.created_at, ReceiptRow.id)
                )
                for receipt in receipts:
                    changes = {}
                    if receipt.name == "write_file":
                        changes[receipt.arguments["path"]] = receipt.arguments["content"]
                    elif receipt.name == "integrate":
                        changes = {name: change["after"] for name, change in receipt.plan["changes"].items()}
                    for name, content in changes.items():
                        file_path = safe_path(path, name)
                        if content is None:
                            file_path.unlink(missing_ok=True)
                        else:
                            atomic_write(file_path, content.encode())
        return path

    def changes(self, workspace: Path, snapshot_hash: str, allowed_paths: list[str]) -> dict:
        base = self.root / "snapshots" / snapshot_hash
        names = {p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file()}
        names |= {p.relative_to(workspace).as_posix() for p in workspace.rglob("*") if p.is_file()}
        changes = {}
        for name in sorted(names):
            original = safe_path(base, name)
            current = safe_path(workspace, name)
            before = original.read_bytes() if original.exists() else None
            after = current.read_bytes() if current.exists() else None
            if before != after:
                if not within_scope(name, allowed_paths):
                    raise PolicyError(f"patch out of scope: {name}")
                changes[name] = {
                    "before": digest(before) if before is not None else None,
                    "after": after.decode("utf-8") if after is not None else None,
                }
        return changes

    def materialize(self, target: Path, snapshot_hash: str, changes: dict, allowed_paths: list[str]):
        self.verify_snapshot(snapshot_hash)
        shutil.copytree(self.root / "snapshots" / snapshot_hash, target)
        for name, change in changes.items():
            if not within_scope(name, allowed_paths):
                raise PolicyError("patch out of scope")
            path = safe_path(target, name)
            before = digest(path.read_bytes()) if path.exists() else None
            if before != change["before"]:
                raise PolicyError("patch base mismatch")
            if change["after"] is None:
                path.unlink()
            else:
                atomic_write(path, change["after"].encode())

    def diff(self, snapshot_hash: str, changes: dict) -> str:
        result: list[str] = []
        for name, change in changes.items():
            base = safe_path(self.root / "snapshots" / snapshot_hash, name)
            before = base.read_bytes().decode("utf-8").splitlines(keepends=True) if base.exists() else []
            after = (change["after"] or "").splitlines(keepends=True)
            for line in difflib.unified_diff(before, after, fromfile=f"a/{name}", tofile=f"b/{name}"):
                result.append(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n")
        return "".join(result)

    def export_manifest(self, snapshot_hash: str) -> str:
        base = self.root / "snapshots" / snapshot_hash
        return json.dumps(
            {p.relative_to(base).as_posix(): digest(p.read_bytes()) for p in base.rglob("*") if p.is_file()},
            sort_keys=True,
        )
