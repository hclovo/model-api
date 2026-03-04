import time
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field


# ── 请求 ──────────────────────────────────────────────────────────────────────

class MessageContentPart(BaseModel):
    type: Literal["text", "image_url"]
    text: str | None = None
    image_url: dict[str, str] | None = None


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool", "function"]
    content: str | list[MessageContentPart] | None = None
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


class ChatRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    # 采样参数
    temperature: float | None = None
    top_p: float | None = None
    n: int | None = None
    max_tokens: int | None = None
    max_completion_tokens: int | None = None  # OpenAI o系列新字段，与 max_tokens 等价
    stop: str | list[str] | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    seed: int | None = None
    logprobs: bool | None = None
    top_logprobs: int | None = None
    # 输出格式
    response_format: dict[str, Any] | None = None
    # 工具调用
    tools: list[dict[str, Any]] | None = None
    tool_choice: str | dict[str, Any] | None = None
    # 流式
    stream: bool = False
    stream_options: dict[str, Any] | None = None
    # 其他
    user: str | None = None


# ── 响应 ──────────────────────────────────────────────────────────────────────

class UsageInfo(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChoiceMessage(BaseModel):
    role: str = "assistant"
    content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


class Choice(BaseModel):
    index: int = 0
    message: ChoiceMessage
    finish_reason: str | None = "stop"
    logprobs: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: list[Choice]
    usage: UsageInfo = Field(default_factory=UsageInfo)
    system_fingerprint: str | None = None


# ── 流式响应 ──────────────────────────────────────────────────────────────────

class DeltaMessage(BaseModel):
    role: str | None = None
    content: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


class StreamChoice(BaseModel):
    index: int = 0
    delta: DeltaMessage
    finish_reason: str | None = None
    logprobs: dict[str, Any] | None = None


class ChatStreamChunk(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}")
    object: str = "chat.completion.chunk"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: list[StreamChoice]
    usage: UsageInfo | None = None


# ── 错误响应 ──────────────────────────────────────────────────────────────────

class ErrorDetail(BaseModel):
    message: str
    type: str = "server_error"
    code: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


# ── 模型列表 ──────────────────────────────────────────────────────────────────

class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "model-api"


class ModelListResponse(BaseModel):
    object: str = "list"
    data: list[ModelInfo]
