"""Test-only real-mode UI backend. DeepSeek HTTP ALWAYS uses MockTransport."""

import asyncio
import json

import httpx
from repairlab import harness as harness_module
from repairlab.api import create_app
from repairlab.config import Settings
from repairlab.models import DeepSeekAdapter, ScriptedModelAdapter, select_model
from repairlab.scripts import script


class MockDeepSeekAdapter(DeepSeekAdapter):
    async def complete(self, messages, tools, *, cursor=0):
        reply = await ScriptedModelAdapter(script("repair")).complete(messages, tools, cursor=cursor)
        message = {"role": "assistant", "content": reply.content, "tool_calls": None}
        if reply.calls:
            message["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": json.dumps(call.arguments)},
                }
                for call in reply.calls
            ]
        body = {
            "choices": [{"message": message}],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 10,
                "prompt_tokens_details": {"cached_tokens": 0},
            },
        }
        self.transport = httpx.MockTransport(lambda request: httpx.Response(200, json=body))
        return await super().complete(messages, tools, cursor=cursor)


def mock_factory(settings, source, replies):
    if source == "deepseek":
        assert settings.deepseek_api_key == "mock-transport-only"
        return MockDeepSeekAdapter(settings)
    return select_model(settings, source, replies)


def create_mock_app():
    harness_module.select_model = mock_factory
    return create_app(Settings())


if __name__ == "__main__":
    from repairlab.worker import serve

    harness_module.select_model = mock_factory
    asyncio.run(serve())
