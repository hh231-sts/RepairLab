import json

import pytest
from repairlab import harness as harness_module
from repairlab.models import ScriptedModelAdapter
from repairlab.scripts import FIXED_CODE


@pytest.mark.parametrize("children", [1, 2])
async def test_mixed_delegation_and_tools_keep_call_order_and_settle_usage(app, demo, monkeypatch, children):
    parent_replies = [
        {
            "calls": [
                {"id": "note-first", "name": "note", "arguments": {"text": "Investigate the boundary check"}},
                {
                    "id": "delegate-investigation",
                    "name": "delegate",
                    "arguments": {
                        "key": "investigation",
                        "role": "code_investigation",
                        "objective": "Locate clamp evidence",
                        "scope": ["src/"],
                        "deliverables": ["note"],
                        "hypothesis": "Missing boundary validation",
                        "evidence": ["issue"],
                        "script": "investigate",
                    },
                },
                {"id": "read-after", "name": "read_file", "arguments": {"path": "src/calculator.py"}},
            ]
        },
        {
            "calls": [
                {
                    "id": "fix",
                    "name": "write_file",
                    "arguments": {"path": "src/calculator.py", "content": FIXED_CODE},
                }
            ]
        },
        {"finish": True},
    ]

    if children == 2:
        original = parent_replies[0]["calls"][1]
        parent_replies[0]["calls"].insert(
            2, {**original, "id": "delegate-second", "arguments": {**original["arguments"], "key": "second"}}
        )

    class RoleAdapter:
        async def complete(self, messages, tools, *, cursor=0):
            role = json.loads(messages[0]["content"])["role"]
            return await ScriptedModelAdapter(
                parent_replies if role == "supervisor" else child_replies
            ).complete(messages, tools, cursor=cursor)

    child_replies = [
        {"calls": [{"id": "source", "name": "read_file", "arguments": {"path": "src/calculator.py"}}]},
        {
            "calls": [
                {
                    "id": "evidence",
                    "name": "note",
                    "arguments": {"text": "Boundary validation is absent in the source."},
                }
            ]
        },
        {"finish": True},
    ]
    monkeypatch.setattr(harness_module, "select_model", lambda *args: RoleAdapter())
    run = app.state.platform.submit(demo["issue"]["id"], strategy="adaptive")
    await app.state.harness.run(app.state.ledger.claim("mixed-calls"))
    detail = app.state.platform.detail(run["id"])
    assert detail["status"] == "succeeded", detail["terminal_reason"]
    assert all(call["status"] == "settled" for call in detail["model_calls"])
    from repairlab.db import AgentRow

    with app.state.db.sessions() as session:
        parent = session.get(AgentRow, run["id"] + "-supervisor")
        assistant = next(m for m in parent.messages if m.get("tool_calls"))
        index = parent.messages.index(assistant)
        results = parent.messages[index + 1 : index + 1 + len(assistant["tool_calls"])]
    assert [m["tool_call_id"] for m in results] == [
        "note-first",
        "delegate-investigation",
        *(["delegate-second"] if children == 2 else []),
        "read-after",
    ]
    assert json.loads(results[1]["content"])["outcomes"][0]["status"] == "accepted"
    assert len(detail["agents"]) == children + 1


async def test_single_agent_denied_delegate_returns_observation_without_losing_other_tools(
    app, demo, monkeypatch
):
    replies = [
        {
            "calls": [
                {
                    "id": "unsupported-delegate",
                    "name": "delegate",
                    "arguments": {
                        "key": "child",
                        "role": "code_investigation",
                        "objective": "Inspect source",
                        "scope": ["src/"],
                        "deliverables": ["note"],
                        "hypothesis": "Missing check",
                        "evidence": ["issue"],
                    },
                },
                {"id": "read", "name": "read_file", "arguments": {"path": "src/calculator.py"}},
            ]
        },
        {
            "calls": [
                {
                    "id": "fix",
                    "name": "write_file",
                    "arguments": {"path": "src/calculator.py", "content": FIXED_CODE},
                }
            ]
        },
        {"finish": True},
    ]
    observed = []

    class Adapter:
        async def complete(self, messages, tools, *, cursor=0):
            observed.append((messages, tools))
            return await ScriptedModelAdapter(replies).complete(messages, tools, cursor=cursor)

    monkeypatch.setattr(harness_module, "select_model", lambda *args: Adapter())
    run = app.state.platform.submit(demo["issue"]["id"], strategy="single")
    await app.state.harness.run(app.state.ledger.claim("single-no-delegation"))
    detail = app.state.platform.detail(run["id"])
    assert detail["status"] == "succeeded", detail["terminal_reason"]
    assert all("delegate" not in [tool["function"]["name"] for tool in schemas] for _, schemas in observed)
    tool_result = next(m for m in observed[1][0] if m.get("tool_call_id") == "unsupported-delegate")
    assert json.loads(tool_result["content"])["error"] == "delegation_policy"
    assert len(detail["agents"]) == 1


def test_tool_visibility_matches_role_and_strategy():
    from repairlab.tools import tool_schemas

    def names(**kwargs):
        return {tool["function"]["name"] for tool in tool_schemas(**kwargs)}

    assert "delegate" not in names(strategy="single")
    assert "delegate" in names(strategy="adaptive")
    assert "delegate" not in names(role="implementation", strategy="adaptive", is_child=True)
    assert "write_file" not in names(role="code_investigation", is_child=True)
