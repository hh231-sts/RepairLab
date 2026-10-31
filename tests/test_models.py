import json

import httpx
import pytest
from repairlab.config import Settings
from repairlab.domain import ModelReply
from repairlab.knowledge import EmbeddingAdapter
from repairlab.models import DeepSeekAdapter, ModelError


async def test_disabled_even_with_key_and_transport():
    requests = []
    adapter = DeepSeekAdapter(
        Settings(deepseek_api_key="present-but-unused", model_calls_enabled=False),
        httpx.MockTransport(lambda r: requests.append(r)),
    )
    with pytest.raises(ModelError, match="disabled"):
        await adapter.complete([], [])
    assert requests == []
    with pytest.raises(ValueError, match="embedding_disabled"):
        EmbeddingAdapter(Settings()).encode(["text"])


async def test_multiturn_tool_protocol():
    seen = []

    def respond(request):
        payload = json.loads(request.content)
        seen.append(payload)
        if len(seen) == 1:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": "call-1",
                                        "type": "function",
                                        "function": {
                                            "name": "read_file",
                                            "arguments": '{"path":"src/calculator.py"}',
                                        },
                                    }
                                ],
                            }
                        }
                    ],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 20},
                },
            )
        assert payload["messages"][-1]["tool_call_id"] == "call-1"
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "request verification"}}],
                "usage": {"prompt_tokens": 30, "completion_tokens": 10},
            },
        )

    adapter = DeepSeekAdapter(
        Settings(model_calls_enabled=True, deepseek_api_key="mock-key"), httpx.MockTransport(respond)
    )
    first = await adapter.complete([{"role": "user", "content": "repair"}], [])
    assert first.calls[0].arguments == {"path": "src/calculator.py"}
    second = await adapter.complete(
        [
            {"role": "user", "content": "repair"},
            first.raw_message,
            {"role": "tool", "tool_call_id": "call-1", "content": "evidence"},
        ],
        [],
    )
    assert second.finish and len(seen) == 2
    assert seen[0]["model"] == "deepseek-flash"


@pytest.mark.parametrize(
    "code,category", [(429, "rate_limited"), (400, "invalid_request"), (503, "provider_error")]
)
async def test_provider_errors(code, category):
    adapter = DeepSeekAdapter(
        Settings(model_calls_enabled=True, deepseek_api_key="mock"),
        httpx.MockTransport(lambda r: httpx.Response(code)),
    )
    with pytest.raises(ModelError) as error:
        await adapter.complete([], [])
    assert error.value.category == category


async def test_timeout_and_missing_usage():
    def timeout(request):
        raise httpx.ReadTimeout("timeout")

    adapter = DeepSeekAdapter(
        Settings(model_calls_enabled=True, deepseek_api_key="mock"), httpx.MockTransport(timeout)
    )
    with pytest.raises(ModelError) as error:
        await adapter.complete([], [])
    assert error.value.category == "timeout"
    adapter.transport = httpx.MockTransport(
        lambda r: httpx.Response(
            200, json={"choices": [{"message": {"role": "assistant", "content": "done"}}]}
        )
    )
    assert (await adapter.complete([], [])).usage is None


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"choices": []},
        {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {"id": "bad", "function": {"name": "read_file", "arguments": "invalid"}}
                        ]
                    }
                }
            ]
        },
    ],
)
async def test_bad_response(body):
    adapter = DeepSeekAdapter(
        Settings(model_calls_enabled=True, deepseek_api_key="mock"),
        httpx.MockTransport(lambda r: httpx.Response(200, json=body)),
    )
    with pytest.raises(ModelError):
        await adapter.complete([], [])


def test_action_discriminant():
    with pytest.raises(ValueError):
        ModelReply(finish=True, waiting_input=True)


async def test_deepseek_documented_usage_details():
    usage = {
        "prompt_tokens": 12,
        "completion_tokens": 4,
        "total_tokens": 16,
        "prompt_cache_hit_tokens": 8,
        "prompt_cache_miss_tokens": 4,
        "prompt_tokens_details": {"cached_tokens": 8},
        "completion_tokens_details": {"reasoning_tokens": 0},
    }
    body = {
        "choices": [{"message": {"role": "assistant", "content": "request verification"}}],
        "usage": usage,
    }
    adapter = DeepSeekAdapter(
        Settings(model_calls_enabled=True, deepseek_api_key="mock"),
        httpx.MockTransport(lambda request: httpx.Response(200, json=body)),
    )
    reply = await adapter.complete([], [])
    assert reply.finish and reply.usage == usage


async def test_deepseek_null_tool_calls():
    body = {
        "choices": [{"message": {"role": "assistant", "content": "request verification", "tool_calls": None}}]
    }
    adapter = DeepSeekAdapter(
        Settings(model_calls_enabled=True, deepseek_api_key="mock"),
        httpx.MockTransport(lambda request: httpx.Response(200, json=body)),
    )
    reply = await adapter.complete([], [])
    assert reply.finish and reply.calls == []


