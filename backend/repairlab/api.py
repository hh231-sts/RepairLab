import asyncio
import hmac
import json
import os
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import Field
from sqlalchemy import select

from .config import Settings
from .db import (
    ArtifactRow,
    Database,
    EventRow,
    ExperimentRow,
    IssueRow,
    MemoryRow,
    ProjectRow,
    RunRow,
    SkillRow,
    row_dict,
)
from .domain import Experiment, MemoryEntry, RunLimits, StrictModel, TaskContract, digest
from .harness import Harness
from .knowledge import DeterministicEmbedding, EmbeddingAdapter, Knowledge, seed_skills
from .ledger import Ledger, emit
from .observability import local_tracer
from .sandbox import DockerSandbox
from .service import Platform
from .storage import PolicyError, Store
from .tools import ToolExecutor
from .verification import Verifier


class ProjectInput(StrictModel):
    name: str = Field(min_length=1, max_length=200)
    repository: str
    commit: str | None = None


class RunInput(StrictModel):
    issue_id: str
    strategy: Literal["single", "parallel", "fixed", "adaptive"] = "single"
    model_source: Literal["scripted", "deepseek"] = "scripted"
    script: str = "repair"
    limits: RunLimits | None = None


class SkillInput(StrictModel):
    name: Literal["reproduce", "analyze", "repair", "verify"]
    content: str = Field(min_length=30, max_length=10000)


class ValidationInput(StrictModel):
    run_ids: list[str]


class InputMessage(StrictModel):
    content: str = Field(min_length=1, max_length=5000)


class DocumentInput(StrictModel):
    path: str = Field(min_length=1, max_length=300)
    version: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=100000)


