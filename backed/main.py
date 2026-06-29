#注册路由和配置跨域（CORS）。

# 什么是跨域？明天你写 React 前端时，前端跑在 localhost:5173，后端跑在 localhost:8000。浏览器的安全策略会拦截不同端口之间的请求（叫跨域）。我们需要在后端提前发“通行证”。
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from app.routers import devices

# 自动建表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI 智能家居控制台", version="2.0 架构升级版")

# ===== 核心：配置跨域 CORS =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源访问（开发阶段图方便，上线后要换成具体前端域名）
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法 (GET, POST 等)
    allow_headers=["*"],  # 允许所有请求头
)

# ===== 注册路由 =====
app.include_router(devices.router)

@app.get("/")
def read_root():
    return {"message": "欢迎来到 AI 智能家居后端 V2.0！"}