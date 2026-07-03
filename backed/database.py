"""数据库连接与 ORM 模型定义。

环境变量：
    DATABASE_URL              PostgreSQL 连接串
    DB_POOL_SIZE              连接池大小（默认 10）
    DB_MAX_OVERFLOW           连接池溢出上限（默认 20）
    DB_POOL_RECYCLE           连接回收周期秒数（默认 3600）
"""
import logging
import os

from sqlalchemy import Column, Boolean, Integer, String, Text, DateTime, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

logger = logging.getLogger("ai-smart-home.db")

# 必须在读取 SQLALCHEMY_DATABASE_URL 之前加载 .env
load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:123456@localhost:5432/smart_home",
)

# P1-7：显式配置连接池
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,                                    # 取连接前先 ping，避免拿到死连接
    pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
    pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "3600")),
    pool_timeout=30,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class DBDevice(Base):
    """设备实体表。"""
    __tablename__ = "devices"

    device_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    room = Column(String, nullable=False)
    is_on = Column(Boolean, default=False, nullable=False)


class Memory(Base):
    """AI 长期记忆表（KV 结构）。"""
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(String, nullable=False)


class Scene(Base):
    """场景预设表。

    config 字段是 JSON 字符串，格式：
    {
      "actions": [
        {"device_id": 1, "is_on": true},
        {"device_id": 2, "is_on": false}
      ]
    }
    """
    __tablename__ = "scenes"

    scene_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, default="")
    config = Column(Text, nullable=False, default='{"actions":[]}')


class User(Base):
    """用户表（最小化：仅用户名 + 密码哈希）。

    生产环境需要：邮箱、密码强度、refresh token、登录失败锁定等。
    """
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, server_default="NOW()")


def check_db_connection() -> bool:
    """健康检查：执行 SELECT 1，验证数据库可达。"""
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"数据库健康检查失败: {e}")
        return False
