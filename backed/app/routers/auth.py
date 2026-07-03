"""用户认证路由：注册 + 登录 + JWT 签发。

依赖：PyJWT、passlib[bcrypt]
环境变量：
    JWT_SECRET      JWT 签名密钥（必填，生产请用 32+ 字符随机串）
    JWT_EXPIRES_HOURS   JWT 有效期（默认 24 小时）
"""
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from jwt import PyJWTError
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import SessionLocal, User

router = APIRouter(prefix="/api/auth", tags=["用户认证"])

# ============ 配置 ============
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_HOURS = int(os.getenv("JWT_EXPIRES_HOURS", "24"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============ 请求/响应模型 ============
class RegisterRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    username: str
    user_id: int


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


# ============ 工具函数 ============
def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRES_HOURS)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user_optional(token: str | None = Depends(oauth2_scheme),
                              db: Session = Depends(get_db)) -> User | None:
    """可选鉴权：带 token 就解析，没带或失败就返回 None。
    当前阶段不强制登录，方便演示。后续可改为强制。"""
    if not token:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username = payload.get("sub")
        if not username:
            return None
        return db.query(User).filter(User.username == username).first()
    except PyJWTError:
        return None


# ============ 路由 ============
@router.post("/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if len(req.username) < 3:
        raise HTTPException(status_code=400, detail="用户名至少 3 个字符")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 个字符")

    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    user = User(username=req.username, password_hash=hash_password(req.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    return TokenResponse(
        access_token=create_access_token(user.username),
        username=user.username,
    )


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(
        access_token=create_access_token(user.username),
        username=user.username,
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: User | None = Depends(get_current_user_optional)):
    if not current_user:
        raise HTTPException(status_code=401, detail="未登录")
    return UserResponse(username=current_user.username, user_id=current_user.user_id)
