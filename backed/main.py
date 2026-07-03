"""FastAPI 入口：注册路由 + 配置跨域（CORS） + 健康检查 + 日志 + 自动建表。"""
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, check_db_connection, engine
from app.routers import devices, chat, scenes, auth

# ============ 日志配置（P2-13） ============
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ai-smart-home.main")

# 自动建表（开发期方便；生产建议用 Alembic）
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI 智能家居控制台", version="2.1 架构升级版")

# ============ CORS 配置（P1-8） ============
# 生产环境通过 CORS_ORIGINS 环境变量指定具体域名（逗号分隔）；
# 未配置时回退到 * （仅适合开发环境）
_cors_env = os.getenv("CORS_ORIGINS", "").strip()
if _cors_env:
    cors_origins = [s.strip() for s in _cors_env.split(",") if s.strip()]
else:
    cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=cors_origins != ["*"],  # 配合 * 时必须 False
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ 注册路由 ============
app.include_router(devices.router)
app.include_router(chat.router)
app.include_router(scenes.router)
app.include_router(auth.router)


@app.get("/")
def read_root():
    return {"message": "欢迎来到 AI 智能家居后端 V2.1！", "docs": "/docs"}


@app.get("/health")
def health():
    """P1-9：健康检查，真实探测数据库连通性。"""
    db_ok = check_db_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "up" if db_ok else "down",
    }
