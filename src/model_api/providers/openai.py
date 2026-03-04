import uuid
from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from model_api.config import settings
from model_api.providers.base import BaseProvider
from model_api.schemas import (
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

_SUPPORTED_MODELS = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-3.5-turbo",
    "o1",
    "o1-mini",
    "o3-mini",
]


def _build_messages(request: ChatRequest) -> list[dict]:
    result = []
    for msg in request.messages:
        if isinstance(msg.content, str):
            result.append({"role": msg.role, "content": msg.content})
        elif isinstance(msg.content, list):
            parts = []
            for part in msg.content:
                if part.type == "text":
                    parts.append({"type": "text", "text": part.text or ""})
                elif part.type == "image_url" and part.image_url:
                    parts.append({"type": "image_url", "image_url": part.image_url})
            result.append({"role": msg.role, "content": parts})
    return result


class OpenAIProvider(BaseProvider):
    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url + "/v1",
        )

    def list_models(self) -> list[ModelInfo]:
        return [ModelInfo(id=m, owned_by="openai") for m in _SUPPORTED_MODELS]

    async def chat(self, request: ChatRequest) -> ChatResponse:
        kwargs: dict = {
            "model": request.model,
            "messages": _build_messages(request),
        }
        if request.temperature is not None:
            kwargs["temperature"] = request.temperature
        if request.top_p is not None:
            kwargs["top_p"] = request.top_p
        if request.max_tokens is not None:
            kwargs["max_tokens"] = request.max_tokens
        if request.stop is not None:
            kwargs["stop"] = request.stop

        resp = await self._client.chat.completions.create(**kwargs)
        choice = resp.choices[0]

        return ChatResponse(
            id=resp.id,
            model=resp.model,
            choices=[
                Choice(
                    message=ChoiceMessage(content=choice.message.content),
                    finish_reason=choice.finish_reason,
                )
            ],
            usage=UsageInfo(
                prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
                completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
                total_tokens=resp.usage.total_tokens if resp.usage else 0,
            ),
        )

    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[ChatStreamChunk]:
        kwargs: dict = {
            "model": request.model,
            "messages": _build_messages(request),
            "stream": True,
        }
        if request.temperature is not None:
            kwargs["temperature"] = request.temperature
        if request.top_p is not None:
            kwargs["top_p"] = request.top_p
        if request.max_tokens is not None:
            kwargs["max_tokens"] = request.max_tokens
        if request.stop is not None:
            kwargs["stop"] = request.stop

        chunk_id = f"chatcmpl-{uuid.uuid4().hex}"
        async with await self._client.chat.completions.create(**kwargs) as stream:
            async for chunk in stream:
                choice = chunk.choices[0] if chunk.choices else None
                if choice is None:
                    continue
                yield ChatStreamChunk(
                    id=chunk.id or chunk_id,
                    model=chunk.model or request.model,
                    choices=[
                        StreamChoice(
                            delta=DeltaMessage(
                                role=choice.delta.role,
                                content=choice.delta.content,
                            ),
                            finish_reason=choice.finish_reason,
                        )
                    ],
                )