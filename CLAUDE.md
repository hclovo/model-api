# model-api 项目规范

## 项目简介
基于 FastAPI + uv 的多模型 API 网关，通过 Cloudflare Worker 代理访问 Google Gemini 等境外模型。

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
├── main.py          # FastAPI 入口
├── config.py        # 配置（pydantic-settings）
├── dependencies.py  # 依赖注入（认证等）
├── routes/
│   ├── chat.py      # /v1/chat/completions
│   └── models.py    # /v1/models
└── providers/
    ├── base.py      # Provider 抽象基类
    ├── gemini.py    # Google Gemini
    └── openai.py    # OpenAI
cloudflare/
└── worker.js        # Cloudflare Worker 代理脚本
```

## API 规范
- 对外暴露 OpenAI 兼容接口（`/v1/chat/completions`、`/v1/models`）
- 模型名前缀路由到对应 Provider：
  - `gemini-*` → Gemini Provider
  - `gpt-*` / `o1-*` / `o3-*` → OpenAI Provider
- 支持流式输出（SSE）

## 环境变量
参考 `.env.example`，复制为 `.env` 后填入真实值。