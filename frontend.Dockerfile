# ===== Stage 1: build frontend =====
FROM node:20-alpine AS builder
WORKDIR /app

# 先拷依赖文件，利用 Docker 层缓存
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund

# 再拷源码
COPY frontend/ ./

# 构建时通过环境变量注入后端地址（Vite 只认 VITE_ 前缀）
ARG VITE_API_BASE=http://localhost:8000
ENV VITE_API_BASE=$VITE_API_BASE
RUN npm run build


# ===== Stage 2: serve with nginx =====
FROM nginx:1.27-alpine AS runtime
LABEL org.opencontainers.image.title="ai-smart-home-frontend"
LABEL org.opencontainers.image.description="React 19 SPA served by Nginx"

# 替换默认配置
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

# 拷贝构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget -qO- http://localhost/ >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
