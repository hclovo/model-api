from model_api.providers.base import BaseProvider
from model_api.providers.gemini import GeminiProvider
from model_api.providers.openai import OpenAIProvider

# 惰性单例，按需创建
_gemini: GeminiProvider | None = None
_openai: OpenAIProvider | None = None


def get_provider(model: str) -> BaseProvider:
    """根据模型名称前缀返回对应的 Provider 实例。"""
    global _gemini, _openai

    if model.startswith("gemini"):
        if _gemini is None:
            _gemini = GeminiProvider()
        return _gemini

    if model.startswith(("gpt-", "o1", "o3")):
        if _openai is None:
            _openai = OpenAIProvider()
        return _openai

    raise ValueError(f"不支持的模型: {model}")


def list_all_models():
    """聚合所有 Provider 的模型列表。"""
    from model_api.config import settings

    models = []
    if settings.gemini_api_key:
        models.extend(GeminiProvider().list_models())
    if settings.openai_api_key:
        models.extend(OpenAIProvider().list_models())
    return models


