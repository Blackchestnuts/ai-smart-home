"""FastAPI 入口：注册路由 + 配置跨域（CORS） + 自动建表。"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from app.routers import devices, chat

# 自动建表（开发期方便，生产环境建议改用 Alembic 迁移）
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI 智能家居控制台", version="2.0 架构升级版")

# ===== 核心：配置跨域 CORS =====
# 开发阶段允许所有来源；生产环境请把 allow_origins 改成具体前端域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== 注册路由 =====
app.include_router(devices.router)
app.include_router(chat.router)


@app.get("/")
def read_root():
    return {"message": "欢迎来到 AI 智能家居后端 V2.0！"}
