import asyncio
import json
from typing import Protocol

import httpx

from .config import Settings
from .domain import ModelReply, ToolCall, validate_usage


class ModelError(RuntimeError):
    def __init__(self, category: str, detail: str, *, usage=None, diagnostics=None):
        self.category = category
        self.usage = usage
        self.diagnostics = diagnostics or {}
        super().__init__(detail)


class ModelAdapter(Protocol):
    source: str

    async def complete(self, messages: list[dict], tools: list[dict], *, cursor: int = 0) -> ModelReply: ...


class DisabledModelAdapter:
    source = "disabled"

    async def complete(self, messages, tools, *, cursor=0):
        raise ModelError("model_disabled", "Real model calls are disabled by server configuration")


class DeepSeekAdapter:
    source = "deepseek"

    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.transport = transport

    async def complete(self, messages: list[dict], tools: list[dict], *, cursor: int = 0) -> ModelReply:
        # Gate applies even to transports: tests opt in ONLY with an in-memory transport.
        if not self.settings.model_calls_enabled:
            return await DisabledModelAdapter().complete(messages, tools)
        if not self.settings.deepseek_api_key:
            raise ModelError("configuration", "DEEPSEEK_API_KEY missing")
        request = {
            "model": self.settings.deepseek_model,
            "messages": messages,
            "tools": tools,
            "max_tokens": 4096,
            "temperature": 0,
            "thinking": {"type": "disabled"},
        }
        stage, usage = "http", None
        response = None
        try:
            async with httpx.AsyncClient(transport=self.transport, timeout=45, trust_env=False) as client:
                response = await client.post(
                    "https://api.deepseek.com/chat/completions",
                    json=request,
                    headers={"Authorization": f"Bearer {self.settings.deepseek_api_key}"},
                )
            if response.status_code == 429:
                raise ModelError("rate_limited", "provider rate limited; no automatic duplicate request")
            if response.status_code >= 400:
                raise ModelError(
                    "invalid_request" if response.status_code < 500 else "provider_error",
                    f"provider HTTP {response.status_code}",
                )
            stage = "json"
            body = response.json()
            stage = "usage"
            usage = validate_usage(body.get("usage"))
            stage = "choices"
            if body["choices"][0].get("finish_reason") == "length":
                raise ModelError("output_limit", "provider response was truncated")
            message = body["choices"][0]["message"]
            stage = "tool_calls"
            tool_calls = message.get("tool_calls")
            if tool_calls is None:
                tool_calls = []
            if not isinstance(tool_calls, list):
                raise ValueError("tool_calls must be a list or null")
            stage = "tool_arguments"
            calls = [
                ToolCall(
                    id=x["id"], name=x["function"]["name"], arguments=json.loads(x["function"]["arguments"])
                )
                for x in tool_calls
            ]
            stage = "reply_validation"
            return ModelReply(
                content=message.get("content") or "",
                calls=calls,
                finish=not calls,
                usage=usage,
                raw_message=message,
            )
        except ModelError as exc:
            if exc.usage is None:
                exc.usage = usage
            raise
        except httpx.TimeoutException as exc:
            raise ModelError("timeout", "provider response uncertain; reservation retained") from exc
        except httpx.HTTPError as exc:
            raise ModelError("transport", "provider transport failed") from exc
        except (KeyError, IndexError, TypeError, ValueError, AttributeError) as exc:
            diagnostics = {
                "parse_stage": stage,
                "exception_type": type(exc).__name__,
                "http_status": response.status_code if response is not None else None,
            }
            raise ModelError(
                "protocol",
                f"invalid provider response at {stage} ({type(exc).__name__})",
                usage=usage,
                diagnostics=diagnostics,
            ) from exc


class ScriptedModelAdapter:
    """Deterministic development scripts. Never loaded from task/issue input."""

    source = "scripted"

    def __init__(self, replies: list[dict], delay: float = 0):
        self.replies = replies
        self.delay = delay

    async def complete(self, messages, tools, *, cursor=0):
        if self.delay:
            await asyncio.sleep(self.delay)
        if cursor >= len(self.replies):
            raise ModelError("script_exhausted", "script ended without a completion request")
        return ModelReply.model_validate(self.replies[cursor])


def select_model(settings: Settings, source: str, replies: list[dict]) -> ModelAdapter:
    if source == "scripted":
        return ScriptedModelAdapter(replies)
    if not settings.model_calls_enabled:
        return DisabledModelAdapter()
    return DeepSeekAdapter(settings)