def create_app(settings=None, *, sandbox=None, retrieval=None):
    settings = settings or Settings()
    os.environ["LANGSMITH_TRACING"] = "false"
    settings.prepare()
    db = Database(settings.database_url)
    store, sandbox = Store(settings.data_root), sandbox or DockerSandbox()
    ledger = Ledger(db, settings)
    knowledge = Knowledge(db, store, settings)
    platform = Platform(db, settings, store, knowledge, ledger)
    tools = ToolExecutor(db, ledger, store, sandbox, knowledge, settings, retrieval)
    provider, tools.tracer = local_tracer(settings.data_root)
    verifier = Verifier(db, ledger, store, sandbox, settings)
    harness = Harness(db, ledger, tools, verifier, knowledge, store, settings)

    @asynccontextmanager
    async def lifespan(app):
        # Schema changes are explicit migrations in PostgreSQL. SQLite is a developer fallback.
        if db.engine.dialect.name == "sqlite":
            db.create_schema()
        seed_skills(db)
        yield
        provider.shutdown()
        db.engine.dispose()

    app = FastAPI(title="RepairLab", version="0.1.0", lifespan=lifespan)
    app.state.db, app.state.platform, app.state.harness = db, platform, harness
    app.state.ledger, app.state.tools, app.state.settings = ledger, tools, settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.cors_origin],
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "Last-Event-ID", "Idempotency-Key"],
    )

    async def auth(request: Request):
        supplied = request.headers.get("Authorization", "").removeprefix("Bearer ")
        if not supplied or not hmac.compare_digest(supplied, settings.api_token):
            raise HTTPException(401, "local API token required")

    @app.exception_handler(PolicyError)
    async def policy_error(request, exc):
        return Response(json.dumps({"detail": str(exc)}), status_code=409, media_type="application/json")

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        return Response(
            json.dumps({"detail": "record not found"}), status_code=404, media_type="application/json"
        )

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return Response(json.dumps({"detail": str(exc)}), status_code=409, media_type="application/json")

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "model_calls_enabled": settings.model_calls_enabled,
            "embedding_enabled": settings.embedding_enabled and settings.model_calls_enabled,
            "default_source": settings.public_model_config()["default_source"],
        }

    @app.get("/api/environment", dependencies=[Depends(auth)])
    async def environment():
        try:
            image = await sandbox.image_hash(settings.sandbox_image)
            return {"docker": True, "image": image, "model_calls_enabled": settings.model_calls_enabled}
        except RuntimeError as exc:
            return {
                "docker": False,
                "detail": str(exc)[:1500],
                "model_calls_enabled": settings.model_calls_enabled,
            }

    @app.get("/api/config", dependencies=[Depends(auth)])
    def public_config():
        return settings.public_model_config()

    @app.post("/api/demo", dependencies=[Depends(auth)])
    async def demo():
        return await platform.demo(sandbox)

    @app.get("/api/projects", dependencies=[Depends(auth)])
    def projects():
        with db.sessions() as session:
            return [
                row_dict(r)
                for r in session.scalars(select(ProjectRow).order_by(ProjectRow.created_at.desc()))
            ]

    @app.post("/api/projects", dependencies=[Depends(auth)])
    def create_project(body: ProjectInput):
        return platform.register_project(body.name, body.repository, body.commit)

    @app.post("/api/projects/{project_id}/index", dependencies=[Depends(auth)])
    def index(project_id: str, vectors: Literal["disabled", "deterministic-test", "real"] = "disabled"):
        embedding = (
            DeterministicEmbedding()
            if vectors == "deterministic-test"
            else EmbeddingAdapter(settings)
            if vectors == "real"
            else None
        )
        return knowledge.index(project_id, embedding)

    @app.get("/api/projects/{project_id}/search", dependencies=[Depends(auth)])
    def search(
        project_id: str, query: str, vectors: Literal["disabled", "deterministic-test", "real"] = "disabled"
    ):
        with db.sessions() as session:
            project = session.get(ProjectRow, project_id)
            if not project:
                raise KeyError(project_id)
            embedding = (
                DeterministicEmbedding()
                if vectors == "deterministic-test"
                else EmbeddingAdapter(settings)
                if vectors == "real"
                else None
            )
            return knowledge.search(project_id, project.commit, query, embedding=embedding)

    @app.post("/api/projects/{project_id}/documents", dependencies=[Depends(auth)])
    def document(project_id: str, body: DocumentInput):
        return knowledge.add_document(project_id, body.path, body.version, body.content)

    @app.get("/api/issues", dependencies=[Depends(auth)])
    def issues():
        with db.sessions() as session:
            return [
                row_dict(r) for r in session.scalars(select(IssueRow).order_by(IssueRow.created_at.desc()))
            ]

    @app.post("/api/issues", dependencies=[Depends(auth)])
    def create_issue(body: TaskContract):
        return platform.create_issue(body)

    @app.post("/api/runs", dependencies=[Depends(auth)])
    def submit(body: RunInput, idempotency_key: str | None = Header(None)):
        return platform.submit(
            body.issue_id,
            strategy=body.strategy,
            model_source=body.model_source,
            script_name=body.script,
            submission_key=idempotency_key,
            limits=body.limits.model_dump() if body.limits else None,
        )

    @app.get("/api/runs", dependencies=[Depends(auth)])
    def runs():
        with db.sessions() as session:
            return [
                row_dict(r)
                for r in session.scalars(select(RunRow).order_by(RunRow.created_at.desc()).limit(500))
            ]

    @app.get("/api/runs/{run_id}", dependencies=[Depends(auth)])
    def run_detail(run_id: str):
        return platform.detail(run_id)

    @app.post("/api/runs/{run_id}/control/{action}", dependencies=[Depends(auth)])
    def control(run_id: str, action: Literal["pause", "resume", "cancel", "retry"]):
        if action == "retry":
            detail = platform.detail(run_id)
            if detail["status"] not in {"failed", "cancelled"}:
                raise PolicyError("only failed or cancelled runs can be retried")
            return platform.submit(
                detail["issue_id"],
                strategy=detail["strategy"],
                model_source=detail["model_source"],
                script_name=detail["script"],
                retry_of=run_id,
                limits=detail["versions"].get("limits"),
            )
        return row_dict(ledger.control(run_id, action))

    @app.post("/api/runs/{run_id}/input", dependencies=[Depends(auth)])
    def add_input(run_id: str, body: InputMessage):
        from .db import AgentRow

        with db.transaction() as session:
            run = session.scalar(select(RunRow).where(RunRow.id == run_id).with_for_update())
            if not run or run.status != "waiting_input":
                raise PolicyError("run must be waiting for input")
            agent = session.get(AgentRow, run_id + "-supervisor")
            if run.terminal_reason == "uncertain_model_call":
                raise PolicyError("uncertain paid call requires audit and a new run; retry is not automatic")
            agent.messages = [*agent.messages, {"role": "user", "content": body.content}]
            agent.pending, agent.cursor = None, agent.cursor + 1
            run.status, run.control, run.owner = "queued", None, None
            emit(session, run, "input.received", {"content": body.content})
        return {"accepted": True}

    @app.get("/api/runs/{run_id}/events", dependencies=[Depends(auth)])
    async def events(
        run_id: str,
        request: Request,
        after: int = 0,
        last_event_id: str | None = Header(None),
        follow: bool = True,
    ):
        platform.detail(run_id)
        try:
            cursor = max(after, int(last_event_id or 0))
        except ValueError as exc:
            raise HTTPException(400, "invalid Last-Event-ID") from exc

        async def stream():
            nonlocal cursor
            while not await request.is_disconnected():
                with db.sessions() as session:
                    batch = list(
                        session.scalars(
                            select(EventRow)
                            .where(EventRow.run_id == run_id, EventRow.seq > cursor)
                            .order_by(EventRow.seq)
                            .limit(200)
                        )
                    )
                    run = session.get(RunRow, run_id)
                for event in batch:
                    cursor = event.seq
                    yield f"id: {event.seq}\nevent: trace\ndata: {json.dumps(row_dict(event), ensure_ascii=False)}\n\n"
                if not follow or (
                    run and run.status in {"succeeded", "failed", "cancelled"} and len(batch) < 200
                ):
                    break
                yield ": keepalive\n\n"
                await asyncio.sleep(0.5)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/runs/{run_id}/export", dependencies=[Depends(auth)])
    def export(run_id: str):
        return Response(
            json.dumps(platform.export(run_id), ensure_ascii=False),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="run-{run_id}.json"'},
        )

    @app.get("/api/artifacts/{artifact_id}", dependencies=[Depends(auth)])
    def artifact(artifact_id: str):
        with db.sessions() as session:
            row = session.get(ArtifactRow, artifact_id)
            if not row:
                raise KeyError(artifact_id)
            return Response(
                store.read(row),
                media_type="text/plain; charset=utf-8",
                headers={"X-Content-SHA256": row.sha256},
            )

    @app.get("/api/memories", dependencies=[Depends(auth)])
    def memories():
        with db.sessions() as session:
            return [row_dict(r) for r in session.scalars(select(MemoryRow))]

    @app.post("/api/memories", dependencies=[Depends(auth)])
    def memory(body: MemoryEntry):
        return knowledge.create_memory(body)

    @app.post("/api/memories/{memory_id}/validate", dependencies=[Depends(auth)])
    def validate_memory(memory_id: str, body: ValidationInput):
        return knowledge.validate_memory(memory_id, body.run_ids)

    @app.post("/api/memories/{memory_id}/invalidate", dependencies=[Depends(auth)])
    def invalidate(memory_id: str):
        with db.transaction() as session:
            row = session.get(MemoryRow, memory_id)
            if not row:
                raise KeyError(memory_id)
            row.status, row.version = "invalid", row.version + 1
            return row_dict(row)

    @app.get("/api/skills", dependencies=[Depends(auth)])
    def skills():
        with db.sessions() as session:
            return [
                row_dict(r)
                for r in session.scalars(select(SkillRow).order_by(SkillRow.name, SkillRow.version))
            ]

    @app.post("/api/skills", dependencies=[Depends(auth)])
    def skill(body: SkillInput):
        if any(t in body.content for t in ("```", "diff --git", "def ", "reference.patch")):
            raise PolicyError("skills contain reusable procedures, not task answers")
        with db.transaction() as session:
            current = list(
                session.scalars(select(SkillRow).where(SkillRow.name == body.name).with_for_update())
            )
            version = max((s.version for s in current), default=0) + 1
            for row in current:
                row.active = False
            row = SkillRow(
                id=f"{body.name}:{version}",
                name=body.name,
                version=version,
                content=body.content,
                sha256=digest(body.content),
            )
            session.add(row)
            session.flush()
            return row_dict(row)

    @app.post("/api/skills/{skill_id}/invalidate", dependencies=[Depends(auth)])
    def invalidate_skill(skill_id: str):
        with db.transaction() as session:
            row = session.get(SkillRow, skill_id)
            if not row:
                raise KeyError(skill_id)
            row.active = False
            return row_dict(row)

    @app.get("/api/experiments", dependencies=[Depends(auth)])
    def experiments():
        with db.sessions() as session:
            return [row_dict(r) for r in session.scalars(select(ExperimentRow))]

    @app.post("/api/experiments", dependencies=[Depends(auth)])
    def experiment(body: Experiment):
        return platform.create_experiment(body)

    @app.post("/api/experiments/{experiment_id}/launch", dependencies=[Depends(auth)])
    def launch(experiment_id: str):
        return platform.launch_experiment(experiment_id)

    @app.get("/api/experiments/{experiment_id}/report", dependencies=[Depends(auth)])
    def report(experiment_id: str, download: bool = False):
        data = platform.experiment_report(experiment_id)
        return Response(
            json.dumps(data, ensure_ascii=False),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="experiment-{experiment_id}.json"'}
            if download
            else {},
        )

    return app
