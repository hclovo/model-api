import uuid
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from model_api.config import settings
from model_api.schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatStreamChunk,
    Choice,
    ChoiceMessage,
    DeltaMessage,
    ModelInfo,
    StreamChoice,
    UsageInfo,
)

# 模型名称前缀 → Cloudflare AI Gateway provider 标识
# 文档：https://developers.cloudflare.com/ai-gateway/providers/
_CF_PROVIDER_MAP: list[tuple[str, str]] = [
    ("gemini-", "google-ai-studio"),
    ("gpt-", "openai"),
    ("o1", "openai"),
    ("o3", "openai"),
    ("claude-", "anthropic"),
]

_SUPPORTED_MODELS: list[ModelInfo] = [
    # Google AI Studio
    ModelInfo(id="gemini-2.0-flash", owned_by="google"),
    ModelInfo(id="gemini-2.0-flash-lite", owned_by="google"),
    ModelInfo(id="gemini-1.5-pro", owned_by="google"),
    ModelInfo(id="gemini-1.5-flash", owned_by="google"),
    # OpenAI
    ModelInfo(id="gpt-4o", owned_by="openai"),
    ModelInfo(id="gpt-4o-mini", owned_by="openai"),
    ModelInfo(id="o1", owned_by="openai"),
    ModelInfo(id="o3-mini", owned_by="openai"),
    # Anthropic
    ModelInfo(id="claude-opus-4-5", owned_by="anthropic"),
    ModelInfo(id="claude-sonnet-4-5", owned_by="anthropic"),
    ModelInfo(id="claude-haiku-4-5", owned_by="anthropic"),
]


def _to_cf_model(model: str) -> str:
    """将用户传入的模型名转为 CF AI Gateway 格式：`provider/model`。"""
    if "/" in model:
        return model
    for prefix, provider in _CF_PROVIDER_MAP:
        if model.startswith(prefix):
            return f"{provider}/{model}"
    return model


def _to_messages(messages: list[ChatMessage]) -> list[dict]:
    """将内部 ChatMessage 列表转为 OpenAI SDK 期望的格式。"""
    result = []
    for msg in messages:
        m: dict = {"role": msg.role}
        if isinstance(msg.content, str) or msg.content is None:
            m["content"] = msg.content
        else:
            parts = []
            for part in msg.content:
                if part.type == "text":
                    parts.append({"type": "text", "text": part.text or ""})
                elif part.type == "image_url" and part.image_url:
                    parts.append({"type": "image_url", "image_url": part.image_url})
            m["content"] = parts
        if msg.name is not None:
            m["name"] = msg.name
        if msg.tool_call_id is not None:
            m["tool_call_id"] = msg.tool_call_id
        if msg.tool_calls is not None:
            m["tool_calls"] = msg.tool_calls
        result.append(m)
    return result


def _build_kwargs(request: ChatRequest, cf_model: str, stream: bool = False) -> dict:
    kwargs: dict = {
        "model": cf_model,
        "messages": _to_messages(request.messages),
    }
    # 采样参数
    if request.temperature is not None:
        kwargs["temperature"] = request.temperature
    if request.top_p is not None:
        kwargs["top_p"] = request.top_p
    if request.n is not None:
        kwargs["n"] = request.n
    # max_tokens / max_completion_tokens 二选一，优先用 max_completion_tokens
    max_tok = request.max_completion_tokens or request.max_tokens
    if max_tok is not None:
        kwargs["max_tokens"] = max_tok
    if request.stop is not None:
        kwargs["stop"] = request.stop
    if request.presence_penalty is not None:
        kwargs["presence_penalty"] = request.presence_penalty
    if request.frequency_penalty is not None:
        kwargs["frequency_penalty"] = request.frequency_penalty
    if request.seed is not None:
        kwargs["seed"] = request.seed
    if request.logprobs is not None:
        kwargs["logprobs"] = request.logprobs
    if request.top_logprobs is not None:
        kwargs["top_logprobs"] = request.top_logprobs
    # 输出格式
    if request.response_format is not None:
        kwargs["response_format"] = request.response_format
    # 工具调用
    if request.tools is not None:
        kwargs["tools"] = request.tools
    if request.tool_choice is not None:
        kwargs["tool_choice"] = request.tool_choice
    # 流式
    if stream:
        kwargs["stream"] = True
        if request.stream_options is not None:
            kwargs["stream_options"] = request.stream_options
    return kwargs


class CloudflareProvider:
    """通过 Cloudflare AI Gateway /compat 端点统一接入多个 LLM。"""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.cf_aig_token,
            base_url=settings.cf_aig_base_url,
        )

    def list_models(self) -> list[ModelInfo]:
        return _SUPPORTED_MODELS

    async def chat(self, request: ChatRequest) -> ChatResponse:
        cf_model = _to_cf_model(request.model)
        resp = await self._client.chat.completions.create(**_build_kwargs(request, cf_model))
        choice = resp.choices[0]

        return ChatResponse(
            id=resp.id,
            model=request.model,
            choices=[
                Choice(
                    message=ChoiceMessage(
                        content=choice.message.content,
                        tool_calls=(
                            [tc.model_dump() for tc in choice.message.tool_calls]
                            if choice.message.tool_calls
                            else None
                        ),
                    ),
                    finish_reason=choice.finish_reason,
                )
            ],
            usage=UsageInfo(
                prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
                completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
                total_tokens=resp.usage.total_tokens if resp.usage else 0,
            ),
            system_fingerprint=getattr(resp, "system_fingerprint", None),
        )

    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[ChatStreamChunk]:
        cf_model = _to_cf_model(request.model)
        chunk_id = f"chatcmpl-{uuid.uuid4().hex}"

        # 直接 await 得到 AsyncStream，避免嵌套事件循环问题
        stream = await self._client.chat.completions.create(
            **_build_kwargs(request, cf_model, stream=True)
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta = choice.delta
            yield ChatStreamChunk(
                id=chunk.id or chunk_id,
                model=request.model,
                choices=[
                    StreamChoice(
                        delta=DeltaMessage(
                            role=delta.role,
                            content=delta.content,
                            tool_calls=(
                                [tc.model_dump() for tc in delta.tool_calls]
                                if delta.tool_calls
                                else None
                            ),
                        ),
                        finish_reason=choice.finish_reason,
                    )
                ],
            )
