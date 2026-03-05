# 构建阶段：安装依赖并打包
FROM python:3.13-slim AS builder

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# 优先复制依赖描述文件，利用 Docker 缓存
COPY pyproject.toml uv.lock* ./

# 安装生产依赖到独立目录，不安装 dev 依赖
RUN uv sync --frozen --no-dev --no-install-project

# 复制源码并安装项目本身
COPY src/ ./src/
RUN uv sync --frozen --no-dev

# 运行阶段：最终镜像
FROM python:3.13-slim

WORKDIR /app

# 从构建阶段复制虚拟环境和源码
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

# 将 venv 的 bin 目录加入 PATH
ENV PATH="/app/.venv/bin:$PATH"

# 服务默认端口
EXPOSE 8000

# 环境变量默认值（可在运行时通过 -e 或 .env 覆盖）
ENV HOST=0.0.0.0 \
    PORT=8000 \
    LOG_LEVEL=info

CMD ["model-api"]