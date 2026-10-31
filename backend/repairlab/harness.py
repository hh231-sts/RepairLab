import asyncio
import json
from contextlib import asynccontextmanager
from typing import TypedDict

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from sqlalchemy import select

from .context import assemble
from .db import AgentRow, ArtifactRow, ModelCallRow, ReceiptRow, RunRow
from .domain import DelegationRequest, ModelReply, digest
from .ledger import LeaseLost, RunStopped, emit
from .models import ModelError, select_model
from .policy import planned_reply
from .scripts import script, supervisor_script
from .storage import PolicyError, within_scope
from .tools import tool_schemas


class GraphState(TypedDict):
    agent_id: str
    done: bool


class ThreadedPostgresSaver(BaseCheckpointSaver):
    """Sync psycopg bridge: works with Windows subprocess-capable Proactor loops."""

    def __init__(self, saver):
        super().__init__(serde=saver.serde)
        self.saver = saver

    async def aget_tuple(self, config):
        return await asyncio.to_thread(self.saver.get_tuple, config)

    async def alist(self, config, **kwargs):
        rows = await asyncio.to_thread(lambda: list(self.saver.list(config, **kwargs)))
        for row in rows:
            yield row

    async def aput(self, config, checkpoint, metadata, new_versions):
        return await asyncio.to_thread(self.saver.put, config, checkpoint, metadata, new_versions)

    async def aput_writes(self, config, writes, task_id, task_path=""):
        return await asyncio.to_thread(self.saver.put_writes, config, writes, task_id, task_path)

    async def adelete_thread(self, thread_id):
        return await asyncio.to_thread(self.saver.delete_thread, thread_id)


@asynccontextmanager
async def checkpointer(settings):
    if settings.database_url.startswith("postgresql"):
        from langgraph.checkpoint.postgres import PostgresSaver

        url = settings.database_url.replace("postgresql+psycopg://", "postgresql://")
        with PostgresSaver.from_conn_string(url) as saver:
            await asyncio.to_thread(saver.setup)
            yield ThreadedPostgresSaver(saver)
    else:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        async with AsyncSqliteSaver.from_conn_string(str(settings.data_root / "checkpoints.db")) as saver:
            yield saver


