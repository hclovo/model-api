# model-api

多模型 API 网关，暴露 OpenAI 兼容接口，通过 Cloudflare Worker 代理访问 Google Gemini 等境外模型。

## 特性

- **OpenAI 兼容接口**：`/v1/chat/completions`、`/v1/models`，可直接接入任何支持 OpenAI 格式的客户端
- **多 Provider**：Google Gemini、OpenAI（可按需扩展）
- **Cloudflare 代理**：通过 Cloudflare Worker 绕过网络限制，在国内服务器访问 Google AI API
- **流式输出**：SSE 流式响应
- **可选鉴权**：配置 `API_SECRET_KEY` 后启用 Bearer Token 校验

## 快速开始

### 1. 安装依赖

```bash
uv sync
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 API Keys 和 Cloudflare Worker URL
```

### 3. 部署 Cloudflare Worker（国内机器必须）

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com) → Workers & Pages → Create Worker
2. 将 `cloudflare/worker.js` 的内容粘贴进去，保存部署
3. 将 Worker URL 填入 `.env` 的 `CLOUDFLARE_PROXY_URL`

### 4. 启动服务

```bash
uv run uvicorn model_api.main:app --reload
# 或
uv run model-api
```

## 接口示例

### 非流式对话

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.0-flash",
    "messages": [{"role": "user", "content": "你好"}]
  }'
```

### 流式对话

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.0-flash",
    "messages": [{"role": "user", "content": "写一首诗"}],
    "stream": true
  }'
```

### 列出模型

```bash
curl http://localhost:8000/v1/models
```

## 支持的模型

| 模型名称 | Provider |
|---|---|
| `gemini-2.0-flash` | Google Gemini |
| `gemini-2.0-flash-lite` | Google Gemini |
| `gemini-1.5-pro` | Google Gemini |
| `gemini-1.5-flash` | Google Gemini |
| `gpt-4o` | OpenAI |
| `gpt-4o-mini` | OpenAI |
| `o1` / `o1-mini` / `o3-mini` | OpenAI |

## 项目结构

```
├── src/model_api/
│   ├── main.py          # FastAPI 入口
│   ├── config.py        # 配置（pydantic-settings）
│   ├── schemas.py       # OpenAI 兼容数据结构
│   ├── dependencies.py  # 鉴权依赖
│   ├── routes/
│   │   ├── chat.py      # POST /v1/chat/completions
│   │   └── models.py    # GET /v1/models
│   └── providers/
│       ├── base.py      # Provider 抽象基类
│       ├── gemini.py    # Google Gemini
│       └── openai.py    # OpenAI
├── cloudflare/
│   └── worker.js        # Cloudflare Worker 代理脚本
├── pyproject.toml
└── .env.example
```
