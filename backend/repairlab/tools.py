import json
from pathlib import Path

from opentelemetry import trace
from pydantic import Field
from sqlalchemy import select

from .db import AgentRow, ArtifactRow, ReceiptRow
from .domain import StrictModel, ToolCall, digest
from .ledger import LeaseLost, RunStopped, emit
from .mcp_client import RetrievalClient
from .storage import PolicyError, atomic_write, safe_path, within_scope


class ReadFile(StrictModel):
    path: str


class WriteFile(StrictModel):
    path: str
    content: str | None = Field(max_length=200000)


class RunTests(StrictModel):
    paths: list[str] = Field(min_length=1, max_length=20)


class Search(StrictModel):
    query: str = Field(min_length=1, max_length=2000)


class Note(StrictModel):
    text: str = Field(min_length=1, max_length=20000)


class Integrate(StrictModel):
    key: str


class ReadArtifact(StrictModel):
    artifact_id: str
    offset: int = Field(0, ge=0)
    length: int = Field(8000, gt=0, le=16000)


class Empty(StrictModel):
    pass


PARAMETERS: dict[str, type[StrictModel]] = {
    "read_file": ReadFile,
    "write_file": WriteFile,
    "run_tests": RunTests,
    "search": Search,
    "note": Note,
    "integrate": Integrate,
    "read_artifact": ReadArtifact,
    "list_files": Empty,
}


def tool_schemas(role="supervisor", strategy="adaptive", is_child=False):
    excluded = set()
    if role == "code_investigation" or (strategy == "parallel" and is_child):
        excluded.add("write_file")
    if role != "supervisor" or strategy in {"single", "parallel"}:
        excluded.add("integrate")
    schemas = [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": name.replace("_", " "),
                "parameters": model.model_json_schema(),
            },
        }
        for name, model in PARAMETERS.items()
        if name not in excluded
    ]
    from .domain import DelegationRequest

    if role == "supervisor" and strategy in {"adaptive", "parallel"}:
        schemas.append(
            {
                "type": "function",
                "function": {
                    "name": "delegate",
                    "description": "Evidence-based child request (supervisor only)",
                    "parameters": DelegationRequest.model_json_schema(),
                },
            }
        )
    return schemas


