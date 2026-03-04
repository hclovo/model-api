import json
import uuid
from collections.abc import AsyncIterator

import httpx

from model_api.config import settings
from model_api.providers.base import BaseProvider
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

# Gemini REST API 版本
_API_VERSION = "v1beta"

_SUPPORTED_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
]


def _to_gemini_contents(messages: list[ChatMessage]) -> tuple[str | None, list[dict]]:
    """将 OpenAI messages 转换为 Gemini contents 格式，同时提取 system_instruction。"""
    system_instruction: str | None = None
    contents: list[dict] = []

    for msg in messages:
        if msg.role == "system":
            # Gemini 用 systemInstruction 单独传递
            if isinstance(msg.content, str):
                system_instruction = msg.content
            continue

        role = "user" if msg.role == "user" else "model"

        if isinstance(msg.content, str):
            parts = [{"text": msg.content}]
        elif isinstance(msg.content, list):
            parts = []
            for part in msg.content:
                if part.type == "text" and part.text:
                    parts.append({"text": part.text})
                elif part.type == "image_url" and part.image_url:
                    # 支持 base64 内联图片
                    url = part.image_url.get("url", "")
                    if url.startswith("data:"):
                        media_type, b64data = url.split(";base64,", 1)
                        media_type = media_type.split(":", 1)[1]
                        parts.append({"inline_data": {"mime_type": media_type, "data": b64data}})
        else:
            parts = [{"text": ""}]

        contents.append({"role": role, "parts": parts})

    return system_instruction, contents


def _build_payload(request: ChatRequest) -> dict:
    system_instruction, contents = _to_gemini_contents(request.messages)

    generation_config: dict = {}
    if request.temperature is not None:
        generation_config["temperature"] = request.temperature
    if request.top_p is not None:
        generation_config["topP"] = request.top_p
    if request.max_tokens is not None:
        generation_config["maxOutputTokens"] = request.max_tokens
    if request.stop is not None:
        stop_sequences = [request.stop] if isinstance(request.stop, str) else request.stop
        generation_config["stopSequences"] = stop_sequences

    payload: dict = {"contents": contents}
    if generation_config:
        payload["generationConfig"] = generation_config
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    return payload


class GeminiProvider(BaseProvider):
    def __init__(self) -> None:
        self._api_key = settings.gemini_api_key
        self._base_url = settings.gemini_base_url

    def list_models(self) -> list[ModelInfo]:
        return [ModelInfo(id=m, owned_by="google") for m in _SUPPORTED_MODELS]

    def _model_url(self, model: str, action: str) -> str:
        return f"{self._base_url}/{_API_VERSION}/models/{model}:{action}?key={self._api_key}"

    async def chat(self, request: ChatRequest) -> ChatResponse:
        url = self._model_url(request.model, "generateContent")
        payload = _build_payload(request)

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        candidate = data["candidates"][0]
        text = candidate["content"]["parts"][0].get("text", "")
        finish_reason = candidate.get("finishReason", "STOP").lower()
        usage_meta = data.get("usageMetadata", {})

        return ChatResponse(
            model=request.model,
            choices=[Choice(message=ChoiceMessage(content=text), finish_reason=finish_reason)],
            usage=UsageInfo(
                prompt_tokens=usage_meta.get("promptTokenCount", 0),
                completion_tokens=usage_meta.get("candidatesTokenCount", 0),
                total_tokens=usage_meta.get("totalTokenCount", 0),
            ),
        )

    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[ChatStreamChunk]:
        url = self._model_url(request.model, "streamGenerateContent")
        payload = _build_payload(request)
        chunk_id = f"chatcmpl-{uuid.uuid4().hex}"

        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", url, json=payload) as resp:
                resp.raise_for_status()
                # Gemini 流式返回的是 JSON array，逐行累积解析
                buffer = ""
                async for line in resp.aiter_lines():
                    buffer += line
                    # 尝试解析每个完整的 JSON 对象
                    try:
                        obj = json.loads(buffer.strip().lstrip("[").rstrip(",]"))
                        buffer = ""
                        candidate = obj["candidates"][0]
                        text = candidate["content"]["parts"][0].get("text", "")
                        finish_reason = candidate.get("finishReason")
                        yield ChatStreamChunk(
                            id=chunk_id,
                            model=request.model,
                            choices=[
                                StreamChoice(
                                    delta=DeltaMessage(content=text),
                                    finish_reason=finish_reason.lower() if finish_reason else None,
                                )
                            ],
                        )
                    except (json.JSONDecodeError, KeyError):
                        continue