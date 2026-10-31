import time
import uuid
from contextlib import contextmanager
from typing import Any

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Index, Integer, String, Text, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def uid() -> str:
    return uuid.uuid4().hex


class Base(DeclarativeBase):
    pass


class BudgetRow(Base):
    __tablename__ = "budget_pool"
    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    limit_cny: Mapped[float] = mapped_column(Float, default=2000)
    spent: Mapped[float] = mapped_column(Float, default=0)
    reserved: Mapped[float] = mapped_column(Float, default=0)


class ProjectRow(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(200))
    repository: Mapped[str] = mapped_column(Text)
    commit: Mapped[str] = mapped_column(String(100))
    snapshot_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class IssueRow(Base):
    __tablename__ = "issues"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    contract: Mapped[dict] = mapped_column(JSON)
    contract_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class RunRow(Base):
    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    issue_id: Mapped[str] = mapped_column(ForeignKey("issues.id"))
    submission_key: Mapped[str | None] = mapped_column(String(100), unique=True)
    retry_of: Mapped[str | None] = mapped_column(String(32))
    experiment_id: Mapped[str | None] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    control: Mapped[str | None] = mapped_column(String(16))
    terminal_reason: Mapped[str | None] = mapped_column(Text)
    model_source: Mapped[str] = mapped_column(String(24), default="scripted")
    strategy: Mapped[str] = mapped_column(String(24), default="single")
    script: Mapped[str] = mapped_column(String(100), default="repair")
    owner: Mapped[str | None] = mapped_column(String(100))
    epoch: Mapped[int] = mapped_column(Integer, default=0)
    lease_until: Mapped[float] = mapped_column(Float, default=0)
    started_at: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    ended_at: Mapped[float | None] = mapped_column(Float)
    calls: Mapped[int] = mapped_column(Integer, default=0)
    spent: Mapped[float] = mapped_column(Float, default=0)
    reserved: Mapped[float] = mapped_column(Float, default=0)
    patch_hash: Mapped[str | None] = mapped_column(String(64))
    versions: Mapped[dict] = mapped_column(JSON, default=dict)
    memory_snapshot: Mapped[list] = mapped_column(JSON, default=list)
    event_seq: Mapped[int] = mapped_column(Integer, default=0)


class AgentRow(Base):
    __tablename__ = "agents"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    parent_id: Mapped[str | None] = mapped_column(String(80))
    key: Mapped[str] = mapped_column(String(40))
    role: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(24), default="queued")
    request: Mapped[dict] = mapped_column(JSON, default=dict)
    cursor: Mapped[int] = mapped_column(Integer, default=0)
    messages: Mapped[list] = mapped_column(JSON, default=list)
    pending: Mapped[dict | None] = mapped_column(JSON)
    artifacts: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(Text, default="")


class ReceiptRow(Base):
    __tablename__ = "receipts"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"))
    epoch: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(60))
    arguments: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(24), default="intent")
    plan: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class ArtifactRow(Base):
    __tablename__ = "artifacts"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    agent_id: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(40))
    sha256: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(Integer)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class EventRow(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(80))
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    __table_args__ = (Index("event_run_seq", "run_id", "seq", unique=True),)


class VerificationRow(Base):
    __tablename__ = "verifications"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    patch_hash: Mapped[str] = mapped_column(String(64))
    snapshot_hash: Mapped[str] = mapped_column(String(64))
    environment_hash: Mapped[str] = mapped_column(String(100))
    verifier_hash: Mapped[str] = mapped_column(String(64))
    passed: Mapped[bool] = mapped_column(Boolean)
    reason: Mapped[str] = mapped_column(Text)
    artifact_id: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class MemoryRow(Base):
    __tablename__ = "memories"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(24), default="candidate")
    entry: Mapped[dict] = mapped_column(JSON)
    validation: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class SkillRow(Base):
    __tablename__ = "skills"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    version: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class DocumentRow(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    commit: Mapped[str] = mapped_column(String(100))
    source_version: Mapped[str] = mapped_column(String(100), default="")
    origin: Mapped[str] = mapped_column(String(24), default="repository")
    path: Mapped[str] = mapped_column(Text)
    line: Mapped[int] = mapped_column(Integer)
    symbol: Mapped[str | None] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    vector: Mapped[list | None] = mapped_column(JSON)
    vector_source: Mapped[str | None] = mapped_column(String(80))


class ExperimentRow(Base):
    __tablename__ = "experiments"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(200))
    config: Mapped[dict] = mapped_column(JSON)
    formal: Mapped[bool] = mapped_column(Boolean, default=False)
    launched: Mapped[bool] = mapped_column(Boolean, default=False)
    memory_snapshot: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class ModelCallRow(Base):
    __tablename__ = "model_calls"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    source: Mapped[str] = mapped_column(String(24))
    reserved: Mapped[float] = mapped_column(Float)
    actual: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(24))
    metadata_json: Mapped[dict] = mapped_column(JSON)


def row_dict(row: Any) -> dict:
    return {c.key: getattr(row, c.key) for c in row.__table__.columns}


class Database:
    def __init__(self, url: str):
        args = {"check_same_thread": False, "timeout": 30} if url.startswith("sqlite") else {}
        self.engine = create_engine(url, connect_args=args, pool_pre_ping=True)
        if url.startswith("sqlite"):

            @event.listens_for(self.engine, "connect")
            def sqlite_pragmas(conn, _):
                conn.execute("PRAGMA foreign_keys=ON")
                conn.execute("PRAGMA journal_mode=WAL")

        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    @contextmanager
    def transaction(self):
        with self.sessions.begin() as session:
            # Serialize dev-mode writes; PostgreSQL uses row locks / SKIP LOCKED.
            if self.engine.dialect.name == "sqlite":
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            yield session

    def create_schema(self):
        Base.metadata.create_all(self.engine)
