from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Cloudflare AI Gateway
    # Token: Cloudflare Dashboard → AI Gateway → 你的 Gateway → API Token
    cf_aig_token: str = ""
    # 完整的 /compat 端点，例如：
    # https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_name}/compat
    cf_aig_base_url: str = ""

    # 服务器
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"

    # 可选访问鉴权，客户端需携带 "Authorization: Bearer <key>"
    api_secret_key: str | None = None


settings = Settings()
