import hashlib
import json
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def digest(value: Any) -> str:
    raw = (
        value if isinstance(value, bytes) else json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    )
    return hashlib.sha256(raw).hexdigest()


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RunStatus(StrEnum):
    queued = "queued"
    running = "running"
    waiting_input = "waiting_input"
    paused = "paused"
    verifying = "verifying"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


TERMINAL = {"succeeded", "failed", "cancelled"}


class InputMaterial(StrictModel):
    source: str
    version: str
    content: str = Field(max_length=100000)
    sha256: str

    @model_validator(mode="after")
    def verify_hash(self):
        if digest(self.content.encode()) != self.sha256:
            raise ValueError("material digest mismatch")
        return self


class TaskContract(StrictModel):
    project_id: str
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1, max_length=50000)
    base_commit: str
    snapshot_hash: str
    environment: str
    allowed_paths: list[str] = Field(default_factory=lambda: ["src/"])
    public_tests: list[str] = Field(default_factory=lambda: ["tests"])
    acceptance: str = "Nonempty patch passes independent verifier"
    max_cost_cny: float = Field(5, gt=0, le=5)
    max_calls: int = Field(60, ge=1, le=60)
    max_seconds: int = Field(1200, ge=1, le=1200)
    source: Literal["user", "development_fixture", "swebench"] = "user"
    source_id: str | None = None
    verifier_id: str | None = None
    versions: dict[str, str] = Field(default_factory=lambda: {"harness": "0.1.0", "tools": "1"})
    materials: list[InputMaterial] = Field(default_factory=list)


class ToolCall(StrictModel):
    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class DelegationRequest(StrictModel):
    key: str = Field(pattern=r"^[a-z0-9_-]{1,40}$")
    role: Literal["code_investigation", "reproduction", "implementation"]
    objective: str = Field(min_length=1, max_length=4000)
    scope: list[str] = Field(min_length=1)
    deliverables: list[Literal["note", "test_output", "patch"]] = Field(min_length=1)
    hypothesis: str = Field(min_length=1)
    evidence: list[str] = Field(min_length=1)
    script: str | None = None


def validate_usage(value: dict[str, Any] | None) -> dict[str, Any] | None:
    """Preserve provider detail objects while checking counters used for accounting."""
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("usage must be an object")
    for key in (
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "prompt_cache_hit_tokens",
        "prompt_cache_miss_tokens",
    ):
        if key in value and (type(value[key]) is not int or value[key] < 0):
            raise ValueError("usage token counters must be nonnegative integers")

    def check_details(item):
        if isinstance(item, dict):
            for child in item.values():
                check_details(child)
        elif isinstance(item, (int, float)) and item < 0:
            raise ValueError("usage counters cannot be negative")

    check_details(value)
    return value


class ModelReply(StrictModel):
    origin: Literal["model", "policy"] = "model"
    content: str = ""
    calls: list[ToolCall] = Field(default_factory=list, max_length=8)
    delegations: list[DelegationRequest] = Field(default_factory=list, max_length=2)
    finish: bool = False
    waiting_input: bool = False
    usage: dict[str, Any] | None = None
    raw_message: dict[str, Any] | None = None

    @field_validator("usage")
    @classmethod
    def usage_counters(cls, value):
        return validate_usage(value)

    @model_validator(mode="after")
    def one_action(self):
        if sum([bool(self.calls), bool(self.delegations), self.finish, self.waiting_input]) != 1:
            raise ValueError("reply must contain exactly one action kind")
        return self


class RunLimits(StrictModel):
    max_cost_cny: float = Field(1, gt=0, le=5)
    max_calls: int = Field(20, ge=1, le=60)
    max_seconds: int = Field(600, ge=1, le=1200)


class Run(StrictModel):
    id: str
    issue_id: str
    status: RunStatus
    model_source: Literal["scripted", "deepseek"]
    strategy: Literal["single", "parallel", "fixed", "adaptive"]
    terminal_reason: str | None = None


class Delegation(StrictModel):
    id: str
    run_id: str
    parent_id: str | None = None
    role: str
    status: str
    accepted_artifacts: list[str] = Field(default_factory=list)


class ToolReceipt(StrictModel):
    id: str
    run_id: str
    agent_id: str
    name: str
    arguments: dict[str, Any]
    status: str
    result: dict[str, Any] | None = None


class Artifact(StrictModel):
    id: str
    run_id: str
    agent_id: str
    kind: str
    sha256: str
    size: int


class VerificationResult(StrictModel):
    id: str
    run_id: str
    patch_hash: str
    snapshot_hash: str
    environment_hash: str
    verifier_hash: str
    passed: bool
    reason: str


class MemoryEntry(StrictModel):
    project_id: str
    content: str = Field(min_length=1, max_length=20000)
    source_artifacts: list[str] = Field(min_length=1)
    applicable_versions: list[str] = Field(min_length=1)
    invalidation_conditions: str = Field(min_length=1)
    status: Literal["candidate", "validated", "invalid"] = "candidate"


class Experiment(StrictModel):
    name: str = Field(min_length=1)
    issue_ids: list[str] = Field(min_length=1)
    strategies: list[Literal["single", "parallel", "fixed", "adaptive"]] = Field(min_length=1)
    repetitions: int = Field(1, ge=1, le=3)
    model_source: Literal["scripted", "deepseek"] = "scripted"
    script: str = "repair"
    formal: bool = False
