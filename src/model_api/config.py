from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # API Keys
    gemini_api_key: str | None = None
    openai_api_key: str | None = None

    # Cloudflare Worker 代理地址，例如 https://your-worker.your-subdomain.workers.dev
    cloudflare_proxy_url: str | None = None

    # 服务器
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"

    # 可选的访问鉴权 Key，客户端需携带 "Authorization: Bearer <key>"
    api_secret_key: str | None = None

    @property
    def gemini_base_url(self) -> str:
        """Gemini API 基础地址，配置了代理时走 Cloudflare Worker。"""
        if self.cloudflare_proxy_url:
            return self.cloudflare_proxy_url.rstrip("/") + "/google"
        return "https://generativelanguage.googleapis.com"

    @property
    def openai_base_url(self) -> str:
        """OpenAI API 基础地址，配置了代理时走 Cloudflare Worker。"""
        if self.cloudflare_proxy_url:
            return self.cloudflare_proxy_url.rstrip("/") + "/openai"
        return "https://api.openai.com"


settings = Settings()