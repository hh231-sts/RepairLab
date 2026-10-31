import json
import time
from dataclasses import dataclass

from sqlalchemy import and_, or_, select

from .config import Settings
from .db import AgentRow, BudgetRow, EventRow, IssueRow, ModelCallRow, RunRow
from .domain import TERMINAL, TaskContract, digest


class LeaseLost(RuntimeError):
    pass


class RunStopped(RuntimeError):
    pass


@dataclass(frozen=True)
class Lease:
    run_id: str
    owner: str
    epoch: int


def emit(session, run: RunRow, kind: str, payload: dict):
    run.event_seq += 1
    session.add(EventRow(run_id=run.id, seq=run.event_seq, kind=kind, payload=payload))


class Ledger:
    def __init__(self, db, settings: Settings):
        self.db, self.settings = db, settings

    def fenced(self, session, lease: Lease) -> RunRow:
        run = session.scalar(select(RunRow).where(RunRow.id == lease.run_id).with_for_update())
        if not run or run.owner != lease.owner or run.epoch != lease.epoch or run.lease_until < time.time():
            raise LeaseLost("worker lease expired or replaced")
        if run.status in TERMINAL:
            raise RunStopped(run.status)
        return run

    def contract(self, session, run: RunRow) -> TaskContract:
        issue = session.get(IssueRow, run.issue_id)
        if digest(issue.contract) != issue.contract_hash:
            raise ValueError("immutable task contract was modified")
        contract = TaskContract.model_validate(issue.contract)
        limits = run.versions.get("limits")
        if limits:
            from .domain import RunLimits

            validated = RunLimits.model_validate(limits).model_dump()
            if any(value > getattr(contract, name) for name, value in validated.items()):
                raise ValueError("run limits exceed immutable contract")
            contract = contract.model_copy(update=validated)
        return contract

    def claim(self, owner: str) -> Lease | None:
        now = time.time()
        with self.db.transaction() as session:
            run = session.scalar(
                select(RunRow)
                .where(
                    or_(
                        RunRow.status == "queued",
                        and_(RunRow.status.in_(["running", "verifying"]), RunRow.lease_until < now),
                    )
                )
                .order_by(RunRow.created_at, RunRow.id)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            if not run:
                return None
            takeover = run.status != "queued"
            run.owner, run.epoch, run.lease_until = owner, run.epoch + 1, now + self.settings.lease_seconds
            run.status = "running"
            if run.started_at is None:
                run.started_at = now
            if not session.get(AgentRow, run.id + "-supervisor"):
                session.add(
                    AgentRow(
                        id=run.id + "-supervisor",
                        run_id=run.id,
                        key="supervisor",
                        role="supervisor",
                        status="running",
                    )
                )
            emit(
                session,
                run,
                "lease.takeover" if takeover else "run.started",
                {"owner": owner, "epoch": run.epoch},
            )
            return Lease(run.id, owner, run.epoch)

    def heartbeat(self, lease: Lease):
        with self.db.transaction() as session:
            run = self.fenced(session, lease)
            run.lease_until = time.time() + self.settings.lease_seconds

    def safe_point(self, lease: Lease):
        reason = None
        with self.db.transaction() as session:
            run = self.fenced(session, lease)
            contract = self.contract(session, run)
            if run.control == "cancel":
                run.status, run.terminal_reason, run.ended_at = "cancelled", "user_cancelled", time.time()
                for child in session.scalars(
                    select(AgentRow).where(
                        AgentRow.run_id == run.id, AgentRow.status.in_(["queued", "running"])
                    )
                ):
                    child.status = "cancelled"
                reason = "cancelled"
            elif run.control == "pause":
                run.status, run.control = "paused", None
                reason = "paused"
            elif time.time() - (run.started_at or time.time()) >= contract.max_seconds:
                run.status, run.terminal_reason, run.ended_at = "failed", "deadline_exceeded", time.time()
                reason = "deadline_exceeded"
            elif run.spent + run.reserved > contract.max_cost_cny + 1e-9:
                run.status, run.terminal_reason, run.ended_at = "failed", "budget_exceeded", time.time()
                reason = "budget_exceeded"
            if reason:
                run.owner, run.lease_until = None, 0
                emit(session, run, "run." + reason, {"partial_delivery": True})
        if reason:
            raise RunStopped(reason)

    def control(self, run_id: str, action: str):
        with self.db.transaction() as session:
            run = session.scalar(select(RunRow).where(RunRow.id == run_id).with_for_update())
            if not run:
                raise KeyError(run_id)
            if action == "resume" and run.status in {"paused", "waiting_input"}:
                run.status, run.control, run.owner, run.lease_until = "queued", None, None, 0
            elif action == "pause" and run.status in {"queued", "running", "verifying"}:
                if run.status == "queued":
                    run.status = "paused"
                else:
                    run.control = "pause"
            elif action == "cancel" and run.status not in TERMINAL:
                if run.status in {"queued", "paused", "waiting_input"}:
                    run.status, run.terminal_reason, run.ended_at = "cancelled", "user_cancelled", time.time()
                else:
                    run.control = "cancel"
                for child in session.scalars(
                    select(AgentRow).where(
                        AgentRow.run_id == run.id, AgentRow.status.in_(["queued", "running"])
                    )
                ):
                    child.status = "cancelled"
            else:
                raise ValueError(f"cannot {action} run in state {run.status}")
            emit(session, run, "control." + action, {})
            return run

    def is_cancelled(self, lease: Lease) -> bool:
        with self.db.sessions() as session:
            run = session.get(RunRow, lease.run_id)
            if not run or run.epoch != lease.epoch or run.control == "cancel" or run.status in TERMINAL:
                return True
            contract = self.contract(session, run)
            return time.time() - (run.started_at or time.time()) >= contract.max_seconds

    def reserve(self, lease: Lease, call_id: str, messages: list, source: str) -> ModelCallRow:
        with self.db.transaction() as session:
            run = self.fenced(session, lease)
            previous = session.get(ModelCallRow, call_id)
            if previous:
                # A lost HTTP response might have incurred cost. Never silently replay it.
                raise RunStopped("uncertain_model_call")
            contract = self.contract(session, run)
            amount = 0.0
            if source != "scripted":
                if not self.settings.model_calls_enabled:
                    raise ValueError("model_disabled")
                if (
                    self.settings.price_snapshot == "unconfigured"
                    or self.settings.output_cny_per_million <= 0
                ):
                    raise ValueError("price_snapshot_missing")
                # UTF-8 bytes conservatively bound input tokens, with schema/protocol overhead.
                input_bound = len(json.dumps(messages, ensure_ascii=False).encode()) + 24000
                amount = (
                    input_bound * self.settings.input_cny_per_million
                    + 4096 * self.settings.output_cny_per_million
                ) / 1_000_000
            if run.calls >= contract.max_calls or run.spent + run.reserved + amount > contract.max_cost_cny:
                raise RunStopped("budget_exhausted")
            pool = session.scalar(select(BudgetRow).where(BudgetRow.id == "global").with_for_update())
            if not pool or pool.spent + pool.reserved + amount > min(
                pool.limit_cny, self.settings.global_budget_cny
            ):
                raise RunStopped("global_budget_exhausted")
            pool.reserved += amount
            run.calls += 1
            run.reserved += amount
            call = ModelCallRow(
                id=call_id,
                run_id=run.id,
                source=source,
                reserved=amount,
                status="reserved",
                metadata_json={
                    "model": self.settings.deepseek_model if source != "scripted" else "script-v1",
                    "temperature": 0,
                    "max_tokens": 4096,
                    "price_snapshot": self.settings.price_snapshot,
                    "input_rate": self.settings.input_cny_per_million,
                    "output_rate": self.settings.output_cny_per_million,
                },
            )
            session.add(call)
            emit(session, run, "model.reserved", {"call_id": call_id, "source": source, "amount": amount})
            return call

    def settle_in_session(self, session, run, call_id: str, usage: dict | None):
        call = session.get(ModelCallRow, call_id)
        if call.status != "reserved":
            return
        if call.source == "scripted":
            actual = 0.0
        elif not usage or "prompt_tokens" not in usage or "completion_tokens" not in usage:
            call.status = "usage_missing"
            return  # retain conservative reservation
        else:
            actual = (
                usage["prompt_tokens"] * call.metadata_json["input_rate"]
                + usage["completion_tokens"] * call.metadata_json["output_rate"]
            ) / 1_000_000
        run.reserved = max(0, run.reserved - call.reserved)
        run.spent += actual
        pool = session.scalar(select(BudgetRow).where(BudgetRow.id == "global").with_for_update())
        pool.reserved = max(0, pool.reserved - call.reserved)
        pool.spent += actual
        call.actual, call.status = actual, "settled"
        call.metadata_json = {**call.metadata_json, "usage": usage}

    def end(self, lease: Lease, status: str, reason: str):
        with self.db.transaction() as session:
            run = self.fenced(session, lease)
            if run.control == "cancel":
                status, reason = "cancelled", "user_cancelled"
            run.status, run.terminal_reason = status, reason
            run.ended_at = time.time() if status in TERMINAL else None
            run.owner, run.lease_until = None, 0
            emit(session, run, "run." + status, {"reason": reason})
