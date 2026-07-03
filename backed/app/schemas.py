"""Pydantic 请求/响应模型。"""
from pydantic import BaseModel


class DeviceCreate(BaseModel):
    name: str
    room: str


class DeviceResponse(BaseModel):
    device_id: int
    name: str
    room: str
    is_on: bool

    class Config:
        from_attributes = True


# ============ 场景预设 ============
class SceneAction(BaseModel):
    device_id: int
    is_on: bool


class SceneCreate(BaseModel):
    name: str
    description: str = ""
    actions: list[SceneAction] = []


class SceneResponse(BaseModel):
    scene_id: int
    name: str
    description: str
    actions: list[SceneAction] = []

    class Config:
        from_attributes = True
