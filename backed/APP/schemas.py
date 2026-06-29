#作用：负责规定前端能传什么，后端该返回什么
from pydantic import BaseModel

# 前端创建设备时传来的数据格式
class DeviceCreate(BaseModel):
    name: str
    room: str

# 后端返回给前端的数据格式（比 Create 多了 id 和 is_on）
class DeviceResponse(BaseModel):
    device_id: int
    name: str
    room: str
    is_on: bool

    class Config:
        from_attributes = True  # 告诉 Pydantic：即使数据是从 ORM 对象来的，也能直接读取