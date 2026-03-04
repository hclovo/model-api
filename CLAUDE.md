# model-api 项目规范

## 项目简介
基于 FastAPI + uv 的多模型 API 网关，通过 Cloudflare AI Gateway 统一接入 Google Gemini、OpenAI、Anthropic 等模型。

## 包管理
- 使用 `uv` 管理依赖，不使用 pip/poetry
- 添加依赖：`uv add <package>`
- 运行：`uv run uvicorn model_api.main:app --reload`

## 代码规范
- Python 版本：3.11+
- 类型注解使用 `X | None` 而非 `Optional[X]`
- 使用 `list[X]`、`dict[K, V]` 而非 `List[X]`、`Dict[K, V]`
- 使用 pydantic v2 语法（`model_config`、`model_validator` 等）
- 所有注释和文档用**中文**

## 项目结构
```
src/model_api/
├── main.py              # FastAPI 入口
├── config.py            # 配置（pydantic-settings）
├── schemas.py           # OpenAI 兼容数据结构
├── dependencies.py      # 依赖注入（认证等）
├── routes/
│   ├── chat.py          # /v1/chat/completions
│   └── models.py        # /v1/models
└── providers/
    ├── __init__.py      # get_provider / list_all_models
    └── cloudflare.py    # Cloudflare AI Gateway Provider
```

## Cloudflare AI Gateway
- 所有模型请求统一走 CF AI Gateway `/compat` 端点
- 模型名自动加 provider 前缀后发送给 CF：
  - `gemini-*` → `google-ai-studio/gemini-*`
  - `gpt-*` / `o1` / `o3` → `openai/gpt-*`
  - `claude-*` → `anthropic/claude-*`
- 也可直接传 `provider/model` 格式绕过自动映射

## 环境变量
参考 `.env.example`，复制为 `.env` 后填入真实值。
- `CF_AIG_TOKEN`：Cloudflare AI Gateway Token
- `CF_AIG_BASE_URL`：完整的 /compat 端点 URL