class ToolExecutor:
    def __init__(self, db, ledger, store, sandbox, knowledge, settings, retrieval=None):
        self.db, self.ledger, self.store = db, ledger, store
        self.sandbox, self.knowledge, self.settings = sandbox, knowledge, settings
        self.retrieval = retrieval or RetrievalClient(settings)
        self.tracer = trace.get_tracer("repairlab.tools")

    def workspace(self, session, run, agent):
        contract = self.ledger.contract(session, run)
        return self.store.workspace(run.id, agent.id, contract.snapshot_hash, session, epoch=run.epoch)

    def _plan(self, session, run, agent, call, workspace):
        contract = self.ledger.contract(session, run)
        if call.name not in PARAMETERS:
            raise PolicyError("unknown tool")
        arguments = PARAMETERS[call.name].model_validate(call.arguments).model_dump()
        scope = agent.request.get("scope", contract.allowed_paths)
        if call.name == "write_file":
            name = arguments["path"]
            if (
                agent.role == "code_investigation"
                or (run.strategy == "parallel" and agent.parent_id)
                or not within_scope(name, scope)
                or not within_scope(name, contract.allowed_paths)
            ):
                raise PolicyError("write outside assigned scope")
            path = safe_path(workspace, name)
            after = arguments["content"]
            return {
                "before": digest(path.read_bytes()) if path.exists() else None,
                "after": digest(after.encode()) if after is not None else None,
            }
        if call.name == "run_tests":
            for path in arguments["paths"]:
                safe_path(workspace, path.split("::")[0])
                if not any(path == p or path.startswith(p.rstrip("/") + "/") for p in contract.public_tests):
                    raise PolicyError("only public test paths are executable")
            return {"image": contract.environment}
        if call.name == "integrate":
            if agent.role != "supervisor":
                raise PolicyError("only supervisor integrates")
            child = session.scalar(
                select(AgentRow).where(AgentRow.run_id == run.id, AgentRow.key == arguments["key"])
            )
            if not child or child.status != "accepted" or child.role != "implementation":
                raise PolicyError("child patch not accepted")
            patch = session.scalar(
                select(ArtifactRow).where(
                    ArtifactRow.id.in_(child.artifacts), ArtifactRow.kind == "child_patch"
                )
            )
            if not patch:
                raise PolicyError("accepted child has no patch artifact")
            changes = json.loads(self.store.read(patch))
            for name, change in changes.items():
                path = safe_path(workspace, name)
                before = digest(path.read_bytes()) if path.exists() else None
                if not within_scope(name, contract.allowed_paths) or before != change["before"]:
                    raise PolicyError("integration conflict or scope violation")
            return {"changes": changes, "source_artifact": patch.id}
        return {}

    def _mutate(self, workspace: Path, name: str, content: str | None, plan: dict):
        path = safe_path(workspace, name)
        current = digest(path.read_bytes()) if path.exists() else None
        after = digest(content.encode()) if content is not None else None
        if current == after:
            return {"reconciled": True, "path": name, "sha256": after}
        if current != plan["before"]:
            raise PolicyError("uncertain write conflicts with current file; manual reconciliation required")
        if content is None:
            path.unlink(missing_ok=True)
        else:
            atomic_write(path, content.encode())
        return {"path": name, "sha256": after}

    async def execute(self, lease, agent_id: str, cursor: int, index: int, call: ToolCall):
        key = digest([lease.run_id, agent_id, cursor, index, call.model_dump()])
        self.ledger.safe_point(lease)
        with self.db.transaction() as session:
            run = self.ledger.fenced(session, lease)
            agent = session.get(AgentRow, agent_id)
            workspace = self.workspace(session, run, agent)
            receipt = session.get(ReceiptRow, key)
            if receipt and receipt.status in {"succeeded", "failed"}:
                return receipt.result
            if not receipt:
                try:
                    plan = self._plan(session, run, agent, call, workspace)
                except (ValueError, KeyError) as exc:
                    receipt = ReceiptRow(
                        id=key,
                        run_id=run.id,
                        agent_id=agent_id,
                        epoch=lease.epoch,
                        name=call.name,
                        arguments=call.arguments,
                        status="failed",
                        result={"error": "policy_or_parameters", "detail": str(exc)[:2000]},
                    )
                    session.add(receipt)
                    emit(session, run, "tool.rejected", {"receipt_id": key, "error": receipt.result})
                    return receipt.result
                receipt = ReceiptRow(
                    id=key,
                    run_id=run.id,
                    agent_id=agent_id,
                    epoch=lease.epoch,
                    name=call.name,
                    arguments=call.arguments,
                    plan=plan,
                    status="intent",
                )
                session.add(receipt)
                emit(
                    session, run, "tool.intent", {"receipt_id": key, "agent_id": agent_id, "name": call.name}
                )
            plan = {**receipt.plan, "_intent_epoch": receipt.epoch}
            contract = self.ledger.contract(session, run)
        # The durable intent above commits before any action starts.
        try:
            with self.tracer.start_as_current_span(
                call.name, attributes={"run_id": lease.run_id, "agent_id": agent_id, "receipt_id": key}
            ):
                result = await self._perform(lease, agent_id, call, key, workspace, contract, plan)
            with self.db.transaction() as session:
                run = self.ledger.fenced(session, lease)
                receipt = session.get(ReceiptRow, key)
                payload = json.dumps(result, ensure_ascii=False).encode()
                artifact = self.store.put(
                    session,
                    run.id,
                    agent_id,
                    "test_output" if call.name == "run_tests" else call.name,
                    payload,
                    {"receipt_id": key, "trust": "untrusted_tool_content"},
                )
                receipt.result = {
                    "artifact_id": artifact.id,
                    "preview": payload.decode()[:4000],
                    "truncated": len(payload) > 4000,
                    "error": result.get("error"),
                    "exit_code": result.get("exit_code"),
                }
                receipt.status = "failed" if result.get("error") else "succeeded"
                emit(session, run, "tool.result", {"receipt_id": key, "agent_id": agent_id, **receipt.result})
                return receipt.result
        except (LeaseLost, RunStopped):
            raise
        except Exception as exc:
            with self.db.transaction() as session:
                run = self.ledger.fenced(session, lease)
                receipt = session.get(ReceiptRow, key)
                receipt.status, receipt.result = (
                    "failed",
                    {"error": "tool_execution", "detail": str(exc)[:2000]},
                )
                emit(session, run, "tool.error", {"receipt_id": key, **receipt.result})
                return receipt.result

    async def _perform(self, lease, agent_id, call, key, workspace, contract, plan):
        a = call.arguments
        if call.name == "run_tests":
            return await self.sandbox.test(
                workspace,
                contract.environment,
                a["paths"],
                key,
                self.settings.tool_timeout,
                cancelled=lambda: self.ledger.is_cancelled(lease),
            )
        if call.name == "search":
            return {
                "matches": await self.retrieval.search(contract.project_id, contract.base_commit, a["query"]),
                "transport": "mcp-stdio",
            }
        with self.db.transaction() as session:
            run = self.ledger.fenced(session, lease)
            if run.control == "cancel":
                raise RunStopped("cancelled")
            # Mutations and fence are under one row lock; takeover cannot overlap writes.
            if call.name == "write_file":
                run.patch_hash = None
                result = self._mutate(workspace, a["path"], a["content"], plan)
                if plan.get("_intent_epoch") != lease.epoch:
                    old = (
                        self.store.root / "workspaces" / run.id / agent_id / f"lease-{plan['_intent_epoch']}"
                    )
                    previous = safe_path(old, a["path"])
                    previous_hash = digest(previous.read_bytes()) if previous.exists() else None
                    result.update(
                        {
                            "recovery": "isolated_generation",
                            "previous_generation_hash": previous_hash,
                            "reconciled": previous_hash == plan.get("after"),
                        }
                    )
                return result
            if call.name == "integrate":
                outputs = []
                for name, change in plan["changes"].items():
                    outputs.append(self._mutate(workspace, name, change["after"], change))
                run.patch_hash = None
                return {"integrated": outputs, "source_artifact": plan["source_artifact"]}
            if call.name == "read_file":
                path = safe_path(workspace, a["path"])
                if path.stat().st_size > 2_000_000:
                    raise PolicyError("file exceeds read limit")
                return {"path": a["path"], "content": path.read_text("utf-8"), "commit": contract.base_commit}
            if call.name == "list_files":
                return {
                    "paths": [
                        p.relative_to(workspace).as_posix() for p in workspace.rglob("*") if p.is_file()
                    ][:5000]
                }
            if call.name == "note":
                return {"note": a["text"], "trust": "unverified_agent_claim"}
            if call.name == "read_artifact":
                artifact = session.get(ArtifactRow, a["artifact_id"])
                if (
                    not artifact
                    or artifact.run_id != run.id
                    or artifact.kind in {"verification", "reference", "hidden"}
                ):
                    raise PolicyError("artifact unavailable to agent")
                data = self.store.read(artifact)
                offset, length = a.get("offset", 0), a.get("length", 8000)
                return {
                    "content": data[offset : offset + length].decode(errors="replace"),
                    "total_bytes": len(data),
                    "offset": offset,
                }
        raise PolicyError("unimplemented tool")
