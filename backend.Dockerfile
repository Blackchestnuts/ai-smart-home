# ===== Stage 1: build backend =====
FROM python:3.13-slim AS builder
WORKDIR /app

# 系统依赖（psycopg2 编译所需）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
 && rm -rf /var/lib/apt/lists/*

# 先装依赖（利用层缓存）
COPY backed/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ===== Stage 2: runtime =====
FROM python:3.13-slim AS runtime
LABEL org.opencontainers.image.title="ai-smart-home-backend"
LABEL org.opencontainers.image.description="FastAPI backend for AI smart home"

# 仅运行时需要的库
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
 && rm -rf /var/lib/apt/lists/* \
 && useradd -m -u 1000 app

WORKDIR /app

# 拷贝已安装的依赖
COPY --from=builder /install /usr/local

# 拷贝源码
COPY --chown=app:app backed/ ./

USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fsS http://localhost:8000/ || exit 1

# uvicorn 启动 main:app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