@pytest.mark.parametrize(
    "usage",
    [
        {"prompt_tokens": -1},
        {"completion_tokens": True},
        {"prompt_tokens": None},
        {"completion_tokens_details": {"reasoning_tokens": -1}},
    ],
)
def test_usage_counters_remain_validated(usage):
    with pytest.raises(ValueError):
        ModelReply(finish=True, usage=usage)


async def test_real_adapter_path_settles_nested_usage_in_harness(app, demo, monkeypatch):
    from repairlab import harness as harness_module
    from repairlab.scripts import FIXED_CODE

    settings = app.state.settings
    settings.model_calls_enabled = True
    settings.deepseek_api_key = "mock"
    settings.price_snapshot = "mock-protocol-regression"
    settings.input_cny_per_million = 2
    settings.output_cny_per_million = 8
    usage = {
        "prompt_tokens": 100,
        "completion_tokens": 10,
        "total_tokens": 110,
        "prompt_tokens_details": {"cached_tokens": 0},
        "completion_tokens_details": {"reasoning_tokens": 0},
    }
    seen = []

    def respond(request):
        seen.append(json.loads(request.content))
        message = {"role": "assistant", "content": "Request independent verification", "tool_calls": None}
        if len(seen) == 1:
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "fix-1",
                        "type": "function",
                        "function": {
                            "name": "write_file",
                            "arguments": json.dumps({"path": "src/calculator.py", "content": FIXED_CODE}),
                        },
                    }
                ],
            }
        return httpx.Response(200, json={"choices": [{"message": message}], "usage": usage})

    adapter = DeepSeekAdapter(
        settings.model_copy(update={"deepseek_api_key": "mock"}), httpx.MockTransport(respond)
    )
    monkeypatch.setattr(harness_module, "select_model", lambda *args: adapter)
    run = app.state.platform.submit(demo["issue"]["id"], model_source="deepseek")
    await app.state.harness.run(app.state.ledger.claim("mock-provider-worker"))
    detail = app.state.platform.detail(run["id"])
    assert detail["status"] == "succeeded", detail["terminal_reason"]
    assert len(seen) == detail["calls"] == 2
    assert detail["reserved"] == pytest.approx(0)
    assert detail["spent"] == pytest.approx(0.00056)
    assert all(
        call["metadata_json"]["usage"] == usage and call["status"] == "settled"
        for call in detail["model_calls"]
    )


@pytest.mark.parametrize("include_usage", [True, False])
async def test_protocol_failure_has_safe_diagnostics_and_accounting(app, demo, monkeypatch, include_usage):
    from repairlab import harness as harness_module
    from repairlab.db import EventRow
    from sqlalchemy import select

    settings = app.state.settings
    settings.model_calls_enabled = True
    settings.deepseek_api_key = "mock"
    settings.price_snapshot = "mock-protocol-regression"
    settings.input_cny_per_million = 2
    settings.output_cny_per_million = 8
    private_text = "sk-never-echo-this-payload"
    body = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {"id": "bad", "function": {"name": "read_file", "arguments": private_text}}
                    ],
                }
            }
        ]
    }
    if include_usage:
        body["usage"] = {
            "prompt_tokens": 100,
            "completion_tokens": 10,
            "prompt_tokens_details": {"cached_tokens": 0},
        }
    adapter = DeepSeekAdapter(
        settings.model_copy(update={"deepseek_api_key": "mock"}),
        httpx.MockTransport(lambda request: httpx.Response(200, json=body)),
    )
    monkeypatch.setattr(harness_module, "select_model", lambda *args: adapter)
    run = app.state.platform.submit(demo["issue"]["id"], model_source="deepseek")
    await app.state.harness.run(app.state.ledger.claim("mock-provider-worker"))
    detail = app.state.platform.detail(run["id"])
    assert detail["status"] == "failed" and detail["terminal_reason"] == "protocol"
    call = detail["model_calls"][0]
    assert call["metadata_json"]["error"]["parse_stage"] == "tool_arguments"
    if include_usage:
        assert detail["spent"] == pytest.approx(0.00028) and detail["reserved"] == pytest.approx(0)
        assert call["status"] == "failed"
    else:
        assert detail["spent"] == 0 and detail["reserved"] > 0
        assert call["status"] == "failed_unknown_usage"
    with app.state.db.sessions() as session:
        events = [
            e.payload
            for e in session.scalars(
                select(EventRow).where(EventRow.run_id == run["id"], EventRow.kind == "model.error")
            )
        ]
    assert len(events) == 1 and events[0]["parse_stage"] == "tool_arguments"
    assert private_text not in json.dumps([call, events])
