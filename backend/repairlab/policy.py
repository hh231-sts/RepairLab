from .domain import DelegationRequest, ModelReply, ToolCall


def planned_reply(strategy: str, cursor: int, contract) -> ModelReply | None:
    """Frozen internal baselines share the same tools/workers as adaptive delegation."""
    if strategy not in {"parallel", "fixed"}:
        return None
    if cursor == 0:
        return ModelReply(
            delegations=[
                DelegationRequest(
                    key="investigation",
                    role="code_investigation",
                    objective="Trace the reported issue to source evidence and return a cited note.",
                    scope=contract.allowed_paths,
                    deliverables=["note"],
                    hypothesis="The report describes an implementation mismatch.",
                    evidence=["issue"],
                ),
                DelegationRequest(
                    key="reproduction",
                    role="reproduction",
                    objective="Run relevant public tests and preserve the observable result.",
                    scope=list(
                        dict.fromkeys(
                            [*contract.allowed_paths, *[p.rstrip("/") + "/" for p in contract.public_tests]]
                        )
                    ),
                    deliverables=["test_output"],
                    hypothesis="Public execution can distinguish the reported behavior.",
                    evidence=["issue"],
                ),
            ]
        )
    if strategy == "fixed" and cursor == 1:
        return ModelReply(
            delegations=[
                DelegationRequest(
                    key="implementation",
                    role="implementation",
                    objective="Prepare a scoped repair with public test evidence using accepted investigation and reproduction.",
                    scope=contract.allowed_paths,
                    deliverables=["patch"],
                    hypothesis="Accepted source and test evidence identify a repairable code path.",
                    evidence=["investigation", "reproduction"],
                )
            ]
        )
    if strategy == "fixed" and cursor == 2:
        return ModelReply(
            calls=[ToolCall(id="policy-integrate", name="integrate", arguments={"key": "implementation"})]
        )
    return None
