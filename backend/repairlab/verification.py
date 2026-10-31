import json
import shutil
import tempfile
from pathlib import Path

from sqlalchemy import select

from .db import AgentRow, VerificationRow
from .domain import digest
from .ledger import emit
from .storage import PolicyError


class Verifier:
    def __init__(self, db, ledger, store, sandbox, settings):
        self.db, self.ledger, self.store, self.sandbox, self.settings = db, ledger, store, sandbox, settings

    async def verify(self, lease):
        self.ledger.safe_point(lease)
        with self.db.transaction() as session:
            run = self.ledger.fenced(session, lease)
            contract = self.ledger.contract(session, run)
            agent = session.get(AgentRow, run.id + "-supervisor")
            workspace = self.store.workspace(
                run.id, agent.id, contract.snapshot_hash, session, epoch=run.epoch
            )
            changes = self.store.changes(workspace, contract.snapshot_hash, contract.allowed_paths)
            patch_hash = digest(changes)
            run.patch_hash, run.status = patch_hash, "verifying"
            patch = self.store.put(
                session,
                run.id,
                agent.id,
                "patch",
                self.store.diff(contract.snapshot_hash, changes).encode(),
                {"patch_hash": patch_hash},
            )
            self.store.put(
                session,
                run.id,
                agent.id,
                "patch_manifest",
                json.dumps(changes).encode(),
                {"patch_hash": patch_hash},
            )
            emit(session, run, "verification.started", {"patch_hash": patch_hash, "patch_artifact": patch.id})
        if not changes:
            return await self._record(lease, contract, patch_hash, False, "empty_patch", "", "", {})
        if not contract.verifier_id:
            return await self._record(lease, contract, patch_hash, False, "verifier_unavailable", "", "", {})
        # Verifier packages are trusted admin imports outside all agent snapshots and tool paths.
        verifier_path = (self.store.root / "verifiers" / contract.verifier_id).resolve()
        if (
            not verifier_path.is_relative_to((self.store.root / "verifiers").resolve())
            or not verifier_path.is_dir()
        ):
            raise PolicyError("invalid verifier package")
        manifest = {
            p.relative_to(verifier_path).as_posix(): digest(p.read_bytes())
            for p in verifier_path.rglob("*")
            if p.is_file()
        }
        verifier_hash = digest(manifest)
        if verifier_hash != contract.versions.get("verifier"):
            return await self._record(
                lease, contract, patch_hash, False, "verifier_version_mismatch", "", verifier_hash, {}
            )
        environment_hash = await self.sandbox.image_hash(contract.environment)
        if environment_hash != contract.versions.get("environment"):
            return await self._record(
                lease,
                contract,
                patch_hash,
                False,
                "environment_version_mismatch",
                environment_hash,
                verifier_hash,
                {},
            )
        with self.db.sessions() as session:
            prior = session.scalar(
                select(VerificationRow).where(
                    VerificationRow.run_id == lease.run_id,
                    VerificationRow.patch_hash == patch_hash,
                    VerificationRow.verifier_hash == verifier_hash,
                    VerificationRow.environment_hash == environment_hash,
                )
            )
            if prior:
                return prior
        folder = Path(tempfile.mkdtemp(prefix="verify-", dir=self.store.root / "workspaces"))
        target = folder / "repo"
        try:
            self.store.materialize(target, contract.snapshot_hash, changes, contract.allowed_paths)
            paths = [*contract.public_tests, "/verifier"]
            mount = verifier_path
            if contract.source == "swebench":
                from .storage import atomic_write, safe_path

                for name in manifest:
                    atomic_write(safe_path(target, name), (verifier_path / name).read_bytes())
                paths = list(
                    dict.fromkeys([*contract.public_tests, *json.loads(contract.versions["hidden_tests"])])
                )
                mount = None
            action = digest([lease.run_id, patch_hash, verifier_hash, environment_hash])
            try:
                result = await self.sandbox.test(
                    target,
                    environment_hash,
                    paths,
                    action,
                    self.settings.tool_timeout,
                    verifier=mount,
                    cancelled=lambda: self.ledger.is_cancelled(lease),
                )
            finally:
                await self.sandbox.stop("repairlab-" + action[:40])
            return await self._record(
                lease,
                contract,
                patch_hash,
                result["exit_code"] == 0,
                "tests_passed" if result["exit_code"] == 0 else "tests_failed",
                environment_hash,
                verifier_hash,
                result,
            )
        finally:
            shutil.rmtree(folder)

    async def _record(
        self, lease, contract, patch_hash, passed, reason, environment_hash, verifier_hash, result
    ):
        with self.db.transaction() as session:
            run = self.ledger.fenced(session, lease)
            if run.patch_hash != patch_hash:
                raise PolicyError("stale verification refused")
            artifact = self.store.put(
                session,
                run.id,
                "independent-verifier",
                "verification",
                json.dumps(result).encode(),
                {"private_to_agent": True},
            )
            row = VerificationRow(
                run_id=run.id,
                patch_hash=patch_hash,
                snapshot_hash=contract.snapshot_hash,
                environment_hash=environment_hash,
                verifier_hash=verifier_hash,
                passed=passed,
                reason=reason,
                artifact_id=artifact.id,
            )
            session.add(row)
            session.flush()
            emit(
                session,
                run,
                "verification.result",
                {"id": row.id, "passed": passed, "reason": reason, "patch_hash": patch_hash},
            )
            return row
