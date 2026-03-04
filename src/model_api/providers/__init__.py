from model_api.providers.cloudflare import CloudflareProvider

_instance: CloudflareProvider | None = None


def get_provider(model: str) -> CloudflareProvider:
    global _instance
    if _instance is None:
        _instance = CloudflareProvider()
    return _instance


def list_all_models():
    return get_provider("").list_models()