class Harness:
    def __init__(self, db, ledger, tools, verifier, knowledge, store, settings):
        self.db, self.ledger, self.tools, self.verifier = db, ledger, tools, verifier
        self.knowledge, self.store, self.settings = knowledge, store, settings
        self.child_slots = asyncio.Semaphore(2)

    async def run(self, lease):
        heartbeat = asyncio.create_task(self._heartbeat(lease))
        try:
            async with checkpointer(self.settings) as saver:
                await self._agent(lease, lease.run_id + "-supervisor", saver)
            self.ledger.safe_point(lease)
            with self.db.sessions() as session:
                agents = list(session.scalars(select(AgentRow).where(AgentRow.run_id == lease.run_id)))
                rejected = any(a.parent_id and a.status != "accepted" for a in agents)
                failures = session.scalar(
                    select(ReceiptRow)
                    .where(ReceiptRow.run_id == lease.run_id, ReceiptRow.status == "failed")
                    .limit(1)
                )
            if rejected or failures:
                self.ledger.end(lease, "failed", "delegation_rejected" if rejected else "tool_error")
                return
            verification = await self.verifier.verify(lease)
            self.ledger.safe_point(lease)
            with self.db.sessions() as session:
                run = session.get(RunRow, lease.run_id)
                if verification.patch_hash != run.patch_hash:
                    raise PolicyError("stale verification refused")
            self.ledger.end(lease, "succeeded" if verification.passed else "failed", verification.reason)
        except LeaseLost:
            # A stale executor cannot emit results, alter state or finish a run.
            return
        except RunStopped as exc:
            if str(exc) not in {"paused", "cancelled", "deadline_exceeded"}:
                try:
                    self.ledger.end(
                        lease, "waiting_input" if str(exc) == "uncertain_model_call" else "failed", str(exc)
                    )
                except (LeaseLost, RunStopped):
                    pass
        except Exception as exc:
            reason = (
                exc.category
                if isinstance(exc, ModelError)
                else (
                    "environment_unavailable"
                    if "docker" in str(exc).lower()
                    else type(exc).__name__ + ": " + str(exc)[:300]
                )
            )
            try:
                self.ledger.end(lease, "failed", reason)
            except (LeaseLost, RunStopped):
                pass
        finally:
            heartbeat.cancel()
            await asyncio.gather(heartbeat, return_exceptions=True)
            # Containers are kept while active/paused to allow reconciliation, then collected.
            with self.db.sessions() as session:
                run = session.get(RunRow, lease.run_id)
                terminal = run and run.status in {"succeeded", "failed", "cancelled"}
                ids = (
                    [
                        r.id
                        for r in session.scalars(
                            select(ReceiptRow).where(
                                ReceiptRow.run_id == lease.run_id, ReceiptRow.name == "run_tests"
                            )
                        )
                    ]
                    if terminal
                    else []
                )
            for key in ids:
                try:
                    await self.tools.sandbox.stop("repairlab-" + key[:40])
                except RuntimeError:
                    pass  # A daemon outage must not overwrite the durable terminal record.

    async def _heartbeat(self, lease):
        while True:
            await asyncio.sleep(self.settings.lease_seconds / 3)
            self.ledger.heartbeat(lease)

    async def _await_model(self, lease, adapter, messages, cursor, schemas=None):
        task = asyncio.create_task(
            adapter.complete(messages, schemas if schemas is not None else tool_schemas(), cursor=cursor)
        )
        try:
            while True:
                done, _ = await asyncio.wait({task}, timeout=0.2)
                if done:
                    return task.result()
                if self.ledger.is_cancelled(lease):
                    # Retain uncertain fee reservations; cancelling HTTP cannot prove no charge.
                    self.ledger.safe_point(lease)
                    raise RunStopped("model_interrupted")
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def _agent(self, lease, agent_id, saver):
        async def step(state):
            done = await self._step(lease, state["agent_id"], saver)
            return {"agent_id": state["agent_id"], "done": done}

        builder = StateGraph(GraphState)
        builder.add_node("durable_step", step)
        builder.add_edge(START, "durable_step")
        builder.add_conditional_edges("durable_step", lambda state: END if state["done"] else "durable_step")
        graph = builder.compile(checkpointer=saver)
        # The ledger is authoritative for side effects. A fresh invocation safely reconciles
        # a checkpoint that is behind the receipt commit, including a previous graph crash.
        await graph.ainvoke(
            {"agent_id": agent_id, "done": False},
            {"configurable": {"thread_id": agent_id}, "recursion_limit": 250},
        )

    async def _step(self, lease, agent_id, saver):
        self.ledger.safe_point(lease)
        with self.db.sessions() as session:
            run = session.get(RunRow, lease.run_id)
            agent = session.get(AgentRow, agent_id)
            if agent.status in {"completed", "accepted", "rejected", "cancelled"}:
                return True
            contract = self.ledger.contract(session, run)
            # Recheck current invalidation state even for a frozen snapshot.
            from .db import MemoryRow

            memories = [
                m
                for m in run.memory_snapshot
                if m["project_id"] == contract.project_id
                and contract.base_commit in m["entry"]["applicable_versions"]
                and (current := session.get(MemoryRow, m["id"]))
                and current.status == "validated"
            ]
            skills = run.versions.get("skills", [])
            messages = assemble(contract, agent.role, agent.messages, memories, skills, strategy=run.strategy)
            schemas = tool_schemas(
                role=agent.role, strategy=run.strategy, is_child=agent.parent_id is not None
            )
            pending, cursor = agent.pending, agent.cursor
            source, strategy, name, role = run.model_source, run.strategy, run.script, agent.role
            request = agent.request
        if not pending:
            replies = (
                []
                if source != "scripted"
                else (
                    supervisor_script(strategy, name)
                    if role == "supervisor"
                    else script(
                        request.get("script")
                        or {
                            "code_investigation": "investigate",
                            "reproduction": "reproduce",
                            "implementation": "implement",
                        }[role]
                    )
                )
            )
            planned = (
                planned_reply(strategy, cursor, contract)
                if source == "deepseek" and role == "supervisor"
                else None
            )
            call_id = None
            if planned:
                reply = planned.model_copy(update={"origin": "policy"})
            else:
                adapter = select_model(self.settings, source, replies)
                call_id = agent_id + ":" + str(cursor)
                self.ledger.reserve(lease, call_id, messages, source)
                try:
                    reply = await self._await_model(lease, adapter, messages, cursor, schemas)
                except ModelError as exc:
                    with self.db.transaction() as session:
                        run = self.ledger.fenced(session, lease)
                        self.ledger.settle_in_session(session, run, call_id, exc.usage)
                        call = session.get(ModelCallRow, call_id)
                        details = {"category": exc.category, "detail": str(exc), **exc.diagnostics}
                        call.metadata_json = {**call.metadata_json, "error": details}
                        call.status = "failed" if call.actual is not None else "failed_unknown_usage"
                        emit(
                            session,
                            run,
                            "model.error",
                            {"call_id": call_id, **details, "usage_available": exc.usage is not None},
                        )
                    raise
            with self.db.transaction() as session:
                run = self.ledger.fenced(session, lease)
                agent = session.get(AgentRow, agent_id)
                agent.pending = reply.model_dump()
                if call_id:
                    self.ledger.settle_in_session(session, run, call_id, reply.usage)
                emit(
                    session,
                    run,
                    "agent.reply",
                    {
                        "agent_id": agent_id,
                        "cursor": cursor,
                        "action": "delegate" if reply.delegations else "finish" if reply.finish else "tool",
                        "content": reply.content,
                        "scripted_test": source == "scripted",
                    },
                )
            pending = reply.model_dump()
        reply = ModelReply.model_validate(pending)
        results = []
        if reply.delegations:
            await self._delegate(lease, agent_id, reply.delegations, saver, strategy)
        elif reply.calls:
            index = 0
            while index < len(reply.calls):
                call = reply.calls[index]
                if call.name == "delegate":
                    batch = [(index, call)]
                    if index + 1 < len(reply.calls) and reply.calls[index + 1].name == "delegate":
                        batch.append((index + 1, reply.calls[index + 1]))
                    results.extend(
                        await self._delegate_calls(lease, agent_id, cursor, batch, saver, strategy)
                    )
                    index += len(batch)
                else:
                    results.append((call, await self.tools.execute(lease, agent_id, cursor, index, call)))
                    index += 1
        elif reply.waiting_input:
            self.ledger.end(lease, "waiting_input", "agent_requested_input")
            raise RunStopped("waiting_input")
        elif reply.finish and role != "supervisor":
            await self._finish_child(lease, agent_id)
        with self.db.transaction() as session:
            run = self.ledger.fenced(session, lease)
            agent = session.get(AgentRow, agent_id)
            history = list(agent.messages)
            if reply.calls and reply.origin == "policy":
                history.append(
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "fixed_policy_actions": [c.model_dump() for c in reply.calls],
                                "observations": [r for _, r in results],
                            }
                        ),
                    }
                )
            elif reply.calls:
                history.append(
                    reply.raw_message
                    or {
                        "role": "assistant",
                        "content": reply.content,
                        "tool_calls": [
                            {
                                "id": c.id,
                                "type": "function",
                                "function": {"name": c.name, "arguments": json.dumps(c.arguments)},
                            }
                            for c in reply.calls
                        ],
                    }
                )
                history += [
                    {"role": "tool", "tool_call_id": c.id, "content": json.dumps(r, ensure_ascii=False)}
                    for c, r in results
                ]
            elif reply.delegations:
                if reply.raw_message:
                    history.append(reply.raw_message)
                    history += [
                        {
                            "role": "tool",
                            "tool_call_id": c["id"],
                            "content": json.dumps({"delegation_status": "reviewed"}),
                        }
                        for c in reply.raw_message.get("tool_calls", [])
                    ]
                else:
                    history.append(
                        {
                            "role": "assistant",
                            "content": json.dumps({"delegated": [d.key for d in reply.delegations]}),
                        }
                    )
            else:
                history.append({"role": "assistant", "content": reply.content})
            agent.messages, agent.pending, agent.cursor = history, None, cursor + 1
            if reply.finish:
                agent.status = "completed" if role == "supervisor" else agent.status
                agent.summary = reply.content
            emit(
                session,
                run,
                "agent.progress",
                {"agent_id": agent_id, "cursor": agent.cursor, "done": reply.finish},
            )
        return reply.finish

    async def _delegate_calls(self, lease, agent_id, cursor, batch, saver, strategy):
        """Delegate tools have receipts and one matching response per original call ID."""
        results, pending = {}, []
        for index, call in batch:
            self.ledger.safe_point(lease)
            key = digest([lease.run_id, agent_id, cursor, index, call.model_dump()])
            with self.db.transaction() as session:
                run = self.ledger.fenced(session, lease)
                receipt = session.get(ReceiptRow, key)
                if receipt and receipt.status in {"succeeded", "rejected"}:
                    results[index] = receipt.result
                    continue
                if not receipt:
                    receipt = ReceiptRow(
                        id=key,
                        run_id=run.id,
                        agent_id=agent_id,
                        epoch=lease.epoch,
                        name="delegate",
                        arguments=call.arguments,
                        status="intent",
                        plan={},
                    )
                    session.add(receipt)
                    emit(
                        session,
                        run,
                        "tool.intent",
                        {"receipt_id": key, "agent_id": agent_id, "name": "delegate"},
                    )
                try:
                    request = DelegationRequest.model_validate(call.arguments)
                except ValueError:
                    receipt.status, receipt.result = (
                        "rejected",
                        {
                            "error": "delegation_parameters",
                            "detail": "Invalid structured delegation arguments",
                        },
                    )
                    results[index] = receipt.result
                    emit(session, run, "tool.rejected", {"receipt_id": key, **receipt.result})
                    continue
                pending.append((index, key, request))
        if pending:
            try:
                outcomes = await self._delegate(
                    lease,
                    agent_id,
                    [request for _, _, request in pending],
                    saver,
                    strategy,
                    append_context=False,
                )
                by_key = {outcome["key"]: outcome for outcome in outcomes}
                for index, _, request in pending:
                    results[index] = {"outcomes": [by_key[request.key]]}
                status = "succeeded"
            except PolicyError as exc:
                for index, _, _ in pending:
                    results[index] = {"error": "delegation_policy", "detail": str(exc)}
                status = "rejected"
            with self.db.transaction() as session:
                run = self.ledger.fenced(session, lease)
                for index, key, _ in pending:
                    receipt = session.get(ReceiptRow, key)
                    receipt.status, receipt.result = status, results[index]
                    emit(
                        session,
                        run,
                        "tool.result" if status == "succeeded" else "tool.rejected",
                        {"receipt_id": key, "agent_id": agent_id, **results[index]},
                    )
        return [(call, results[index]) for index, call in batch]

    async def _delegate(self, lease, parent_id, requests, saver, strategy, append_context=True):
        if parent_id != lease.run_id + "-supervisor" or strategy == "single":
            raise PolicyError("strategy or parent forbids delegation")
        if len(requests) > 2 or len({r.key for r in requests}) != len(requests):
            raise PolicyError("at most two distinct concurrent child tasks")
        with self.db.transaction() as session:
            run = self.ledger.fenced(session, lease)
            contract = self.ledger.contract(session, run)
            existing = list(
                session.scalars(
                    select(AgentRow).where(AgentRow.run_id == run.id, AgentRow.parent_id == parent_id)
                )
            )
            keys = {c.key for c in existing}
            if len(keys | {r.key for r in requests}) > 4:
                raise PolicyError("at most four distinct child tasks per run")
            for request in requests:
                if strategy == "parallel" and request.role == "implementation":
                    raise PolicyError("parallel investigation children are read-only investigators/testers")
                if strategy == "fixed" and request.key not in {
                    "investigation",
                    "reproduction",
                    "implementation",
                }:
                    raise PolicyError("fixed collaboration uses its frozen role plan")
                for evidence in request.evidence:
                    if evidence == "issue":
                        continue
                    accepted = next(
                        (c for c in existing if c.key == evidence and c.status == "accepted"), None
                    )
                    artifact = session.get(ArtifactRow, evidence)
                    if not accepted and (
                        not artifact or artifact.run_id != run.id or artifact.kind == "verification"
                    ):
                        raise PolicyError("delegation cites nonexistent or private evidence")
                for scope in request.scope:
                    # Children may read public tests but all writes remain bounded by contract.
                    if not within_scope(
                        scope.rstrip("/") + "/_scope",
                        [
                            s if s.endswith("/") else s + "/"
                            for s in [*contract.allowed_paths, *contract.public_tests]
                        ],
                    ):
                        raise PolicyError("child scope exceeds contract")
                if request.key not in keys:
                    child = AgentRow(
                        id=run.id + "-" + request.key,
                        run_id=run.id,
                        parent_id=parent_id,
                        key=request.key,
                        role=request.role,
                        status="running",
                        request=request.model_dump(),
                    )
                    session.add(child)
                    emit(session, run, "delegation.created", {"id": child.id, **request.model_dump()})
                else:
                    child = next(c for c in existing if c.key == request.key)
                    if child.request != request.model_dump():
                        raise PolicyError("delegation key reused with different contract")

        async def child_run(request):
            async with self.child_slots:
                try:
                    await self._agent(lease, lease.run_id + "-" + request.key, saver)
                except (LeaseLost, RunStopped):
                    raise
                except Exception as exc:
                    with self.db.transaction() as session:
                        run = self.ledger.fenced(session, lease)
                        child = session.get(AgentRow, run.id + "-" + request.key)
                        child.status, child.summary = "rejected", str(exc)[:2000]
                        emit(session, run, "delegation.rejected", {"id": child.id, "reason": child.summary})

        # Wait for both children before the single integration step. No child writes parent files.
        outcomes_or_errors = await asyncio.gather(*(child_run(r) for r in requests), return_exceptions=True)
        for outcome in outcomes_or_errors:
            if isinstance(outcome, BaseException):
                raise outcome
        with self.db.transaction() as session:
            run = self.ledger.fenced(session, lease)
            parent = session.get(AgentRow, parent_id)
            outcomes = []
            for request in requests:
                child = session.get(AgentRow, run.id + "-" + request.key)
                outcomes.append(
                    {
                        "key": child.key,
                        "status": child.status,
                        "artifacts": child.artifacts,
                        "summary": child.summary,
                    }
                )
            if append_context:
                parent.messages = [
                    *parent.messages,
                    {"role": "user", "content": json.dumps({"child_evidence": outcomes})},
                ]
            emit(session, run, "delegation.reviewed", {"outcomes": outcomes})
            return outcomes

    async def _finish_child(self, lease, agent_id):
        with self.db.transaction() as session:
            run = self.ledger.fenced(session, lease)
            child = session.get(AgentRow, agent_id)
            contract = self.ledger.contract(session, run)
            artifacts = list(
                session.scalars(
                    select(ArtifactRow).where(ArtifactRow.run_id == run.id, ArtifactRow.agent_id == agent_id)
                )
            )
            receipts = list(
                session.scalars(
                    select(ReceiptRow).where(ReceiptRow.run_id == run.id, ReceiptRow.agent_id == agent_id)
                )
            )
            if child.role == "implementation":
                workspace = self.store.workspace(
                    run.id, child.id, contract.snapshot_hash, session, epoch=run.epoch
                )
                changes = self.store.changes(workspace, contract.snapshot_hash, child.request["scope"])
                if changes:
                    artifacts.append(
                        self.store.put(session, run.id, child.id, "child_patch", json.dumps(changes).encode())
                    )
            aliases = {"patch": "child_patch"}
            required = {aliases.get(x, x) for x in child.request["deliverables"]}
            delivered = {a.kind for a in artifacts}
            valid = (
                bool(receipts) and all(r.status == "succeeded" for r in receipts) and required <= delivered
            )
            executed = {r.name for r in receipts if r.status == "succeeded"}
            required_tools = {
                "code_investigation": {"read_file"},
                "reproduction": {"run_tests"},
                "implementation": {"write_file", "run_tests"},
            }[child.role]
            valid = valid and required_tools <= executed
            # Parent validates actual bytes and receipt-linked ownership, never model-supplied IDs.
            for artifact in artifacts:
                self.store.read(artifact)
            child.status = "accepted" if valid else "rejected"
            child.artifacts = [a.id for a in artifacts] if valid else []
            emit(
                session,
                run,
                "delegation." + child.status,
                {"id": child.id, "required": sorted(required), "delivered": sorted(delivered)},
            )
