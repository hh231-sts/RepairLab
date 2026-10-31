import shutil
import time
from typing import Any

from sqlalchemy import select, text

from .db import (
    AgentRow,
    ArtifactRow,
    DocumentRow,
    EventRow,
    ExperimentRow,
    IssueRow,
    ModelCallRow,
    ProjectRow,
    ReceiptRow,
    RunRow,
    SkillRow,
    VerificationRow,
    row_dict,
)
from .domain import Experiment, InputMaterial, RunLimits, TaskContract, digest
from .ledger import emit
from .scripts import script
from .storage import PolicyError


class Platform:
    def __init__(self, db, settings, store, knowledge, ledger):
        self.db, self.settings, self.store, self.knowledge, self.ledger = (
            db,
            settings,
            store,
            knowledge,
            ledger,
        )

    def register_project(self, name: str, repository: str, commit: str | None):
        path = (self.settings.repository_root / repository).resolve()
        base_commit, snapshot_hash = self.store.snapshot(path, self.settings.repository_root, commit)
        with self.db.transaction() as session:
            project = ProjectRow(
                name=name, repository=repository, commit=base_commit, snapshot_hash=snapshot_hash
            )
            session.add(project)
            session.flush()
            result = row_dict(project)
        self.knowledge.index(result["id"])
        return result

    def create_issue(self, contract: TaskContract):
        with self.db.transaction() as session:
            project = session.get(ProjectRow, contract.project_id)
            if (
                not project
                or contract.base_commit != project.commit
                or contract.snapshot_hash != project.snapshot_hash
            ):
                raise PolicyError("contract must bind the registered immutable repository version")
            from .storage import relative_path

            for scope in [*contract.allowed_paths, *contract.public_tests]:
                relative_path(scope.rstrip("/"))
            documents = list(
                session.scalars(
                    select(DocumentRow).where(
                        DocumentRow.project_id == project.id, DocumentRow.origin == "material"
                    )
                )
            )
            contract = contract.model_copy(
                update={
                    "materials": [
                        *contract.materials,
                        *[
                            InputMaterial(
                                source=d.path,
                                version=d.source_version,
                                content=d.content,
                                sha256=digest(d.content.encode()),
                            )
                            for d in documents
                        ],
                    ]
                }
            )
            row = IssueRow(
                project_id=project.id,
                contract=contract.model_dump(),
                contract_hash=digest(contract.model_dump()),
            )
            session.add(row)
            session.flush()
            return row_dict(row)

    def _create_run(
        self,
        session,
        issue_id: str,
        *,
        strategy="single",
        model_source="scripted",
        script_name="repair",
        retry_of=None,
        experiment_id=None,
        memory_snapshot=None,
        submission_key=None,
        limits=None,
    ):
        if strategy not in {"single", "parallel", "fixed", "adaptive"} or model_source not in {
            "scripted",
            "deepseek",
        }:
            raise PolicyError("invalid strategy/model source")
        if model_source != "scripted" and not self.settings.model_calls_enabled:
            raise PolicyError("model_disabled")
        if model_source != "scripted" and not self.settings.public_model_config()["model_ready"]:
            raise PolicyError(self.settings.public_model_config()["reason"])
        if model_source == "scripted":
            script(script_name)  # only trusted names; user cannot submit arbitrary scripts
        issue = session.get(IssueRow, issue_id)
        if not issue:
            raise KeyError(issue_id)
        contract = TaskContract.model_validate(issue.contract)
        effective_limits = None
        if limits is not None:
            effective_limits = RunLimits.model_validate(limits).model_dump()
            if any(value > getattr(contract, name) for name, value in effective_limits.items()):
                raise PolicyError("run limits must not exceed the immutable issue contract")
        if model_source == "scripted" and contract.source != "development_fixture":
            raise PolicyError("fixture scripts only run on development fixtures")
        skills = [row_dict(s) for s in session.scalars(select(SkillRow).where(SkillRow.active.is_(True)))]
        memory = (
            memory_snapshot
            if memory_snapshot is not None
            else self.knowledge.frozen_memories(session, contract.project_id, contract.base_commit)
        )
        row = RunRow(
            issue_id=issue_id,
            strategy=strategy,
            model_source=model_source,
            script=script_name,
            retry_of=retry_of,
            experiment_id=experiment_id,
            memory_snapshot=memory,
            submission_key=submission_key,
            versions={
                **contract.versions,
                "contract_hash": issue.contract_hash,
                "skills": skills,
                "model": self.settings.deepseek_model if model_source == "deepseek" else "script-v1",
                "price_snapshot": self.settings.price_snapshot,
                "limits": effective_limits,
            },
        )
        session.add(row)
        session.flush()
        emit(session, row, "run.queued", {"scripted_test": model_source == "scripted", "strategy": strategy})
        return row_dict(row)

    def submit(self, issue_id: str, *, submission_key=None, **kwargs):
        key = digest(submission_key) if submission_key else None
        with self.db.transaction() as session:
            if key:
                if self.db.engine.dialect.name == "postgresql":
                    session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": int(key[:15], 16)})
                existing = session.scalar(select(RunRow).where(RunRow.submission_key == key))
                if existing:
                    requested_limits = (
                        RunLimits.model_validate(kwargs["limits"]).model_dump()
                        if kwargs.get("limits")
                        else None
                    )
                    if existing.versions.get("limits") != requested_limits:
                        raise PolicyError("idempotency key reused for different limits")
                    if existing.issue_id != issue_id or any(
                        getattr(existing, field) != kwargs.get(arg, default)
                        for field, arg, default in [
                            ("strategy", "strategy", "single"),
                            ("model_source", "model_source", "scripted"),
                            ("script", "script_name", "repair"),
                        ]
                    ):
                        raise PolicyError("idempotency key reused for different input")
                    return row_dict(existing)
            return self._create_run(session, issue_id, submission_key=key, **kwargs)

    async def demo(self, sandbox):
        project = self.register_project("边界计算 · 开发夹具", "calculator", "fixture-v1")
        source = self.settings.task_root / "clamp" / "tests"
        verifier_hash = digest(
            {
                p.relative_to(source).as_posix(): digest(p.read_bytes())
                for p in source.rglob("*")
                if p.is_file()
            }
        )
        verifier_id = digest(["development-fixture", verifier_hash])
        target = self.store.root / "verifiers" / verifier_id
        if not target.exists():
            shutil.copytree(source, target)
        environment = self.settings.sandbox_image
        try:
            environment_hash = await sandbox.image_hash(environment)
        except RuntimeError:
            environment_hash = "unavailable-build-sandbox-image"
        contract = TaskContract(
            project_id=project["id"],
            title="clamp 未校验倒置边界",
            description="clamp(value, low, high) 应将数值限制在闭区间；当 low > high 时应抛出 ValueError。请定位问题、复现并修复，保留证据。",
            base_commit=project["commit"],
            snapshot_hash=project["snapshot_hash"],
            environment=environment,
            source="development_fixture",
            source_id="clamp-v1",
            verifier_id=verifier_id,
            versions={
                "harness": "0.1.0",
                "tools": "1",
                "verifier": verifier_hash,
                "environment": environment_hash,
            },
        )
        return {
            "project": project,
            "issue": self.create_issue(contract),
            "environment_available": not environment_hash.startswith("unavailable"),
        }

    def detail(self, run_id):
        with self.db.sessions() as session:
            run = session.get(RunRow, run_id)
            if not run:
                raise KeyError(run_id)
            result = row_dict(run)
            models: list[tuple[str, Any]] = [
                ("agents", AgentRow),
                ("receipts", ReceiptRow),
                ("artifacts", ArtifactRow),
                ("verifications", VerificationRow),
                ("model_calls", ModelCallRow),
            ]
            for name, model in models:
                result[name] = [
                    row_dict(x) for x in session.scalars(select(model).where(model.run_id == run_id))
                ]
            result["elapsed_seconds"] = (
                max(0, (run.ended_at or time.time()) - run.started_at) if run.started_at else 0
            )
            result["scripted_test"] = run.model_source == "scripted"
            return result

    def export(self, run_id):
        result = self.detail(run_id)
        with self.db.sessions() as session:
            result["events"] = [
                row_dict(e)
                for e in session.scalars(
                    select(EventRow).where(EventRow.run_id == run_id).order_by(EventRow.seq)
                )
            ]
            result["issue"] = row_dict(session.get(IssueRow, result["issue_id"]))
            result["artifact_content"] = {
                a.id: self.store.read(a).decode(errors="replace")
                for a in session.scalars(select(ArtifactRow).where(ArtifactRow.run_id == run_id))
            }
        return result

    def create_experiment(self, config: Experiment):
        if config.formal and config.model_source == "scripted":
            raise PolicyError("scripted tests cannot count as formal experiments")
        if config.model_source != "scripted" and not self.settings.model_calls_enabled:
            raise PolicyError("model_disabled")
        with self.db.transaction() as session:
            snapshots = []
            for issue_id in config.issue_ids:
                issue = session.get(IssueRow, issue_id)
                if not issue:
                    raise KeyError(issue_id)
                snapshots += self.knowledge.frozen_memories(
                    session, issue.project_id, issue.contract["base_commit"]
                )
            row = ExperimentRow(
                name=config.name, config=config.model_dump(), formal=config.formal, memory_snapshot=snapshots
            )
            session.add(row)
            session.flush()
            return row_dict(row)

    def launch_experiment(self, experiment_id):
        with self.db.transaction() as session:
            experiment = session.scalar(
                select(ExperimentRow).where(ExperimentRow.id == experiment_id).with_for_update()
            )
            if not experiment:
                raise KeyError(experiment_id)
            config = Experiment.model_validate(experiment.config)
            if experiment.launched:
                raise PolicyError("experiment already launched; reuse its immutable runs")
            runs = []
            for issue_id in config.issue_ids:
                for strategy in config.strategies:
                    for _ in range(config.repetitions):
                        runs.append(
                            self._create_run(
                                session,
                                issue_id,
                                strategy=strategy,
                                model_source=config.model_source,
                                script_name=config.script,
                                experiment_id=experiment_id,
                                memory_snapshot=experiment.memory_snapshot,
                            )
                        )
            experiment.launched = True
            return runs

    def experiment_report(self, experiment_id):
        with self.db.sessions() as session:
            experiment = session.get(ExperimentRow, experiment_id)
            if not experiment:
                raise KeyError(experiment_id)
            runs = [
                row_dict(r)
                for r in session.scalars(select(RunRow).where(RunRow.experiment_id == experiment_id))
            ]
        groups: dict[str, Any] = {}
        for run in runs:
            group = groups.setdefault(
                run["strategy"],
                {
                    "total": 0,
                    "completed": 0,
                    "succeeded": 0,
                    "cost_cny": 0.0,
                    "reserved_cny": 0.0,
                    "latency_seconds": [],
                    "failures": {},
                },
            )
            group["total"] += 1
            group["cost_cny"] += run["spent"]
            group["reserved_cny"] += run["reserved"]
            if run["ended_at"]:
                group["completed"] += 1
                group["latency_seconds"].append(
                    run["ended_at"] - run["started_at"] if run["started_at"] else 0
                )
            group["succeeded"] += int(run["status"] == "succeeded")
            if run["status"] == "failed":
                reason = run["terminal_reason"] or "unknown"
                group["failures"][reason] = group["failures"].get(reason, 0) + 1
        return {
            "experiment": row_dict(experiment),
            "scripted_test": experiment.config["model_source"] == "scripted",
            "formal_model_evidence": experiment.formal and experiment.config["model_source"] != "scripted",
            "groups": groups,
            "runs": runs,
        }
