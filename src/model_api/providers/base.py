from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from model_api.schemas import ChatRequest, ChatResponse, ChatStreamChunk, ModelInfo


class BaseProvider(ABC):
    """所有模型 Provider 的抽象基类。"""

    @abstractmethod
    def list_models(self) -> list[ModelInfo]:
        """返回该 Provider 支持的模型列表。"""

    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """非流式对话。"""

    @abstractmethod
    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[ChatStreamChunk]:
        """流式对话，返回 SSE chunk 异步迭代器。"""